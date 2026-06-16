@echo off
chcp 65001 >nul
title 临床医学知识库 - Cloudflare Tunnel
echo ============================================================
echo   临床医学知识库 · Cloudflare Tunnel 部署
echo   账户: 736055468@qq.com
echo ============================================================
echo.

REM Step 1: cloudflared
SET CF=%USERPROFILE%\cloudflared.exe
if not exist "%CF%" (
    echo [1/4] 下载 cloudflared...
    powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CF%' -TimeoutSec 120 } catch { Write-Host 'Download failed - please download manually from:' ; Write-Host 'https://github.com/cloudflare/cloudflared/releases' }"
    if not exist "%CF%" (
        echo.
        echo ❌ cloudflared 下载失败 (网络受限)
        echo.
        echo 请在其他网络环境下手动下载:
        echo   https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
        echo   保存到: %CF%
        echo   然后重新运行此脚本
        pause
        exit /b 1
    )
)
echo [1/4] cloudflared ✓

REM Step 2: Login
echo [2/4] 登录 Cloudflare (浏览器将打开, 请登录 736055468@qq.com)...
"%CF%" tunnel login
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 登录失败, 请检查网络连接
    pause
    exit /b 1
)
echo [2/4] 登录成功 ✓

REM Step 3: Create tunnel
echo [3/4] 创建 Tunnel...
"%CF%" tunnel create medical-kb 2>nul
echo [3/4] Tunnel 创建完成 ✓

REM Step 4: Route DNS
echo [4/4] 配置 DNS 路由...
echo   在 Cloudflare Dashboard 中添加 CNAME 记录:
echo   类型: CNAME
echo   名称: medical   (或你想要的子域名)
echo   目标: [复制上方输出的 Tunnel ID].cfargotunnel.com
echo.
echo   或使用命令行自动配置 (需开启 Cloudflare API Token):
echo   %CF% tunnel route dns medical-kb medical.你的域名.com
echo.
echo ============================================================
echo   ✅ 配置完成!
echo ============================================================
echo.
echo   启动方式:
echo   终端1: python d:\医疗\app.py
echo   终端2: %CF% tunnel run medical-kb
echo.
echo   公网地址: https://medical.你的域名.com
echo ============================================================
pause
