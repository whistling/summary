package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/oschwald/geoip2-golang"
	"github.com/p4gefau1t/trojan-go/proxy"
)

// IPResponse 表示 IP 查询 API 的响应
type IPResponse struct {
	IP string `json:"ip"`
}

// ProxyManager 管理多个代理节点
type ProxyManager struct {
	config     *Config
	clients    map[string]*proxy.Proxy
	activeNode *ProxyNode
	geoDB      *geoip2.Reader
	mutex      sync.RWMutex
	ctx        context.Context
	cancel     context.CancelFunc
}

// NewProxyManager 创建一个新的代理管理器
func NewProxyManager(config *Config) (*ProxyManager, error) {
	// 初始化 GeoIP 数据库
	db, err := geoip2.Open("GeoLite2-Country.mmdb")
	if err != nil {
		return nil, fmt.Errorf("无法打开 GeoIP 数据库: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &ProxyManager{
		config:  config,
		clients: make(map[string]*proxy.Proxy),
		geoDB:   db,
		ctx:     ctx,
		cancel:  cancel,
	}, nil
}

// Start 启动代理管理器
func (pm *ProxyManager) Start() error {
	// 初始化所有节点
	basePort := pm.config.LocalPort
	for i := range pm.config.Nodes {
		// 为每个节点分配不同的本地端口
		pm.config.Nodes[i].LocalPort = basePort + i

		client, err := getProxyClient(pm.config.Nodes[i].URI, pm.config.Nodes[i].LocalPort)
		if err != nil {
			fmt.Printf("初始化节点 %s 失败: %v\n", pm.config.Nodes[i].URI, err)
			continue
		} else {
			go func() {
				log.Printf("节点启动中 %s ...\n", pm.config.Nodes[i].URI)
				err = client.Run()
				if err != nil {
					fmt.Printf("节点 %s 运行失败: %v\n", pm.config.Nodes[i].URI, err)
				}
			}()
		}
		pm.clients[pm.config.Nodes[i].URI] = client
	}
	time.Sleep(time.Second * 3)

	// 启动节点检查
	go pm.checkLoop()

	time.Sleep(time.Second * 20)

	// 选择初始节点
	return pm.switchToNextAvailableNode()
}

// Stop 停止代理管理器
func (pm *ProxyManager) Stop() {
	pm.cancel()
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	// 关闭所有客户端
	for _, client := range pm.clients {
		client.Close()
	}

	// 关闭 GeoIP 数据库
	pm.geoDB.Close()
}

// checkLoop 定期检查所有节点的状态
func (pm *ProxyManager) checkLoop() {
	ticker := time.NewTicker(time.Duration(pm.config.CheckInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-pm.ctx.Done():
			return
		case <-ticker.C:
			pm.checkNodes()
		}
	}
}

// checkNodes 并发检查所有节点
func (pm *ProxyManager) checkNodes() {
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, pm.config.ConcurrentChecks)

	for i := range pm.config.Nodes {
		node := &pm.config.Nodes[i]
		wg.Add(1)
		semaphore <- struct{}{}

		go func(node *ProxyNode) {
			defer wg.Done()
			defer func() { <-semaphore }()

			// 检查节点延迟和可用性
			latency, ip, err := pm.checkNode(node)

			pm.mutex.Lock()
			node.LastCheck = time.Now()
			node.Latency = latency

			if err != nil {
				node.FailCount++
				node.Available = false
				fmt.Printf("节点 %s 检查失败: %v\n", node.URI, err)
			} else {
				node.FailCount = 0
				node.Available = true

				// 更新 IP 地理位置信息
				if country, err := pm.getIPCountry(ip); err == nil {
					node.Country = country
				}

				fmt.Printf("节点 %d 检查成功: 国家：%s, 延迟：%v \n", node.LocalPort, node.Country, node.Latency)
			}
			pm.mutex.Unlock()

			// 如果当前节点不可用且失败次数超过阈值，切换到其他节点
			if node == pm.activeNode && !node.Available && node.FailCount >= pm.config.MaxFails {
				pm.switchToNextAvailableNode()
			}
		}(node)
	}

	wg.Wait()
}

// checkNode 检查单个节点的延迟和可用性
func (pm *ProxyManager) checkNode(node *ProxyNode) (time.Duration, string, error) {
	// 创建测试用的 HTTP 客户端
	httpClient := &http.Client{
		Transport: &http.Transport{
			Proxy: func(req *http.Request) (*url.URL, error) {
				return url.Parse(fmt.Sprintf("socks5://127.0.0.1:%d", node.LocalPort))
			},
		},
		Timeout: 5 * time.Second,
	}

	// log.Printf("正在检查节点: %s", node.URI)

	// 添加重试机制
	var lastErr error
	for retries := 0; retries < 3; retries++ {
		// 发送测试请求并计时
		start := time.Now()
		resp, err := httpClient.Get(pm.config.TestAPI)
		if err != nil {
			lastErr = err
			time.Sleep(time.Second * 2) // 失败后等待2秒再重试
			continue
		}
		defer resp.Body.Close()

		latency := time.Since(start)

		// 解析响应获取 IP
		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			lastErr = err
			continue
		}

		var ipResp IPResponse
		if err := json.Unmarshal(body, &ipResp); err != nil {
			lastErr = err
			continue
		}

		return latency, ipResp.IP, nil
	}

	return 0, "", fmt.Errorf("节点检查失败（重试3次）: %v", lastErr)
}

// switchToNextAvailableNode 切换到下一个可用节点
func (pm *ProxyManager) switchToNextAvailableNode() error {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	// 检查是否可以切换
	if pm.activeNode != nil {
		if time.Since(pm.activeNode.LastSwitchTime) < time.Duration(pm.config.SwitchCooldown)*time.Second {
			return fmt.Errorf("节点切换冷却中，请稍后再试")
		}
	}

	// 查找延迟最低的可用节点
	var bestNode *ProxyNode
	var bestLatency time.Duration = -1

	for i := range pm.config.Nodes {
		node := &pm.config.Nodes[i]
		if !node.Available || node == pm.activeNode {
			continue
		}
		if bestLatency == -1 || node.Latency < bestLatency {
			bestNode = node
			bestLatency = node.Latency
		}
	}

	if bestNode == nil {
		return fmt.Errorf("没有可用的节点")
	}

	// 切换到新节点
	if client, ok := pm.clients[bestNode.URI]; ok {
		go client.Run()
		bestNode.LastSwitchTime = time.Now()
		pm.activeNode = bestNode
		fmt.Printf("切换到节点 %s (延迟: %v)\n", bestNode.URI, bestNode.Latency)
		return nil
	}

	return fmt.Errorf("节点 %s 未初始化", bestNode.URI)
}

// getIPCountry 获取 IP 的国家信息
func (pm *ProxyManager) getIPCountry(ip string) (string, error) {
	parsedIP := net.ParseIP(ip)
	if parsedIP == nil {
		return "", fmt.Errorf("无效的 IP 地址")
	}

	record, err := pm.geoDB.Country(parsedIP)
	if err != nil {
		return "", err
	}

	return record.Country.Names["zh-CN"], nil
}
