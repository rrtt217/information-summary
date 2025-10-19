import requests
import json
from datetime import datetime, timedelta, timezone
import time
from ollama import Client

def get_recent_commit_messages(owner, repo, days=1, token=None):
    """
    从commit-fetcher.py导入的获取最近commit消息的函数
    """
    since_date = (datetime.now(tz=timezone(timedelta(hours=0))) - timedelta(days=days)).isoformat()
    all_commits = []
    page = 1
    
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        
        params = {
            'since': since_date,
            'per_page': 100,
            'page': page
        }
        
        headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'commit-fetcher',
        }
        
        if token:
            headers['Authorization'] = f'token {token}'
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # 检查API限制
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers['X-RateLimit-Remaining'])
                if remaining == 0:
                    reset_time = int(response.headers['X-RateLimit-Reset'])
                    wait_time = reset_time - time.time()
                    if wait_time > 0:
                        print(f"API限制达到，等待 {wait_time:.0f} 秒")
                        time.sleep(wait_time + 1)
                        continue
            
            response.raise_for_status()
            commits = response.json()
            
            # 如果没有更多commit，退出循环
            if not commits:
                break
                
            all_commits.extend(commits)
            
            # 如果返回的commit数量少于100，说明是最后一页
            if len(commits) < 100:
                break
                
            page += 1
            time.sleep(0.5)  # 避免请求过快
            
        except requests.exceptions.RequestException as e:
            print(f"第 {page} 页请求失败: {e}")
            break
    
    # 提取commit message
    commit_messages = []
    for commit in all_commits:
        if 'commit' in commit and 'message' in commit['commit']:
            commit_messages.append(commit['commit']['message'])
    
    return commit_messages

def get_diff_between_commits(owner, repo, base_sha, head_sha, token=None, raw=True, timeout=30):
    """
    从commit-fetcher.py导入的获取diff的函数
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}"
    headers = {
        'User-Agent': 'commit-fetcher',
    }
    if token:
        headers['Authorization'] = f'token {token}'
    if raw:
        headers['Accept'] = 'application/vnd.github.v3.diff'
    else:
        headers['Accept'] = 'application/vnd.github+json'
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            print(f"未找到比较对象: {base_sha}...{head_sha}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"获取 diff 失败: {e}")
        return None

def call_ollama(prompt):
    """
    调用Ollama进行文本概括，使用Ollama Python库
    """
    try:
        # 使用Ollama Python库
        client = Client(host='http://localhost:11434')
        response = client.generate(model='llama2', prompt=prompt, stream=False)
        return response.get('response', "")
    except Exception as e:
        return f"Ollama调用失败: {e}"

def summarize_commits_with_ollama(owner, repo, option=1, days=1, token=None):
    """
    主函数：获取最近n天的commit，使用Ollama进行概括
    
    参数:
    - owner: 仓库所有者
    - repo: 仓库名
    - option: 处理选项 (1=直接概括, 2=基于diff生成message)
    - days: 最近多少天
    - token: GitHub token (可选)
    
    返回:
    - 概括内容 (str)
    """
    print(f"开始获取 {owner}/{repo} 最近 {days} 天的commit...")
    
    # 获取commit消息
    commit_messages = get_recent_commit_messages(owner, repo, days=days, token=token)
    
    if not commit_messages:
        return f"在 {days} 天内没有找到 {owner}/{repo} 的commit"
    
    print(f"找到 {len(commit_messages)} 个commit")
    
    if option == 1:
        # 选项1：直接翻译概括commit message
        return summarize_direct_option(commit_messages, owner, repo)
    elif option == 2:
        # 选项2：根据相邻commit的diff生成message
        return summarize_with_diff_option(commit_messages, owner, repo, token)
    else:
        return "无效的选项，请选择1或2"

def summarize_direct_option(commit_messages, owner, repo):
    """
    选项1：直接翻译概括commit message
    """
    print("使用选项1：直接翻译概括commit message")
    
    # 将所有commit消息合并成一个文本
    combined_messages = "\n".join([f"Commit {i+1}: {msg}" for i, msg in enumerate(commit_messages)])
    
    prompt = f"""
请对以下来自GitHub仓库 {owner}/{repo} 的commit消息进行概括总结：

{combined_messages}

要求：
1. 用中文进行概括
2. 按功能模块或主题分类
3. 突出重要变更
4. 保持简洁明了

请提供概括总结："""
    
    print("调用Ollama进行概括...")
    summary = call_ollama(prompt)
    
    return summary

def summarize_with_diff_option(commit_messages, owner, repo, token):
    """
    选项2：根据相邻commit的diff生成message，然后与原来的commit message配对进行概括
    """
    print("使用选项2：根据diff生成message并配对概括")
    
    # 为了简化，这里只处理前几个commit的diff
    if len(commit_messages) < 2:
        return "commit数量不足，无法进行diff分析"
    
    print("获取commit的详细信息以进行diff分析...")
    
    # 获取完整的commit列表以获取SHA值
    since_date = (datetime.now(tz=timezone(timedelta(hours=0))) - timedelta(days=1)).isoformat()
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {
        'since': since_date,
        'per_page': 100
    }
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-A-gent': 'commit-fetcher',
    }
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        commits = response.json()
        
        if not commits or len(commits) < 2:
            return "无法获取足够的commit信息进行diff分析"
        
        # 获取前两个commit进行diff分析
        base_sha = commits[1]['sha']  # 较旧的commit
        head_sha = commits[0]['sha']  # 较新的commit
        
        print(f"比较commit {base_sha[:7]}...{head_sha[:7]}")
        
        # 获取diff
        diff_text = get_diff_between_commits(owner, repo, base_sha, head_sha, token=token, raw=True)
        
        if diff_text:
            # 使用Ollama分析diff并生成message
            diff_prompt = f"""
            请分析以下Git diff并生成一个简洁的commit消息描述这个变更：

            {diff_text[:65536]}  # 限制diff长度
            
            根据这个diff，生成的commit消息应该描述："""
            
            generated_message = call_ollama(diff_prompt)
            
            original_message = commit_messages[0] if commit_messages else "无原始消息"
            
            # 将生成的message与原始message配对，然后进行概括
            pair_prompt = f"""
            请对比以下两个commit消息并给出概括：

            原始commit消息:
            {original_message}

            基于diff生成的commit消息:
            {generated_message}

            请对这两个commit消息进行对比分析，并提供一个综合的概括总结：

            概括总结："""
            
            final_summary = call_ollama(pair_prompt)
            
            return f"""基于diff分析的commit概括：

            原始commit: {original_message}

            基于diff生成的commit: {generated_message}

            综合概括：
                    {final_summary}"""
        else:
            return "无法获取diff信息"
            
    except Exception as e:
        return f"在diff分析过程中出错: {e}"

if __name__ == "__main__":
    # 测试函数
    owner = "torvalds"
    repo = "linux"
    
    print("测试选项1：直接概括")
    summary1 = summarize_commits_with_ollama(owner, repo, option=1, days=1)
    print("选项1结果:")
    print(summary1)
    
    print("\n" + "="*50 + "\n")
    
    print("测试选项2：基于diff的分析")
    summary2 = summarize_commits_with_ollama(owner, repo, option=2, days=1)
    print("选项2结果:")
    print(summary2)