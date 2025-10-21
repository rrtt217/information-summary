"""配置加载器"""
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Union, List

import yaml

from .models import (
    AppConfig, RepositoryConfig, OllamaConfig, PushConfig, 
    PushServiceConfig, ScheduleConfig
)


class ConfigLoader:
    """配置加载器，支持YAML和JSON格式"""
    
    def __init__(self):
        self.env_pattern = re.compile(r'\$\{([^}]+)\}')
    
    def _resolve_env_vars(self, value: Any) -> Any:
        """解析环境变量引用"""
        if isinstance(value, str):
            return self.env_pattern.sub(lambda m: os.getenv(m.group(1), ''), value)
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]
        return value
    
    def load_yaml(self, path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            config_dict = yaml.safe_load(content)
            resolved_dict = self._resolve_env_vars(config_dict)
            return resolved_dict
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML配置文件格式错误: {e}")
    
    def load_json(self, path: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            config_dict = json.loads(content)
            resolved_dict = self._resolve_env_vars(config_dict)
            return resolved_dict
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON配置文件格式错误: {e}")
    
    def load_config_file(self, path: str) -> Dict[str, Any]:
        """加载配置文件"""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        if path_obj.suffix.lower() in ['.yaml', '.yml']:
            return self.load_yaml(path)
        elif path_obj.suffix.lower() == '.json':
            return self.load_json(path)
        else:
            raise ValueError(f"不支持的配置文件格式: {path_obj.suffix}")
    
    def load_config(self, path: str) -> AppConfig:
        """加载配置文件并返回AppConfig对象"""
        config_dict = self.load_config_file(path)
        return self._dict_to_app_config(config_dict)
    
    def _dict_to_app_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """将字典转换为AppConfig对象"""
        # 解析仓库配置
        repositories = []
        for repo_dict in config_dict.get('repositories', []):
            repo_config = RepositoryConfig(
                name=repo_dict['name'],
                type=repo_dict['type'],
                owner=repo_dict.get('owner'),
                repo=repo_dict.get('repo'),
                branch=repo_dict.get('branch', 'main'),
                token=repo_dict.get('token'),
                project_id=repo_dict.get('project_id'),
                base_url=repo_dict.get('base_url')
            )
            repositories.append(repo_config)
        
        # 解析Ollama配置
        ollama_dict = config_dict.get('ollama', {})
        ollama_config = OllamaConfig(
            base_url=ollama_dict.get('base_url', 'http://localhost:11434'),
            model=ollama_dict.get('model', 'llama2'),
            system_prompt=ollama_dict.get('system_prompt', '你是一个代码仓库分析助手'),
            temperature=ollama_dict.get('temperature', 0.7),
            max_tokens=ollama_dict.get('max_tokens', 2048)
        )
        
        # 解析推送配置
        push_dict = config_dict.get('push', {})
        push_services = []
        for service_dict in push_dict.get('services', []):
            push_service = PushServiceConfig(
                type=service_dict['type'],
                sendkey=service_dict.get('sendkey'),
            webhook_url=service_dict.get('webhook_url')
            )
            push_services.append(push_service)
        
        push_config = PushConfig(services=push_services)
        
        # 解析调度配置
        schedules = []
        for schedule_dict in config_dict.get('schedules', []):
            schedule_config = ScheduleConfig(
                cron=schedule_dict['cron'],
                repositories=schedule_dict.get('repositories', [])
        )
        schedules.append(schedule_config)
        
        return AppConfig(
            repositories=repositories,
            ollama=ollama_config,
            push=push_config,
            schedules=schedules,
            log_level=config_dict.get('log_level', 'INFO'),
            cache_dir=config_dict.get('cache_dir', './cache')
        )