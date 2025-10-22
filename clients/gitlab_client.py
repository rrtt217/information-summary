"""GitLab API 客户端实现"""
import aiohttp
import base64
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from .generic_client import GenericClient, RateLimitException


class GitLabClient(GenericClient):
    """GitLab API 客户端"""
    # 由于GitLab API限制，不能直接通过owner/repo访问项目，需要先获取Project ID
    def __init__(self, token: Optional[str] = None, base_url: str = "https://gitlab.com/api/v4"):
        """
        初始化 GitLab 客户端
        
        Args:
            token: GitLab 个人访问令牌
            base_url: GitLab API 基础 URL
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Accept": "application/json"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    async def _get_project_id(self, owner: str, repo: str) -> int:
        """
        获取项目的 Project ID
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            
        Returns:
            Project ID 整数
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["id"]
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取项目ID失败: {response.status}")


    async def get_readme(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        获取指定仓库的 README 内容
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            branch: 分支名称
            
        Returns:
            README 内容字符串
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/repository/files/README.md/raw"
        params = {"ref": branch}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                        reset_time
                    )
                else:
                    raise Exception(f"获取 README 失败: {response.status}")
    
    async def get_commit_messages_since(self, owner: str, repo: str, since: datetime, branch: str = "main") -> str:
        """
        获取自指定时间以来的提交记录，提取关键信息
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            branch: 分支名称
            since: 起始时间
            
        Returns:
            包含关键信息的提交记录字符串，每行一个提交，信息包括：
            - message (提交信息)
            - author (作者信息)
            - sha (提交哈希)
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/repository/commits"
        params = {
            "ref_name": branch,
            "since": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    commits_data = await response.json()
                    extracted_info = ""
                    for commit in commits_data:
                        commit_info = {
                            "message": commit.get("message", ""),
                            "sha": commit.get("id", ""),
                            "author_name": commit.get("author_name", ""),
                            "author_email": commit.get("author_email", "")
                        }
                        extracted_info += f"Commit {commit_info['sha'][:7]} by {commit_info['author_name']}: {commit_info['message']}\n"
                    return extracted_info
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                    reset_time
                )
                else:
                    raise Exception(f"获取提交记录失败: {response.status}")
    
    async def get_issues_since(self, owner: str, repo: str, since: datetime, state: Literal["opened", "closed", "all"] = "all", contains_body: bool = False) -> str:
        """
        获取自指定时间以来的问题记录
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            since: 起始时间（datetime, UTC+0）
        
        Returns:
            包含关键信息的问题记录字符串（每行一个问题），信息包括：
            - title (问题标题)
            - user (创建者信息)
            - state (问题状态)
            - number (问题编号)
            - assignees (指派人信息)
            - labels (标签信息)
            - （可选）body (问题正文)
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/issues"
        params = {
            "state": state,
            "updated_after": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    issue_data = await response.json()
                    extracted_info = ""
                    for issue in issue_data:
                        if issue['labels']:
                            labels = ",".join([str(label) for label in issue['labels']])
                        else:
                            labels = None
                        extracted_info += f"Issue #{issue['iid']} by {issue['author']['username']}: {issue['title']} (State: {issue['state']}), {'(Labels: {labels})' if labels else ''}\n"
                        if contains_body:
                            extracted_info += issue['description'] + "\n"
                    return extracted_info
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                    reset_time
                )
                else:
                    raise Exception(f"获取问题记录失败: {response.status}")
    
    async def get_pull_requests_since(self, owner: str, repo: str, since: datetime, state: Literal["opened", "closed", "merged", "all"] = "all", contains_body: bool = False) -> str:
        """
        获取自指定时间以来的合并请求记录
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            since: 起始时间
            
        Returns:
            包含关键信息的合并请求字符串（每行一个合并请求），信息包括：
            - title (合并请求标题)
            - user (创建者信息)
            - state (合并请求状态)
            - number (合并请求编号)
            - assignees (指派人信息)
            - labels (标签信息)
            - (可选) body (合并请求正文)
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/merge_requests"
        params = {
            "state": state,
            "updated_after": since.isoformat()
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    mr_data = await response.json()
                    extracted_info = ""
                    for mr in mr_data:
                        if mr['labels']:
                            labels = ",".join([str(label) for label in mr['labels']])
                        else:
                            labels = None
                        extracted_info += f"MR #{mr['iid']} by {mr['author']['username']}: {mr['title']} (State: {mr['state']}) {'(Labels: {labels})' if labels else ''}\n"
                        if contains_body:
                            extracted_info += mr['description'] + "\n"
                    return extracted_info
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                    reset_time
                )
                else:
                    raise Exception(f"获取合并请求失败: {response.status}")
    
    async def get_commit_message(self, owner: str, repo: str, ref: str) -> str:
        """
        获取指定提交的提交信息
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            ref: 提交引用（SHA、分支名等）
        
        Returns:
            提交信息字符串
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/repository/commits/{ref}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message", "")
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                    f"GitLab API 速率限制：{response.status}",
                reset_time
            )
                else:
                    raise Exception(f"获取提交信息失败: {response.status}")
    
    async def get_issue(self, owner: str, repo: str, issue_number: int) -> str:
        """
        获取指定问题的信息
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            issue_number: 问题编号
        
        Returns:
            包含问题信息的字符串，与get_issues_since返回格式相同
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/issues/{issue_number}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    issue = await response.json()
                    labels = ",".join([str(label) for label in issue['labels']]) if issue['labels'] else None
        issue_info = f"Issue #{issue['iid']} by {issue['author']['username']}: {issue['title']} (State: {issue['state']}), {'(Labels: {labels})' if labels else ''}\n"
        issue_info += issue['description'] + "\n"
        return issue_info
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> str:
        """
        获取指定合并请求的信息
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            pr_number: 合并请求编号
        
        Returns:
            包含合并请求信息的字符串，与get_pull_requests_since返回格式相同
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/merge_requests/{pr_number}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    mr = await response.json()
                    labels = ",".join([str(label) for label in mr['labels']]) if mr['labels'] else None
        mr_info = f"MR #{mr['iid']} by {mr['author']['username']}: {mr['title']} (State: {mr['state']}) {'(Labels: {labels})' if labels else ''}\n"
        mr_info += mr['description'] + "\n"
        return mr_info
    
    async def get_issue_comments_since(self, owner: str, repo: str, issue_number: int, since: datetime) -> str:
        """
        获取自指定时间以来指定问题的评论
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            issue_number: 问题编号
            since: 起始时间
        
        Returns:
            包含问题评论的字符串，每条评论以如下格式：
            <User>: <Comment>
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/issues/{issue_number}/notes"
        params = {"created_after": since.isoformat()}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    issue_comment_data = await response.json()
                    return "\n\n".join([f"{comment['author']['username']}: {comment['body']}" for comment in issue_comment_data])
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                    f"GitLab API 速率限制：{response.status}",
                reset_time
            )
                else:
                    raise Exception(f"获取问题评论失败: {response.status}")
    
    async def get_pull_request_comments_since(self, owner: str, repo: str, pr_number: int, since: datetime) -> str:
        """
        获取自指定时间以来指定合并请求的评论
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            pr_number: 合并请求编号
            since: 起始时间
        
        Returns:
            包含合并请求评论的字符串，每条评论以如下格式：
            <User>: <Comment>
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/merge_requests/{pr_number}/notes"
        params = {"created_after": since.isoformat()}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    mr_comment_data = await response.json()
                    return "\n\n".join([f"{comment['author']['username']}: {comment['body']}" for comment in mr_comment_data])
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                    reset_time
                    )
                else:
                    raise Exception(f"获取合并请求评论失败: {response.status}")
    
    async def compare_two_commits(self, owner: str, repo: str, base: str, head: str) -> str:
        """
        比较两个提交之间的差异
        
        Args:
            owner: 所有者或命名空间
            repo: 项目名称
            base: 基础提交
            head: 目标提交
        
        Returns:
            比较结果
        """
        project_id = f"{owner}/{repo}"
        url = f"{self.base_url}/projects/{project_id.replace('/', '%2F')}/repository/compare"
        params = {
            "from": base,
            "to": head
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:
                    reset_timestamp = response.headers.get("RateLimit-Reset")
                    reset_time = None
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp))
                    raise RateLimitException(
                        f"GitLab API 速率限制：{response.status}",
                reset_time
            )
                else:
                    raise Exception(f"比较提交失败: {response.status}")