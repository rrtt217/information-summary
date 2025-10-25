from clients.github_client import GitHubClient
from clients.gitlab_client import GitLabClient
from clients.generic_client import GenericClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Dict, Callable
from processors.generic_processor import GenericProcessor
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
class Repository:
    """代码仓库抽象类"""
    owner: str
    repo: str
    client: GenericClient
    jobs: Dict[str, Dict[str,str]]

    def __init__(self, type: str, owner: str, repo: str, jobs: Dict[str,Dict[str,str]] , token: Optional[str] = None, base_url: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.jobs = jobs
        if type == "github":
            self.client = GitHubClient(token=token, base_url=base_url or "https://api.github.com")
        elif type == "gitlab":
            self.client = GitLabClient(token=token, base_url=base_url or "https://gitlab.com/api/v4")
        else:
            raise ValueError(f"Unsupported repository type: {type}")
    def add_jobs_to_scheduler(self, scheduler: AsyncIOScheduler, processor: GenericProcessor, push_service: Optional[Callable] = None):
        """
        将该仓库的所有任务添加到调度器中。
        """
        # 根据传入的processor和任务类型映射，构建任务函数映射
        job_func_map = {
            "commits": processor.summarize_repository_changes_since,
            "issues": processor.summarize_repository_issues_since,
            "pull_requests": processor.summarize_repository_pull_requests_since
        }
        # 初始化上次运行时间记录
        if not hasattr(self, 'last_run_times'):
            self.last_run_times = {}
        
        for job_name, job_config in self.jobs.items():
            cron_expr = job_config.get("cron")
            if not cron_expr:
                logger.warning(f"Job {job_name} for {self.owner}/{self.repo} is missing cron expression")
                continue
            
            job_type = job_config.get("type")
            if not job_type or job_type not in job_func_map:
                logger.warning(f"Unknown job type {job_type} for job {job_name} in {self.owner}/{self.repo}")
                continue
            
            job_func = job_func_map[job_type]
            
            # 创建包装函数处理任务执行
            async def job_wrapper(job_name=job_name, job_config=job_config, job_func=job_func, job_type=job_type):
                now = datetime.now(timezone.utc)
                # 获取上次运行时间，首次运行默认为7天前
                last_run = self.last_run_times.get(job_name, now - timedelta(days=7))
                self.last_run_times[job_name] = now
                
                # 准备通用参数
                base_args = [
                    self.client,
                    self.owner,
                    self.repo,
                    last_run  # since参数
                ]
                
                # 根据任务类型准备特定参数
                if job_type == "commits":
                    base_args.append(job_config.get("branch"))
                    kwargs = {
                        "diff_analysis": job_config.get("diff_analysis", False),
                        "use_info": job_config.get("use_info", False)
                    }
                elif job_type in ["issues", "pull_requests"]:
                    kwargs = {
                        "state": job_config.get("state", "all"),
                        "contains_body": job_config.get("contains_body", False),
                        "use_info": job_config.get("use_info", False)
                    }
                else:
                    kwargs = {}
                
                # 执行任务
                logger.info(f"Executing job {job_name} of type {job_type}")
                result = await job_func(*base_args, **kwargs)
                logger.info(f"Job {job_name} completed, result length: {len(result) if result else 0}")
                
                # 如果有推送服务，推送结果
                if push_service:
                    logger.info(f"Calling push service with result")
                    await push_service(title=f"Repository {self.owner}/{self.repo} - Job {job_name} Result", content=result)
                    logger.info(f"Push service called successfully")
                else:
                    logger.warning(f"No push service available for job {job_name}")
            
            # 添加任务到调度器
            scheduler.add_job(
                job_wrapper,
                CronTrigger.from_crontab(cron_expr),
                id=f"{self.owner}_{self.repo}_{job_name}",
                name=f"{self.owner}/{self.repo} - {job_name}"
            )