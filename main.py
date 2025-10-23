#!/bin/env python3
import asyncio
import argparse
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.logging import RichHandler
from rich.console import Console
import logging
from config.loader import ConfigLoader
from clients.github_client import GitHubClient
from clients.gitlab_client import GitLabClient
from processors.ollama_processor import OllamaProcessor
from processors.openai_processor import OpenAIProcessor
from pushers.serverchan_pushservice import ServerChanPushService

scheduler = AsyncIOScheduler()
console = Console()
logger = logging.getLogger(__name__)
