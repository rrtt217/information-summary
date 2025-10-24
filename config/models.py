"""配置数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Literal


@dataclass
class RepositoryConfig:
    """仓库配置"""
    identifier: str
    type: str  # "github" 或 "gitlab"
    owner: str
    repo: str
    branch: Optional[str] = None
    token: Optional[str] = None
    jobs: Dict[str, Dict[str,str]] = field(default_factory=dict) 
    """
        自定义任务配置, 格式为
        {
        "job_name": {
            "job_type": "",  # 任务类型，如 "commit_summary", "issue_summary" 等
            "cron": "*/5 * * * *",  # cron表达式
            ... 其他任务相关配置
            }
        }
    """
    # GitLab 特定字段
    base_url: Optional[str] = None
    


@dataclass
class LlmProcessorConfig:
    """大语言模型文本处理配置"""
    type : Literal["ollama", "openai"] = "ollama"
    identifier: str = "llama2"
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
    default_processor: str = "llama2"
    log_level: str = "INFO"
    cache_dir: str = "./cache"