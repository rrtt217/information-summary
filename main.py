#!/bin/env python3
import asyncio
import argparse
from datetime import datetime, timedelta
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from config.loader import ConfigLoader, AppConfig
from clients.github_client import GitHubClient
from clients.gitlab_client import GitLabClient
from processors.ollama_processor import OllamaProcessor
from processors.openai_processor import OpenAIProcessor
from processors.generic_processor import GenericProcessor
from pushers.serverchan_pushservice import ServerChanPushService
from pushers.generic_pushservice import GenericPushService
from repo.repository import Repository
from typing import Optional, Dict, Callable, Union
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter, WordCompleter

#__________________命令提示符____________________#
CommandDictType = Dict[str, Union[None, Callable[..., str], 'CommandDictType']]
class CommandPrompt:
    session: PromptSession
    completer: WordCompleter
    scheduler: AsyncIOScheduler
    def __init__(self, scheduler) -> None:
        self.session = PromptSession()
        self.completer = WordCompleter(["help", "exit"])
        self.scheduler = scheduler

    async def run(self):
        while True:
            prompt = await self.session.prompt_async(">", completer=self.completer)
            prompts = prompt.split(" ")
            if prompts[0] == "exit":
                if len(prompts) == 1:
                    break
                else:
                    logging.error(f"'exit' received {len(prompts) - 1} parameters, expect 0")
            logging.info(f"Prompt: {prompt}")



#__________________主程序____________________#
# 初始化调度器
scheduler = AsyncIOScheduler(event_loop=asyncio.get_event_loop())

# 加载配置
config_loader = ConfigLoader()
config: AppConfig = config_loader.load_config("config.yaml")
processors: Dict[str, GenericProcessor] = {}
push_services: Dict[str, GenericPushService] = {}
repos: Dict[str, Repository] = {}
logging_level_map: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
# 初始化logger
logging.basicConfig(level=logging_level_map.get(config.log_level, logging.INFO), format='%(asctime)s - %(levelname)s - %(message)s')
# 创建处理器
for proc_cfg in config.processors:
    if proc_cfg.type == "ollama":
        processor = OllamaProcessor(
            model_name=proc_cfg.model,
            temperature=proc_cfg.temperature,
            max_tokens=proc_cfg.max_tokens,
            base_url=proc_cfg.base_url
        )
    elif proc_cfg.type == "openai":
        processor = OpenAIProcessor(
            model_name=proc_cfg.model,
            temperature=proc_cfg.temperature,
            max_tokens=proc_cfg.max_tokens,
            base_url=proc_cfg.base_url
        )
    else:
        raise ValueError(f"Unsupported processor type: {proc_cfg.type}")
    processors[proc_cfg.identifier] = processor
# 创建推送服务
for push_cfg in config.push_services:
    if push_cfg.type == "serverchan":
        push_service = ServerChanPushService(config=push_cfg.configs)
    else:
        raise ValueError(f"Unsupported push service type: {push_cfg.type}")
    push_services[push_cfg.type] = push_service
# 创建仓库实例
for repo_cfg in config.repositories:
    if repo_cfg.type == "github":
        client = GitHubClient(
            token=repo_cfg.token
        )
    elif repo_cfg.type == "gitlab":
        client = GitLabClient(
            token=repo_cfg.token,
            base_url=repo_cfg.base_url if repo_cfg.base_url else "https://gitlab.com/api/v4"
        )
    else:
        raise ValueError(f"Unsupported repository type: {repo_cfg.type}")
    repository = Repository(
        type=repo_cfg.type,
        owner=repo_cfg.owner,
        repo=repo_cfg.repo,
        jobs=repo_cfg.jobs,
        token=repo_cfg.token,
        base_url=repo_cfg.base_url
    )
    repos[repo_cfg.identifier] = repository
# 为每个仓库添加任务到调度器
for repo_id, repository in repos.items():
    processor = processors.get(config.default_processor)
    if not processor:
        raise ValueError(f"Default processor {config.default_processor} not found")
    repository.add_jobs_to_scheduler(scheduler, processor, push_services.get("serverchan").push if push_services.get("serverchan") else None) # pyright: ignore[reportOptionalMemberAccess]
# 启动调度器
scheduler.start()
logging.info("Scheduler started. Press Ctrl+C or Ctrl+D to exit.")
command_prompt = CommandPrompt(scheduler)
try:
    # 让用户能看到全屏程序启动前的日志
    time.sleep(1)
    asyncio.run(command_prompt.run())
except (KeyboardInterrupt, SystemExit, EOFError):
    pass