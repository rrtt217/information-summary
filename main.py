#!/bin/env python3
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from cli import CommandPrompt, CommandParser
from config.loader import ConfigLoader, AppConfig
from gitclients.github_client import GitHubClient
from gitclients.gitlab_client import GitLabClient
from processors.ollama_processor import OllamaProcessor
from processors.openai_processor import OpenAIProcessor
from processors.generic_processor import GenericProcessor
from pushers.serverchan_pushservice import ServerChanPushService
from pushers.generic_pushservice import GenericPushService
from repo.repository import Repository
from typing import Optional, Dict, Tuple

#__________________初始化____________________#
def initialize(is_config_reload: bool = False, scheduler: Optional[AsyncIOScheduler] = None, command_prompt: Optional[CommandPrompt] = None) -> Tuple[AsyncIOScheduler, CommandPrompt]:
    assert not is_config_reload or (is_config_reload and scheduler is not None and command_prompt is not None), "Scheduler must be provided when reloading config"
    if not scheduler:
        scheduler = AsyncIOScheduler(event_loop=asyncio.get_event_loop())
    else:
        # 先清除现有任务
        scheduler.remove_all_jobs()
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
    if not command_prompt:
        command_prompt = CommandPrompt(
            CommandParser(
            {
                "help": None,
                "exit": lambda: "exit",
                "scheduler": {
                    "list": lambda: "\n".join([str(job) for job in scheduler.get_jobs()]),
                    "shutdown":  (lambda *args,**kwargs : scheduler.shutdown(*args,**kwargs) or "Shuting down scheduler...") if scheduler.running else lambda: "Scheduler is not running",
                    "start": (lambda *args,**kwargs : scheduler.start(*args,**kwargs) or "Starting scheduler...") if not scheduler.running else lambda: "Scheduler is already running",
                    "pause": lambda: scheduler.pause() or "Pausing scheduler...",
                    "resume": lambda: scheduler.resume() or "Resuming scheduler...",
                },
                "config": {
                    "show": lambda: str(config),
                    "reload": config_reload  # Placeholder for future implementation
                }
            }
                        )
            )
    if not is_config_reload:
        scheduler.start()
        logging.info("Scheduler started. Press Ctrl+C or Ctrl+D to exit.")
    return scheduler, command_prompt

def config_reload() -> None:
    logging.info("Reloading configuration...")
    global scheduler, command_prompt
    scheduler, command_prompt = initialize(is_config_reload=True, scheduler=scheduler, command_prompt=command_prompt)

#__________________主程序____________________#
scheduler, command_prompt = initialize()
try:
    asyncio.get_event_loop().run_until_complete(command_prompt.run())
except (KeyboardInterrupt, SystemExit, EOFError):
    scheduler.shutdown()
    logging.info("Scheduler shut down. Exiting program")