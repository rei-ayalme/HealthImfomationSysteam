# 流式聊天测试工具 - 本地调试教程

## 📖 项目简介

`quick_start.py` 是一个流式聊天测试脚本，支持与本地API服务器进行交互式对话。该工具可以处理多种文件格式，支持数据分析、可视化生成等功能。

## ✨ 主要功能

- 🔄 **流式对话**：实时显示AI响应内容
- 📁 **文件支持**：支持多种文件格式（CSV、TXT、JSON、Excel、PDF等）
- 📦 **ZIP解压**：自动解压ZIP文件并处理其中的支持文件
- 🚀 **自动启动**：自动检测并启动API服务器（如果未运行）
- 📊 **数据分析**：支持数据探索性分析（EDA）和可视化生成

## 🔧 环境要求

### 必需依赖

- Python 3.7+
- OpenAI Python SDK
- requests 库

### 安装依赖

```bash
pip install openai requests
```

或者使用requirements.txt（如果存在）：

```bash
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. 准备工作

确保你的工作目录包含以下文件：
- `quick_start.py` - 主脚本文件
- `main.py` - API服务器文件（可选，脚本会自动检测）
- `Simpson.csv` - 示例CSV数据文件
- `example.zip` - 示例ZIP压缩文件

### 2. 启动脚本

在终端中运行：

```bash
python quick_start.py
```

### 3. 交互式使用

脚本启动后，按照提示进行操作：

#### 步骤1：输入API密钥
```
Enter API Key: your_api_key_here
```

#### 步骤2：选择对话类型
```
Select dialog type:
  1. No-file dialog
  2. Dialog with files

Enter choice (1 or 2): 
```

#### 步骤3：输入文件路径（如果选择了选项2）
```
Enter file paths (comma separated): 
```

#### 步骤4：输入分析指令（可选）
```
Enter analysis instruction (blank for default): 
```

## 📝 使用示例

### 示例1：使用CSV文件进行分析

**场景**：分析 `Simpson.csv` 数据文件

**操作步骤**：

1. 运行脚本：
   ```bash
   python quick_start.py
   ```

2. 输入API密钥：
   ```
   Enter API Key: your_api_key
   ```

3. 选择对话类型：
   ```
   Enter choice (1 or 2): 2
   ```

4. 输入文件路径：
   ```
   Enter file paths (comma separated): Simpson.csv
   ```
   
   或者使用绝对路径：
   ```
   Enter file paths (comma separated): D:\da_gradio\test\Simpson.csv
   ```

5. 输入分析指令（可选）：
   ```
   Enter analysis instruction (blank for default): 
   ```
   
   如果留空，将使用默认指令：分析数据文件，执行EDA，并生成可视化。

**预期输出**：
- 脚本会自动上传文件到API服务器
- 实时流式显示分析结果
- 如果生成了可视化文件，会显示生成的文件数量

### 示例2：使用ZIP压缩文件

**场景**：分析 `example.zip` 压缩包中的文件

**操作步骤**：

1. 运行脚本：
   ```bash
   python quick_start.py
   ```

2. 输入API密钥：
   ```
   Enter API Key: your_api_key
   ```

3. 选择对话类型：
   ```
   Enter choice (1 or 2): 2
   ```

4. 输入ZIP文件路径：
   ```
   Enter file paths (comma separated): example.zip
   ```

5. 输入自定义分析指令（可选）：
   ```
   Enter analysis instruction (blank for default): 请分析压缩包中的所有文件，找出关键模式和异常值
   ```

**注意事项**：
- ZIP文件会自动解压
- 只处理支持的文件格式（见下方支持格式列表）
- 如果ZIP中包含多个文件，所有支持的文件都会被上传分析

### 示例3：无文件对话

**场景**：进行普通对话，不分析文件

**操作步骤**：

1. 运行脚本：
   ```bash
   python quick_start.py
   ```

2. 输入API密钥：
   ```
   Enter API Key: your_api_key
   ```

3. 选择对话类型：
   ```
   Enter choice (1 or 2): 1
   ```

4. 输入对话指令：
   ```
   Enter analysis instruction (blank for default): 请解释一下什么是机器学习
   ```

## 📋 支持的文件格式

脚本支持以下文件格式：

| 格式 | 扩展名 |
|------|--------|
| CSV数据 | `.csv` |
| 文本文件 | `.txt` |
| JSON数据 | `.json` |
| Excel表格 | `.xlsx`, `.xls` |
| PDF文档 | `.pdf` |
| Word文档 | `.doc`, `.docx` |
| 代码文件 | `.py`, `.js`, `.html` |
| 配置文件 | `.xml`, `.yaml`, `.yml` |
| Markdown | `.md` |
| 日志文件 | `.log` |

## ⚙️ 配置说明

### API服务器配置

脚本默认配置：
- **API地址**：`http://localhost:8200/v1`
- **模型名称**：`deepanalyze-8b`

如需修改，请编辑 `quick_start.py` 文件中的以下变量：

```python
DEFAULT_API_BASE = "http://localhost:8200/v1"
DEFAULT_MODEL = "deepanalyze-8b"
```

### 自动启动服务器

如果检测到 `main.py` 文件存在，脚本会自动尝试启动API服务器。服务器启动过程：
1. 检查服务器是否已运行
2. 如果未运行，尝试启动 `main.py`
3. 等待最多30秒，直到服务器就绪

## 🔍 常见问题排查

### 问题1：API服务器连接失败

**错误信息**：
```
❌ API server failed to start
```

**解决方案**：
1. 检查API服务器是否在运行：
   ```bash
   # 检查端口8200是否被占用
   netstat -an | findstr 8200  # Windows
   lsof -i :8200  # Linux/Mac
   ```

2. 手动启动API服务器：
   ```bash
   python main.py
   ```

3. 检查 `main.py` 文件是否存在且可执行

### 问题2：文件上传失败

**错误信息**：
```
❌ API error: ...
```

**解决方案**：
1. 检查文件路径是否正确（支持相对路径和绝对路径）
2. 确认文件格式在支持列表中
3. 检查文件是否损坏或无法读取
4. 验证API密钥是否有效

### 问题3：ZIP文件解压失败

**解决方案**：
1. 确认ZIP文件未损坏
2. 检查ZIP文件是否包含支持的文件格式
3. 查看临时目录权限（脚本会在系统临时目录创建解压文件夹）

### 问题4：流式输出中断

**解决方案**：
1. 检查网络连接
2. 确认API服务器正常运行
3. 查看服务器日志获取详细错误信息

### 问题5：Windows系统下脚本无法启动服务器

**解决方案**：
- 确保Python已正确安装
- 检查 `main.py` 文件是否存在
- 尝试手动运行 `python main.py` 查看错误信息

## 💡 使用技巧

### 1. 批量文件分析

可以同时分析多个文件，用逗号分隔：

```
Enter file paths (comma separated): Simpson.csv, example.zip, data.json
```

### 2. 自定义分析指令

提供具体的分析需求可以获得更好的结果：

```
Enter analysis instruction (blank for default): 
请分析Simpson.csv中的treatment和success之间的关系，并生成相关性分析报告
```

### 3. 文件路径格式

- **相对路径**：`Simpson.csv`（相对于脚本所在目录）
- **绝对路径**：`D:\da_gradio\test\Simpson.csv`（Windows）或 `/path/to/file.csv`（Linux/Mac）

### 4. 中断执行

按 `Ctrl+C` 可以随时中断脚本执行。

## 📊 输出说明

### 成功输出示例

```
✅ API server already running

Enter API Key: ***

Select dialog type:
  1. No-file dialog
  2. Dialog with files

Enter choice (1 or 2): 2

Enter file paths (comma separated): Simpson.csv

Enter analysis instruction (blank for default): 

🔄 Starting analysis...
============================================================
[流式输出分析结果...]
============================================================

✅ Analysis complete (generated files: 2)
```

### 生成的文件

如果分析过程中生成了文件（如可视化图表），这些文件会保存在系统临时目录中。脚本会显示生成的文件数量。

## 🔐 安全提示

- **API密钥安全**：不要在代码中硬编码API密钥
- **文件权限**：确保脚本有读取输入文件的权限
- **临时文件**：脚本会在临时目录创建文件，注意清理敏感数据

## 📚 进阶使用

### 修改默认分析指令

编辑 `quick_start.py` 中的默认指令：

```python
if files_to_upload:
    user_instruction = (
        f"Please analyze the following data files {', '.join(file_names)}, "
        "perform EDA, and generate visualizations. Focus on relationships, trends, and key insights."
    )
```

### 添加新的文件格式支持

在 `get_supported_file_extensions()` 函数中添加新的扩展名：

```python
def get_supported_file_extensions():
    return [
        '.csv', '.txt', '.json', '.xlsx', '.xls', 
        '.pdf', '.doc', '.docx', '.py', '.js', '.html',
        '.xml', '.yaml', '.yml', '.md', '.log',
        '.your_extension'  # 添加新格式
    ]
```

## 📞 获取帮助

如果遇到问题：
1. 检查本文档的"常见问题排查"部分
2. 查看脚本输出的错误信息
3. 检查API服务器日志
4. 确认所有依赖已正确安装

## 📄 许可证

请根据项目实际情况添加许可证信息。

---

**祝您使用愉快！** 🎉

