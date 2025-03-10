package main

import (
	"encoding/json"
	"os"
	"time"
)

// ProxyNode 代表一个代理节点的配置信息
type ProxyNode struct {
	URI            string        `json:"uri"`         // Trojan URI
	LastCheck      time.Time     `json:"last_check"`  // 最后一次检查时间
	Latency        time.Duration `json:"latency"`     // 延迟
	Available      bool          `json:"available"`   // 是否可用
	FailCount      int           `json:"fail_count"`  // 连续失败次数
	Country        string        `json:"country"`     // 节点所在国家
	LastSwitchTime time.Time     `json:"switch_time"` // 最后一次切换时间
	LocalPort      int           `json:"local_port"`  // 本地分配的端口
}

// Config 包含所有配置信息
type Config struct {
	Nodes            []ProxyNode `json:"nodes"`             // 代理节点列表
	CheckInterval    int         `json:"check_interval"`    // 检查间隔(秒)
	MaxFails         int         `json:"max_fails"`         // 最大失败次数
	SwitchCooldown   int         `json:"switch_cooldown"`   // 切换冷却时间(秒)
	ConcurrentChecks int         `json:"concurrent_checks"` // 并发检查数
	TestAPI          string      `json:"test_api"`          // 测试 API
	LocalPort        int         `json:"local_port"`        // 本地 SOCKS5 端口
}

// LoadConfig 从文件加载配置
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	// 设置默认值
	if config.CheckInterval == 0 {
		config.CheckInterval = 60 // 默认60秒检查一次
	}
	if config.MaxFails == 0 {
		config.MaxFails = 3 // 默认连续失败3次切换节点
	}
	if config.SwitchCooldown == 0 {
		config.SwitchCooldown = 300 // 默认5分钟冷却时间
	}
	if config.ConcurrentChecks == 0 {
		config.ConcurrentChecks = 3 // 默认并发检查3个节点
	}
	if config.TestAPI == "" {
		config.TestAPI = "https://api.ipify.org/?format=json"
	}
	if config.LocalPort == 0 {
		config.LocalPort = 1080
	}

	return &config, nil
}
