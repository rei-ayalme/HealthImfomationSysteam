#!/usr/bin/env python3
"""
简单流式对话测试脚本
支持带文件和不带文件的流式对话
"""

import openai
import os
import sys
import tempfile
import shutil
import requests
import zipfile
import subprocess
import threading
import time
from pathlib import Path

# 默认配置
DEFAULT_API_BASE = os.getenv("DA_QUICKSTART_API_BASE", "http://localhost:8200/v1")
DEFAULT_MODEL = os.getenv("DA_QUICKSTART_MODEL", "deepanalyze-8b")

# 全局客户端变量
client = None


def check_api_server_connection(api_base):
    """检查 API 服务器连接"""
    try:
        response = requests.get(f"{api_base}/models", timeout=3)
        return response.status_code == 200
    except:
        return False


def start_api_server():
    """在后台启动 API 服务器"""
    script_dir = Path(__file__).parent
    main_py = script_dir / "main.py"
    
    if not main_py.exists():
        return None
    
    try:
        # 在后台启动服务器，静默输出
        kwargs = {
            "cwd": str(script_dir),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            [sys.executable, str(main_py)],
            **kwargs
        )
        return process
    except:
        return None


def wait_for_server(api_base, max_wait=30, server_process=None):
    """等待服务器启动；显示进度以免控制台看起来卡住"""
    for i in range(max_wait):
        if server_process is not None and server_process.poll() is not None:
            code = server_process.returncode
            print(
                f"\n❌ API server process exited early (code {code}). "
                "Run `python main.py` in another terminal to see the error."
            )
            return False
        if check_api_server_connection(api_base):
            if i > 0:
                print()
            return True
        # 单行更新，保持输出可读
        print(f"\rWaiting for API at {api_base}... {i + 1}s / {max_wait}s", end="", flush=True)
        time.sleep(1)
    print()
    return False


def get_supported_file_extensions():
    """支持的文件扩展名"""
    return [
        '.csv', '.txt', '.json', '.xlsx', '.xls', 
        '.pdf', '.doc', '.docx', '.py', '.js', '.html',
        '.xml', '.yaml', '.yml', '.md', '.log'
    ]


def is_supported_file(file_path):
    """检查文件类型是否受支持"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in get_supported_file_extensions()


def extract_zip_file(zip_path, extract_to):
    """将 ZIP 文件解压到目标目录"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            zip_ref.extractall(extract_to)
            
            extracted_files = []
            for file_name in file_list:
                if not file_name.endswith('/'):
                    file_path = os.path.join(extract_to, file_name)
                    if os.path.exists(file_path):
                        extracted_files.append(file_path)
            
            return extracted_files
    except:
        return []


def download_file_from_url(url, filename, temp_dir):
    """从 URL 下载文件到临时目录"""
    try:
        file_path = os.path.join(temp_dir, filename)
        response = requests.get(url, stream=True)
        
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return file_path
        return None
    except:
        return None


