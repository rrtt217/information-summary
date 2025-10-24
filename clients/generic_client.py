from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Literal, TypeVar, Callable
from functools import wraps
import asyncio
from datetime import datetime
import logging


class RateLimitException(Exception):
    """API 速率限制异常"""
    def __init__(self, message: str = "API调用频率超过限制", reset_time: Optional[datetime] = None):
        self.message = message
        self.reset_time = reset_time
        super().__init__(self.message)
class GenericClient(ABC):
    """通用的客户端接口"""
    token: Optional[str]
    base_url: str
    # 目前，所有的方法都应返回纯文本字符串，以便LLM识读。
    # 未来可以考虑返回更复杂的结构体，以便更灵活地处理不同的数据需求。
    @abstractmethod
    async def get_readme(self, owner: str, repo: str, branch: Optional[str] = None) -> str:
        """获取指定仓库的README内容"""
        pass
    @abstractmethod
    async def get_repository_info(self, owner: str, repo: str) -> Any:
        """获取指定仓库的信息"""
        pass
    @abstractmethod
    async def get_commit_messages_since(self, owner: str, repo: str,  since: datetime, contains_full_sha: bool = False, branch: Optional[str] = None) -> Any:
        """获取自指定时间以来的提交记录"""
        pass

    # 对于Issue 和PR，与Commit有几点不同：
    # 1. Commit是基于分支的，而Issue和PR是基于仓库的，所以不需要branch参数。
    # 2. Issue和PR有可能被关闭或合并，所以在获取时需要考虑它们的状态，因此需要state参数。
    # 3. Issue和PR通常包含更多的元数据，如标签、评论等。对于get_*_since方法，包含评论会导致返回值过长，故这一部分被拆分到get_*_comments_since方法中。
    #    然而是否包含Issue和PR的body应该是可选的。
    # 4. (TODO) Issue和PR的数量可能远大于Commit，因此在实现时需要考虑分页处理。实现分页以后，可以把since改为Optional.
    # 5. (TODO) Issue和PR的过滤条件可能更加复杂，如按标签、按作者等，未来可以考虑扩展这些功能。
    
    @abstractmethod
    async def get_issues_since(self, owner: str, repo: str, since: datetime, state: Literal["open", "closed", "all"], contains_body: bool) -> Any:
        """获取自指定时间以来的问题记录"""
        pass
    @abstractmethod
    async def get_pull_requests_since(self, owner: str, repo: str, since: datetime, state: Literal["open", "closed", "all"], contains_body: bool) -> Any:
        """获取自指定时间以来的拉取/合并请求记录"""
        pass
    @abstractmethod
    async def get_commit_message(self, owner: str, repo: str, ref: str) -> str:
        """获取指定提交的提交信息"""
        pass

    # 以下这两个方法不会返回评论内容，因为Github API没有实现。
    # (TODO) 原则上这两个方法应当处理更多的错误码，因为Issue和PR可能被删除或移动，导致无法访问。
    @abstractmethod
    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Any:
        """获取指定问题的信息"""
        pass
    @abstractmethod
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Any:
        """获取指定拉取/合并请求的信息"""
        pass

    @abstractmethod
    async def get_issue_comments_since(self, owner: str, repo: str, issue_number: int, since: datetime) -> Any:
        """获取自指定时间以来指定问题的评论"""
        pass
    @abstractmethod
    async def get_pull_request_comments_since(self, owner: str, repo: str, pr_number: int, since: datetime) -> Any:
        """获取自指定时间以来指定拉取/合并请求的评论"""
        pass
    @abstractmethod
    async def compare_two_commits(self, owner: str, repo: str, base: str, head: str) -> Any:
        """比较两个提交之间的差异"""
        pass

T = TypeVar('T')

def auto_retry_on_rate_limit(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """自动重试装饰器 - 支持异步函数"""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except RateLimitException as e:
                    if retries >= max_retries:
                        raise e
                    # 计算延迟时间
                    delay = base_delay * (backoff_factor ** retries)
                    
                    # 如果提供了重置时间，使用更长的等待
                    if e.reset_time:
                        now = datetime.now()
                        if e.reset_time > now:
                            delay = max(delay, (e.reset_time - now).total_seconds())
                    
                    logging.warning(
                        f"遭遇速率限制，{delay:.2f}秒后重试 "
                        f"(重试 {retries + 1}/{max_retries})"
                    )
                    
                    # 使用异步sleep，不会阻塞事件循环
                    await asyncio.sleep(delay)
                    retries += 1
                    continue  
        return wrapper
    return decorator