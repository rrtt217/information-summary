"""GitHub API 客户端实现"""
import aiohttp
from typing import Any, Dict, List, Optional
from datetime import datetime
from .generic_client import GenericClient, RateLimitException


class GitHubClient(GenericClient):
    """GitHub API 客户端"""
    
    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        """
        初始化 GitHub 客户端
        
        Args:
            token: GitHub 个人访问令牌
            base_url: GitHub API 基础 URL
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}" 
    
    async def get_readme(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        获取指定仓库的 README 内容
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            branch: 分支名称
        
        Returns:
            README 内容字符串
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/readme"
        params = {"ref": branch}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("content", "")
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取 README 失败: {response.status}")
    
    async def get_commit_messages_since(self, owner: str, repo: str, since: datetime, branch: str = "main" ) -> str:
        """
        获取自指定时间以来的提交记录，提取关键信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            branch: 分支名称
            since: 起始时间
        
        Returns:
            包含关键信息的提交记录字符串，每行一个提交， 信息包括：
            - message (提交信息)
            - author/committer (作者/提交者信息)
            - sha (提交哈希)
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        params = {
            "sha": branch,
            "since": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    commits_data = await response.json()
                    extracted_info = ""
                    # 提取关键提交信息
                    for commit in commits_data:
                        commit_info = {
                            "message": commit.get("commit", {}).get("message", ""),
                            "sha": commit.get("sha", ""),
                            "html_url": commit.get("html_url", "")
                        }
                        
                        # 提取作者信息（优先使用author，如果没有则使用committer）
                        author_info = commit.get("author") or commit.get("committer") or {}
                        if author_info:
                            commit_info["author"] = {
                                "name": author_info.get("name"),
                                "email": author_info.get("email"),
                                "login": author_info.get("login")
                        }
                        extracted_info += f"Commit {commit_info['sha'][:7]} by {commit_info['author']['name']}: {commit_info['message']}\n"
                    return extracted_info
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取提交记录失败: {response.status}")
    
    async def get_issues_since(self, owner: str, repo: str, since: datetime) -> str:
        """
        获取自指定时间以来的问题记录
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            since: 起始时间（datetime, UTF+0）
        
        Returns:
            包含关键信息的问题记录字符串（每行一个问题），信息包括：
            - title (问题标题)
            - user (创建者信息)
            - state (问题状态)
            - number (问题编号)
            - assignees (指派人信息)
            - labels (标签信息)
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",
            "since": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    issue_data = await response.json()
                    extracted_info = ""
                    for issue in issue_data:
                        # 过滤掉拉取请求，只保留问题
                        if "pull_request" not in issue:
                            if issue['labels']:
                                labels = ",".join([str(label['name']) for label in issue['labels']])
                            else:
                                labels = None
                            extracted_info += f"Issue #{issue['number']} by {issue['user']['login']}: {issue['title']} (State: {issue['state']}), {'(Labels: {labels})' if labels else ''})\n"
                    return extracted_info
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取问题记录失败: {response.status}")
    
    async def get_pull_requests_since(self, owner: str, repo: str, since: datetime) -> List[Dict[str, Any]]:
        """
        获取自指定时间以来的拉取请求记录
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            since: 起始时间
        
        Returns:
            拉取请求记录列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {
            "state": "all",
            "since": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取拉取请求失败: {response.status}")
    
    async def get_commit_message(self, owner: str, repo: str, ref: str) -> str:
        """
        获取指定提交的提交信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            ref: 提交引用（SHA、分支名等）
        
        Returns:
            提交信息字符串
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{ref}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("commit", {}).get("message", "")
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取提交信息失败: {response.status}")
    
    async def get_issue_comments_since(self, owner: str, repo: str, issue_number: int, since: datetime) -> List[Dict[str, Any]]:
        """
        获取自指定时间以来指定问题的评论
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            issue_number: 问题编号
            since: 起始时间
        
        Returns:
            问题评论列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {"since": since.isoformat()}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取问题评论失败: {response.status}")
    
    async def get_pull_request_comments_since(self, owner: str, repo: str, pr_number: int, since: datetime) -> List[Dict[str, Any]]:
        """
        获取自指定时间以来指定拉取请求的评论
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: 拉取请求编号
            since: 起始时间
        
        Returns:
            拉取请求评论列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        params = {"since": since.isoformat()}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取拉取请求评论失败: {response.status}")
    
    async def compare_two_commits(self, owner: str, repo: str, base: str, head: str) -> Dict[str, Any]:
        """
        比较两个提交之间的差异
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            base: 基础提交
            head: 目标提交
        
        Returns:
            比较结果
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/compare/{base}...{head}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("X-RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitHub API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"比较提交失败: {response.status}")