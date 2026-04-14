@echo off
chcp 65001 >nul
echo ========================================
echo 健康信息系统启动脚本
echo ========================================
echo.

REM 设置路径
set PROJECT_ROOT=%~dp0..
set REDIS_DIR=%PROJECT_ROOT%\Redis-x64-5.0.14.1

echo [信息] 项目目录: %PROJECT_ROOT%
echo.

REM 步骤 1: 启动 Redis
echo [步骤 1] 检查并启动 Redis 服务...
if not exist "%REDIS_DIR%\redis-server.exe" (
    echo [警告] 未找到 Redis 服务器，将使用内存缓存模式
    goto start_app
)

REM 检查 Redis 是否已在运行
tasklist | findstr "redis-server.exe" >nul
if %errorlevel% == 0 (
    echo [信息] Redis 服务已在运行
) else (
    echo [信息] 正在启动 Redis 服务...
    start "Redis Server" /min "%REDIS_DIR%\redis-server.exe" "%REDIS_DIR%\redis.windows.conf"
    timeout /t 2 /nobreak >nul
    echo [成功] Redis 服务已启动
)
echo.

REM 步骤 2: 测试 Redis 连接
echo [步骤 2] 测试 Redis 连接...
cd /d "%PROJECT_ROOT%"
python scripts\test_redis.py
if %errorlevel% neq 0 (
    echo [警告] Redis 连接测试未通过，应用将使用内存缓存模式
)
echo.

:start_app
REM 步骤 3: 启动主应用
echo [步骤 3] 启动 FastAPI 主应用...
echo [信息] 访问地址: http://127.0.0.1:8000
echo [信息] API 文档: http://127.0.0.1:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause
