"""
DeepAnalyze API 服务器数据模型
包含所有用于 OpenAI 兼容性的 Pydantic 模型
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class FileObject(BaseModel):
    """OpenAI 文件对象"""
    id: str
    object: Literal["file"] = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str


class FileDeleteResponse(BaseModel):
    """OpenAI 文件删除响应"""
    id: str
    object: Literal["file"] = "file"
    deleted: bool




class ThreadObject(BaseModel):
    """OpenAI 线程对象"""
    id: str
    object: Literal["thread"] = "thread"
    created_at: int
    last_accessed_at: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    file_ids: List[str] = Field(default_factory=list)
    tool_resources: Optional[Dict[str, Any]] = Field(default=None)


class MessageObject(BaseModel):
    """OpenAI 消息对象"""
    id: str
    object: Literal["thread.message"] = "thread.message"
    created_at: int
    thread_id: str
    role: Literal["user", "assistant"]
    content: List[Dict[str, Any]]
    file_ids: List[str] = Field(default_factory=list)
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatCompletionRequest(BaseModel):
    """对话补全请求模型"""
    model: str
    messages: List[Dict[str, Any]]
    file_ids: Optional[List[str]] = Field(default=None)
    temperature: Optional[float] = Field(0.4)
    stream: Optional[bool] = Field(False)


class FileInfo(BaseModel):
    """用于 OpenAI 兼容性的文件信息模型"""
    filename: str
    url: str


class ChatCompletionChoice(BaseModel):
    """对话补全选项模型"""
    index: int
    message: Dict[str, Any]
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """对话补全响应模型"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    generated_files: Optional[List[Dict[str, str]]] = Field(default=None)
    attached_files: Optional[List[str]] = Field(default=None)


class ChatCompletionChunk(BaseModel):
    """对话补全流式分块模型"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    generated_files: Optional[List[Dict[str, str]]] = Field(default=None)


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: int


class ThreadCleanupRequest(BaseModel):
    """Thread cleanup request model"""
    timeout_hours: int = Field(12, description="Timeout in hours for thread cleanup")


class ThreadCleanupResponse(BaseModel):
    """Thread cleanup response model"""
    status: str
    cleaned_threads: int
    timeout_hours: int
    timestamp: int


class ThreadStatsResponse(BaseModel):
    """Thread statistics response model"""
    total_threads: int
    recent_threads: int  # < 1 hour
    old_threads: int     # 1-12 hours
    expired_threads: int # > 12 hours
    timeout_hours: int
    timestamp: int


class ModelObject(BaseModel):
    """OpenAI Model Object"""
    id: str
    object: Literal["model"] = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None


class ModelsListResponse(BaseModel):
    """OpenAI Models List Response"""
    object: Literal["list"] = "list"
    data: List[ModelObject]