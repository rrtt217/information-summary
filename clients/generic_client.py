from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime


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
    @abstractmethod
    async def get_readme(self, owner: str, repo: str, branch: str) -> str:
        """获取指定仓库的README内容"""
        pass
    @abstractmethod
    async def get_commits_since(self, owner: str, repo: str, since: datetime, branch: str) -> Any:
        """获取自指定时间以来的提交记录"""
        pass
    @abstractmethod
    async def get_issues_since(self, owner: str, repo: str, since: datetime) -> Any:
        """获取自指定时间以来的问题记录"""
        pass
    @abstractmethod
    async def get_pull_requests_since(self, owner: str, repo: str, since: datetime) -> Any:
        """获取自指定时间以来的拉取/合并请求记录"""
        pass
    @abstractmethod
    async def get_commit_message(self, owner: str, repo: str, ref: str) -> str:
        """获取指定提交的提交信息"""
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
    async def compare_two_commits(self, owner: str, repo: str, base: str, head: str, ) -> Any:
        """比较两个提交之间的差异"""
        pass