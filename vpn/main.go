package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	// 使用独立的FlagSet来避免与trojan-go包的flag冲突
	flags := flag.NewFlagSet("vpn", flag.ExitOnError)
	configPath := flags.String("config", "config.json", "配置文件路径")
	flags.Parse(os.Args[1:])

	// 加载配置文件
	config, err := LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("加载配置文件失败: %v", err)
	}

	// 创建代理管理器
	manager, err := NewProxyManager(config)
	if err != nil {
		log.Fatalf("创建代理管理器失败: %v", err)
	}

	// 启动代理管理器
	if err := manager.Start(); err != nil {
		log.Fatalf("启动代理管理器失败: %v", err)
	}

	// 等待中断信号
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// 打印启动信息
	fmt.Println("代理管理器已启动，按 Ctrl+C 停止...")

	// 等待中断信号
	<-sigChan

	// 优雅关闭
	fmt.Println("\n正在关闭代理管理器...")
	manager.Stop()
	fmt.Println("代理管理器已关闭")
}
