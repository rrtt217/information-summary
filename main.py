#!/bin/env python3
import asyncio
import argparse
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from config.loader import ConfigLoader
from clients.github_client import GitHubClient
from clients.gitlab_client import GitLabClient
from processors.ollama_processor import OllamaProcessor
from processors.openai_processor import OpenAIProcessor
from pushers.serverchan_pushservice import ServerChanPushService
from repo.repository import Repository

scheduler = AsyncIOScheduler(event_loop=asyncio.get_event_loop())
# 加载配置

config_loader = ConfigLoader()
config = config_loader.load_config("config.yaml")
processors = {}
push_services = {}
repos = {}
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
for push_cfg in config.push_services:
    if push_cfg.type == "serverchan":
        push_service = ServerChanPushService(config=push_cfg.configs)
    else:
        raise ValueError(f"Unsupported push service type: {push_cfg.type}")
    push_services[push_cfg.type] = push_service
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
    repository.add_jobs_to_scheduler(scheduler, processor, push_services.get("serverchan").push if "serverchan" in push_services else None)
scheduler.start()
logging.info("Scheduler started. Press Ctrl+C to exit.")
try:
    asyncio.get_event_loop().run_forever()
except (KeyboardInterrupt, SystemExit):
    pass