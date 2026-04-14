@echo off
chcp 65001 >nul
echo ========================================
echo Redis 服务启动脚本
echo ========================================
echo.

REM 设置 Redis 目录
set REDIS_DIR=%~dp0..\Redis-x64-5.0.14.1

REM 检查 Redis 目录是否存在
if not exist "%REDIS_DIR%\redis-server.exe" (
    echo [错误] 未找到 Redis 服务器程序！
    echo 请确保 Redis-x64-5.0.14.1 目录存在于项目根目录下。
    pause
    exit /b 1
)

echo [信息] Redis 目录: %REDIS_DIR%
echo [信息] 正在启动 Redis 服务...
echo.

REM 启动 Redis 服务
cd /d "%REDIS_DIR%"
start "Redis Server" redis-server.exe redis.windows.conf

echo [成功] Redis 服务已启动！
echo [信息] 默认监听地址: 127.0.0.1:6379
echo.
echo 提示：
echo - 请勿关闭 Redis 服务窗口
echo - 如需停止服务，请在 Redis 窗口中按 Ctrl+C
echo - 或运行 redis-cli.exe shutdown 命令
echo.
pause
