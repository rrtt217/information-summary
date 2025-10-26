#!/bin/env python3
import asyncio
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
from prompt_toolkit.completion import NestedCompleter

#__________________命令提示符____________________#
CommandDictType = Dict[str, Union[None, Callable[..., Optional[str]], 'CommandDictType']]
class CommandParser:
    command_dict: CommandDictType
    def __init__(self, command_dict: CommandDictType) -> None:
        self.command_dict = command_dict

    def parse(self, prompt: str) -> Optional[str]:
        current_level = self.command_dict
        commands = prompt.split(" ")
        cmd = ""
        is_first = True
        while True:
            if len(commands) == 0:
                return None
            subcmd = commands.pop(0)
            cmd += f" {subcmd}"
            if current_level and subcmd in current_level:
                next_level = current_level[subcmd]
                if subcmd == "help" and is_first:
                    help_text = "Available commands:\n"
                    for key in current_level.keys():
                        help_text += f"  {key}\n"
                    return help_text
                if callable(next_level):
                    # 位置参数传递给函数
                    if all((c == "" or c[0] != "-") and (len(c) < 2 or c[1] != "-") for c in commands):
                        return next_level(*commands)
                    # 关键词参数传递给函数
                    elif all((c.startswith("--") and "=" in c) for c in commands):
                        return next_level(**{c.lstrip("--").split("=")[0]: c.lstrip("--").split("=")[1] for c in commands})
                else:
                    current_level = next_level
            else:
                raise SyntaxError(f"Unknown command: {cmd.strip()}")
            is_first = False
    def get_completer(self) -> NestedCompleter:
        def build_completer(command_dict: CommandDictType) -> NestedCompleter:
            completer_dict = {}
            for key, value in command_dict.items():
                if callable(value) or value is None:
                    completer_dict[key] = None
                else:
                    completer_dict[key] = build_completer(value)
            return NestedCompleter.from_nested_dict(completer_dict)
        return build_completer(self.command_dict)
class CommandPrompt:
    session: PromptSession
    completer: NestedCompleter
    parser: CommandParser
    scheduler: AsyncIOScheduler
    def __init__(self, parser: CommandParser) -> None:
        self.session = PromptSession()
        self.parser = parser
        self.completer = self.parser.get_completer()

    async def run(self):
        while True:
            prompt = await self.session.prompt_async(">", completer=self.completer)
            try:
                result = self.parser.parse(prompt)
                if result == "exit":
                    print("Exiting...")
                    break
                if result is not None:
                    print(result)
            except SyntaxError as e:
                logging.error(f"Syntax Error: {e}")
            except Exception as e:
                logging.error(f"Error: {e}")



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
        }
    }
    )
    )
try:
    asyncio.run(command_prompt.run())
except (KeyboardInterrupt, SystemExit, EOFError):
    scheduler.shutdown()
    logging.info("Scheduler shut down. Exiting program")