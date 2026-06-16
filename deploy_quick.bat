@echo off
chcp 65001 >nul
echo ============================================================
echo   临床医学知识库 - Cloudflare 快速隧道 (无需登录)
echo   生成随机 *.trycloudflare.com 域名, 即时可用
echo ============================================================
echo.
echo   先确保 Flask 已启动: python d:\医疗\app.py
echo.
echo   启动隧道...
if exist "%USERPROFILE%\cloudflared.exe" (
    "%USERPROFILE%\cloudflared.exe" tunnel --url http://localhost:5000
) else (
    echo cloudflared 未下载!
    echo 请先运行 deploy_cloudflare.bat 下载
    echo 或手动下载: https://github.com/cloudflare/cloudflared/releases
)
pause
