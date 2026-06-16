# 临床医学知识库 · Cloudflare 部署指南

## 前置准备

### 1. 下载 cloudflared (一次性)

由于当前网络 GitHub 受限，请在**手机热点**或其他网络环境下载:

📥 **下载地址**: 
```
https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
```

下载后放到 `C:\Users\青城\cloudflared.exe`

### 2. 启动 Flask 应用

```bash
python d:\医疗\app.py
```

输出:
```
  本地访问: http://127.0.0.1:5000
  手机访问: http://192.168.0.178:5000
```

### 3. 运行 Cloudflare Tunnel

```bash
d:\医療\setup_tunnel.bat
```

按提示操作:
1. 浏览器弹出 → 登录 `736055468@qq.com`
2. 选择要使用的域名
3. 授权 Tunnel 访问

## 部署后访问

| 方式 | 地址 |
|------|------|
| 本地 | `http://127.0.0.1:5000` |
| 公网 | `https://medical.你的域名.com` (配置DNS后) |
| 临时 | `https://xxx.trycloudflare.com` (快速隧道) |

## 快速测试 (无需域名)

```bash
C:\Users\青城\cloudflared.exe tunnel --url http://localhost:5000
```

立即生成一个 `*.trycloudflare.com` 临时公网地址。

## 开机自启 (可选)

创建 `C:\Users\青城\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\tunnel.bat`:

```batch
@echo off
start /b python d:\医疗\app.py
timeout /t 5
C:\Users\青城\cloudflared.exe tunnel run medical-kb
```
