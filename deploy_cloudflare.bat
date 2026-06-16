@echo off
chcp 65001 >nul
echo ============================================================
echo   临床医学知识库 - Cloudflare Tunnel 部署
echo ============================================================

REM Step 1: Download cloudflared
if not exist "%USERPROFILE%\cloudflared.exe" (
    echo [1/3] 下载 cloudflared (首次约30秒)...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%USERPROFILE%\cloudflared.exe'" 2>nul
    if not exist "%USERPROFILE%\cloudflared.exe" (
        echo 下载失败! 请手动下载:
        echo https://github.com/cloudflare/cloudflared/releases
        echo 放到 %USERPROFILE%\cloudflared.exe
        pause
        exit /b 1
    )
)
echo [1/3] cloudflared 就绪

REM Step 2: Login (opens browser)
echo [2/3] 打开浏览器登录 Cloudflare (选择你的域名)...
"%USERPROFILE%\cloudflared.exe" tunnel login

REM Step 3: Create tunnel and run
echo [3/3] 创建 Tunnel 并启动...
"%USERPROFILE%\cloudflared.exe" tunnel create medical-kb 2>nul

echo.
echo ============================================================
echo   部署成功! 将以下域名添加到 Cloudflare DNS:
echo   类型: CNAME
echo   名称: medical (或自定义子域名)
echo   目标: [Tunnel-ID].cfargotunnel.com
echo ============================================================
echo.
echo   启动本地 Flask 后, 在新终端运行:
echo   python d:\医疗\app.py
echo.
echo   本终端启动 Tunnel:
echo   %USERPROFILE%\cloudflared.exe tunnel run medical-kb
echo.
echo   按任意键启动 Tunnel...
pause >nul
"%USERPROFILE%\cloudflared.exe" tunnel run medical-kb
