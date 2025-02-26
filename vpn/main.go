package main

import (
	"fmt"
	"net/url"

	"golang.org/x/net/proxy"
)

// 检测vpn 是否可用
func checkSocks5Proxy(proxyAddr, proxyPort, username, password string) error {
	proxyURL, err := url.Parse(fmt.Sprintf("socks5://%s:%s@%s:%s", username, password, proxyAddr, proxyPort))
	if err != nil {
		return err
	}

	dialer, err := proxy.FromURL(proxyURL, proxy.Direct)
	if err != nil {
		return err
	}
	// ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	// defer cancel()
	// Replace DialContext with Dial since proxy.Dialer doesn't support DialContext
	conn, err := dialer.Dial("tcp", "www.google.com:80")
	if err != nil {
		return err
	}
	defer conn.Close()

	fmt.Println("Socks5 proxy connection successful!")
	return nil
}

func main() {
	proxyAddr := "127.0.0.1" // 替换为你的代理地址
	proxyPort := "7890"      // 替换为你的代理端口
	username := ""           // 替换为你的代理用户名
	password := ""           // 替换为你的代理密码

	err := checkSocks5Proxy(proxyAddr, proxyPort, username, password)
	if err != nil {
		fmt.Println("Socks5 proxy connection failed:", err)
	}
}
