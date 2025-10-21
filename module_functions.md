# 模块函数详细设计

## 1. 配置系统模块 (`config/`)

### ConfigManager 类
```python
class ConfigManager:
    async def load_config(self, config_path: str) -> AppConfig:
        """异步加载配置文件"""
        pass
    
    async def validate_config(self, config: AppConfig) -> bool:
        """异步验证配置有效性"""
        pass
    
    async def watch_config_changes(self) -> None:
        """异步监听配置文件变化（可选）"""
        pass
```

### ConfigLoader 类
```python
class ConfigLoader:
    async def load_yaml(self, path: str) -> Dict:
        """异步加载YAML配置"""
        pass
```

## 2. API客户端模块 (`clients/`)

### GitHubClient 类 (异步)
```python
class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        pass
    
    async def get_commits_since(self, owner: str, repo: str, 
                          since: datetime, branch: str = "main") -> List[CommitInfo]:
        """获取指定时间后的commits"""
        pass
    
    async def get_issue_details(self, owner: str, repo: str, 
                                 issue_number: int) -> IssueInfo:
        """获取issue详细信息"""
        pass
    
    async def get_pull_request_details(self, owner: str, repo: str, 
                                      pr_number: int) -> PRInfo:
        """获取PR详细信息"""
        pass
    
    async def get_repository_issues(self, owner: str, repo: str, 
                                      since: datetime) -> List[IssueInfo]:
        """获取指定时间后的issues"""
        pass
    
    async def get_open_pull_requests(self, owner: str, repo: str) -> List[PRInfo]:
        """获取打开的PR列表"""
        pass
```

### GitLabClient 类 (异步)
```python
class GitLabClient:
    def __init__(self, token: str, base_url: str):
        pass
    
    async def get_commits_since(self, project_id: str, 
                                since: datetime, branch: str = "main") -> List[CommitInfo]:
        """获取GitLab仓库commits"""
        pass
    
    async def get_merge_request_details(self, project_id: str, 
                                          mr_iid: int) -> MRInfo:
        """获取MR详细信息"""
        pass
    
    async def get_project_issues(self, project_id: str, 
                                      since: datetime) -> List[IssueInfo]:
        """获取GitLab项目issues"""
        pass
```

## 3. 数据服务模块 (`services/`)

### DataFetcher 类 (异步)
```python
class DataFetcher:
    async def fetch_repository_data(self, repo_config: RepositoryConfig,
                                      period_start: datetime, 
                                      period_end: datetime) -> RepositoryData:
        """异步获取仓库数据"""
        pass
    
    async def filter_relevant_data(self, data: RepositoryData, 
                                      filters: Dict) -> RepositoryData:
        """异步过滤数据"""
        pass
    
    async def aggregate_metrics(self, data: RepositoryData) -> Dict[str, Any]:
        """异步聚合指标"""
        pass
```

### OllamaProcessor 类 (异步)
```python
class OllamaProcessor:
    def __init__(self, config: OllamaConfig):
        pass
    
    async def generate_summary(self, data: RepositoryData) -> ProcessedSummary:
        """异步生成汇总摘要"""
        pass
    
    async def analyze_development_trends(self, data: RepositoryData) -> Dict:
        """异步分析开发趋势"""
        pass
    
    async def identify_key_changes(self, data: RepositoryData) -> List[str]:
        """异步识别关键变更"""
        pass
```

### PushService 类 (异步)
```python
class PushService:
    async def push_to_serverchan(self, summary: ProcessedSummary, 
                                      config: PushConfig) -> bool:
        """异步推送到ServerChan"""
        pass
    
    async def push_to_webhook(self, summary: ProcessedSummary, 
                                      config: PushConfig) -> bool:
        """异步推送到Webhook"""
        pass
    
    async def push_to_multiple_services(self, summary: ProcessedSummary) -> bool:
        """异步推送到多个服务"""
        pass
```

## 4. 调度模块 (`scheduler/`)

### CronScheduler 类 (异步)
```python
class CronScheduler:
    async def start(self) -> None:
        """异步启动调度器"""
        pass
    
    async def stop(self) -> None:
        """异步停止调度器"""
        pass
```

### TaskExecutor 类 (异步)
```python
class TaskExecutor:
    async def execute_monitoring_task(self, schedule_config: ScheduleConfig) -> None:
        """异步执行监控任务"""
        pass
```

## 5. 异步处理关键函数

### 必须异步的核心函数：
1. **网络请求函数** (I/O密集型)
   - `GitHubClient.get_commits_since()`
   - `GitLabClient.get_commits_since()`
   - `PushService.push_to_serverchan()`

2. **AI处理函数** (计算密集型)
   - `OllamaProcessor.generate_summary()`
   - `OllamaProcessor.analyze_development_trends()`

3. **并行处理函数** (性能优化)
   - `DataFetcher.fetch_multiple_repositories()`
   - `TaskExecutor.execute_parallel_tasks()`

## 异步执行示例

```python
async def monitor_single_repository(repo_config: RepositoryConfig) -> bool:
    """异步监控单个仓库"""
    try:
        # 1. 获取数据 (异步)
        fetcher = DataFetcher()
        repo_data = await fetcher.fetch_repository_data(
            repo_config, 
            period_start, 
            period_end
        )
        
        # 2. 处理数据 (异步)
        processor = OllamaProcessor(ollama_config)
        summary = await processor.generate_summary(repo_data)
        
        # 3. 推送结果 (异步)
        pusher = PushService()
        success = await pusher.push_to_serverchan(summary, push_config)
        return success
    except Exception as e:
        logger.error(f"监控仓库失败: {e}")
        return False

async def main_monitoring_loop():
    """主监控循环"""
    tasks = []
    for repo_config in config.repositories:
        task = asyncio.create_task(monitor_single_repository(repo_config))
        tasks.append(task)
    
    # 并行执行所有仓库监控
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results