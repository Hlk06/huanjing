@echo off
chcp 65001 >nul
echo.
echo   临床医学知识库
echo   部署到: https://medical.topkids.top
echo   账号: 736055468@qq.com
echo ============================================================
echo.

if not exist "%USERPROFILE%\cloudflared.exe" (
    echo [1/3] 下载 cloudflared...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;try{Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%USERPROFILE%\cloudflared.exe' -TimeoutSec 120}catch{exit 1}"
    if not exist "%USERPROFILE%\cloudflared.exe" (echo 下载失败,请手动下载后重试 & pause & exit /b 1)
)
echo [1/3] cloudflared OK

echo.
echo [2/3] 登录 Cloudflare (浏览器自动打开)
echo       输入: 736055468@qq.com 密码: Wr10040816/
echo.
"%USERPROFILE%\cloudflared.exe" tunnel login

echo.
echo [3/3] 创建 Tunnel 并绑定域名...
"%USERPROFILE%\cloudflared.exe" tunnel create topkids-kb
"%USERPROFILE%\cloudflared.exe" tunnel route dns topkids-kb medical.topkids.top

echo.
echo ============================================================
echo   Tunnel 已创建! 现在启动...
echo   公网地址: https://medical.topkids.top
echo   (确保 Flask 已在另一终端运行: python d:\医疗\app.py)
echo ============================================================
echo.
"%USERPROFILE%\cloudflared.exe" tunnel run topkids-kb
