"""配置数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any


@dataclass
class RepositoryConfig:
    """仓库配置"""
    name: str
    type: str  # "github" 或 "gitlab"
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: str = "main"
    token: Optional[str] = None
    # GitLab 特定字段
    project_id: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class OllamaConfig:
    """Ollama 配置"""
    base_url: str = "http://localhost:11434"
    model: str = "llama2"
    system_prompt: str = "你是一个代码仓库分析助手"
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class PushServiceConfig:
    """推送服务配置"""
    type: str  # "serverchan" 或 "webhook"
    sendkey: Optional[str] = None
    webhook_url: Optional[str] = None


@dataclass
class PushConfig:
    """推送配置"""
    services: List[PushServiceConfig] = field(default_factory=list)


@dataclass
class ScheduleConfig:
    """调度配置"""
    cron: str
    repositories: List[str] = field(default_factory=list)


@dataclass
class AppConfig:
    """应用主配置"""
    repositories: List[RepositoryConfig] = field(default_factory=list)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    push: PushConfig = field(default_factory=PushConfig)
    schedules: List[ScheduleConfig] = field(default_factory=list)
    log_level: str = "INFO"
    cache_dir: str = "./cache"