def process_streaming_chat(uploaded_files, user_instruction, api_key):
    """运行流式对话分析"""
    global client
    
    # 初始化客户端
    client = openai.OpenAI(
        base_url=DEFAULT_API_BASE,
        api_key=api_key,
    )
    
    print("🔄 开始分析...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    files_to_upload = []
    file_objects = []
    supported_extensions = get_supported_file_extensions()
    
    try:
        # 处理上传的文件
        if uploaded_files:
            for file_path in uploaded_files:
                if not os.path.exists(file_path):
                    continue
                
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_name)[1].lower()
                
                # 检查 ZIP 文件
                if file_ext == '.zip':
                    extract_dir = os.path.join(temp_dir, f"extracted_{os.path.splitext(file_name)[0]}")
                    os.makedirs(extract_dir, exist_ok=True)
                    extracted_files = extract_zip_file(file_path, extract_dir)
                    
                    if extracted_files:
                        for extracted_file in extracted_files:
                            extracted_name = os.path.basename(extracted_file)
                            extracted_ext = os.path.splitext(extracted_name)[1].lower()
                            
                            if extracted_ext in supported_extensions:
                                dest_path = os.path.join(temp_dir, extracted_name)
                                counter = 1
                                while os.path.exists(dest_path):
                                    name, ext = os.path.splitext(extracted_name)
                                    dest_path = os.path.join(temp_dir, f"{name}_{counter}{ext}")
                                    counter += 1
                                
                                shutil.copy2(extracted_file, dest_path)
                                files_to_upload.append(dest_path)
                else:
                    if file_ext in supported_extensions:
                        dest_path = os.path.join(temp_dir, file_name)
                        shutil.copy2(file_path, dest_path)
                        files_to_upload.append(dest_path)
            
            # 上传文件到 API
            for file_path in files_to_upload:
                try:
                    with open(file_path, "rb") as f:
                        file_obj = client.files.create(file=f, purpose="file-extract")
                        file_objects.append(file_obj)
                except:
                    pass
        
        file_names = [os.path.basename(path) for path in files_to_upload]
        
        # 使用提供的或默认的指令
        if not user_instruction.strip():
            if files_to_upload:
                user_instruction = (
                    f"请分析以下数据文件 {', '.join(file_names)}, "
                    "执行探索性数据分析（EDA）并生成可视化。关注关系、趋势和关键洞察。"
                )
            else:
                user_instruction = "请进行对话式分析并提供详细洞察。"
        
        print("\n" + "=" * 60)
        
        # 构建消息
        if files_to_upload:
            messages = [
                {
                    "role": "user",
                    "content": user_instruction,
                    "file_ids": [file_obj.id for file_obj in file_objects],
                }
            ]
        else:
            messages = [{"role": "user", "content": user_instruction}]
        
        # 通过 extra_body 传递 api_key
        extra_body = {"api_key": api_key} if api_key else {}
        
        # 创建流式请求
        try:
            stream = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                stream=True,
                extra_body=extra_body,
            )
        except openai.InternalServerError as e:
            raise Exception(f"❌ API 服务器错误: {e}")
        except openai.APIError as e:
            raise Exception(f"❌ API 错误: {e}")
        except Exception as e:
            raise Exception(f"❌ Connection error: {e}")
        
        full_response = ""
        collected_files = []
        downloadable_files = []
        
        # 流式输出
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content
            
            if hasattr(chunk, "generated_files") and chunk.generated_files:
                collected_files.extend(chunk.generated_files)
        
        print("\n" + "=" * 60)
        
        # 下载生成的文件
        if collected_files:
            for file_info in collected_files:
                filename = file_info.get("name", f"generated_{len(downloadable_files)}.txt")
                url = file_info.get("url", "")
                if url:
                    local_path = download_file_from_url(url, filename, temp_dir)
                    if local_path:
                        downloadable_files.append(local_path)
        
        print(f"\n✅ 分析完成（生成文件数: {len(collected_files)}）")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
    finally:
        # 清理临时文件（可选）
        # if temp_dir and os.path.exists(temp_dir):
        #     shutil.rmtree(temp_dir)
        pass


def main():
    """入口点"""
    # 检查并在需要时启动 API 服务器
    if not check_api_server_connection(DEFAULT_API_BASE):
        print("正在启动 API 服务器...")
        server_process = start_api_server()
        if server_process:
            if wait_for_server(DEFAULT_API_BASE, server_process=server_process):
                print("✅ API 服务器已启动")
            else:
                print("❌ API 服务器启动失败")
                return
        else:
            print("❌ 无法启动 API 服务器")
            return
    else:
        print("✅ API 服务器已在运行")
    
    # 输入 API 密钥
    api_key = input("\n请输入 API 密钥: ").strip()
    if not api_key:
        print("❌ API 密钥是必需的")
        return
    
    # 选择模式
    print("\n选择对话类型:")
    print("  1. 无文件对话")
    print("  2. 带文件对话")
    choice = input("\n请输入选择 (1 或 2): ").strip()
    
    uploaded_files = []
    if choice == "2":
        file_input = input("\n请输入文件路径（逗号分隔）: ").strip()
        if file_input:
            uploaded_files = [f.strip() for f in file_input.split(',') if f.strip()]
    
    # 输入指令
    user_instruction = input("\n请输入分析指令（留空使用默认）: ").strip()
    
    # 开始流式对话
    try:
        process_streaming_chat(uploaded_files, user_instruction, api_key)
    except KeyboardInterrupt:
        print("\n\n⏹️  已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
