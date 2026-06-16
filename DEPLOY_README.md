# 临床医学知识库 — Cloudflare 部署指南

## 域名
- **域名**: topkids.top
- **目标地址**: medical.topkids.top
- **Cloudflare 账号**: 736055468@qq.com

## 一键部署 (推荐)

### 步骤 1: 获取 Global API Key
1. 浏览器打开: https://dash.cloudflare.com/profile/api-tokens
2. 登录账号: 736055468@qq.com / Wr10040816/
3. 找到 **Global API Key** → 点击 **View** → 输入密码 → 复制 Key

### 步骤 2: 确保 Flask 已启动
```bash
python d:\医疗\app.py
```

### 步骤 3: 运行部署脚本
```bash
python d:\医疗\cloudflare_deploy.py
```
输入 Global API Key → 自动配置 DNS → 完成!

### 步骤 4: 路由器设置端口转发 (如需要)
- 外部端口: 443 → 内部: 192.168.0.178:5000
- 外部端口: 80 → 内部: 192.168.0.178:5000

## 访问
- **公网**: https://medical.topkids.top (Cloudflare CDN + SSL)
- **本地**: http://localhost:5000
- **手机**: http://192.168.0.178:5000

## 备用方案 (手动 DNS)
如果 API Key 方案不可用:
1. 登录 https://dash.cloudflare.com → 选择 topkids.top
2. DNS → 添加记录:
   - 类型: A
   - 名称: medical
   - 内容: 你的公网IP (访问 https://api.ipify.org 获取)
   - 代理: 开启 (橙色云朵)
3. 保存 → 等待 1-5 分钟生效
