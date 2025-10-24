"""配置数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Literal


@dataclass
class RepositoryConfig:
    """仓库配置"""
    name: str
    type: str  # "github" 或 "gitlab"
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: Optional[str] = None
    token: Optional[str] = None
    jobs: Dict[str, str] = field(default_factory=dict)
    # GitLab 特定字段
    base_url: Optional[str] = None
    


@dataclass
class LlmProcessorConfig:
    """大语言模型文本处理配置"""
    type : Literal["ollama", "openai"] = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama2"
    system_prompt: str = "你是一个代码仓库分析助手"
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class PushServiceConfig:
    """推送服务配置"""
    type: str # 目前只支持serverchan
    configs: Dict[str, str] = field(default_factory=dict)

@dataclass
class AppConfig:
    """应用主配置"""
    repositories: List[RepositoryConfig] = field(default_factory=list)
    processors: List[LlmProcessorConfig] = field(default_factory=list)
    push_services: List[PushServiceConfig] = field(default_factory=list)
    log_level: str = "INFO"
    cache_dir: str = "./cache"