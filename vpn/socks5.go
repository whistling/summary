package main

//
// import (
// 	"fmt"
// 	"io/ioutil"
// 	"net/http"
// 	"net/url"
// 	"time"
// )
//
// func main5() {
// 	// trojanURL := "trojan://9BpyF9uRr9fvyUZT8B@fw-jp-test1.trojanwheel.com:5011" //
// 	// trojanURL := "http://9BpyF9uRr9fvyUZT8B@fw-jp-test1.trojanwheel.com:5011" //
//
// 	trojanURL := "socks5://127.0.0.1:1080"
// 	proxyURL, err := url.Parse(trojanURL)
// 	if err != nil {
// 		fmt.Println("解析 Trojan URL 失败:", err)
// 		return
// 	}
//
// 	fmt.Println("正在使用 Trojan 代理", proxyURL)
//
// 	// 创建一个 http.Transport，并设置 Proxy 为 Trojan 代理
// 	transport := &http.Transport{
// 		Proxy: http.ProxyURL(proxyURL),
// 		// 可以根据需要配置更多 Transport 参数，例如 TLSClientConfig, DialContext 等
// 	}
//
// 	// 创建一个 http.Client，使用自定义的 Transport
// 	client := &http.Client{
// 		Transport: transport,
// 		Timeout:   15 * time.Second, // 设置请求超时时间
// 	}
//
// 	// 发送 GET 请求到 https://apiip.net/，验证代理是否生效
// 	resp, err := client.Get("https://apiip.net/ip")
// 	if err != nil {
// 		fmt.Println("GET 请求失败:", err)
// 		return
// 	}
// 	defer resp.Body.Close()
//
// 	body, err := ioutil.ReadAll(resp.Body)
// 	if err != nil {
// 		fmt.Println("读取响应失败:", err)
// 		return
// 	}
//
// 	fmt.Println("响应状态码:", resp.StatusCode)
// 	fmt.Println("响应内容:")
// 	fmt.Println(string(body))
// }
