package main

import (
	"encoding/json"
	"fmt"
	"github.com/p4gefau1t/trojan-go/easy"
	"github.com/p4gefau1t/trojan-go/proxy"
	_ "github.com/p4gefau1t/trojan-go/proxy/client"
	"net/url"
	"strconv"
)

// "trojan://9BpyF9uRr9fvyUZT8B@us-2.regentgrandvalley.com:443"
func getProxyClient(uri string, localPort int) (*proxy.Proxy, error) {
	// 解析 trojan URI
	u, err := url.Parse(uri)
	if err != nil {
		return nil, fmt.Errorf("解析 URI 失败: %v", err)
	}

	if u.Scheme != "trojan" {
		return nil, fmt.Errorf("不支持的协议: %s", u.Scheme)
	}

	// 从 URI 中提取信息
	password := u.User.Username()
	host := u.Hostname()
	port, _ := strconv.Atoi(u.Port())

	// 构建客户端配置
	clientConfig := easy.ClientConfig{
		RunType:    "client",
		LocalAddr:  "127.0.0.1", // 默认本地监听地址
		LocalPort:  localPort,   // 使用传入的本地端口
		RemoteAddr: host,
		RemotePort: port,
		Password: []string{
			password,
		},
	}
	fmt.Printf("clientConfig: %+v\n", clientConfig)
	// 转换为 JSON 配置
	clientConfigJSON, err := json.Marshal(&clientConfig)
	if err != nil {
		return nil, fmt.Errorf("生成配置 JSON 失败: %v", err)
	}

	// 创建代理实例
	proxyClient, err := proxy.NewProxyFromConfigData(clientConfigJSON, true)
	if err != nil {
		return nil, fmt.Errorf("创建代理实例失败: %v", err)
	}

	return proxyClient, nil
}
