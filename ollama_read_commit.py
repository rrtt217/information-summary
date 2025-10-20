import requests
import json
import logging
from datetime import datetime, timedelta, timezone
import time
from ollama import Client

# 设置日志
logger = logging.getLogger(__name__)

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
                        logger.info(f"API限制达到，等待 {wait_time:.0f} 秒")
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
            logger.error(f"第 {page} 页请求失败 (URL: {url}): {e}")
            break
        except Exception as e:
            logger.error(f"第 {page} 页处理出现意外错误: {e}")
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
            logger.warning(f"未找到比较对象: {base_sha}...{head_sha}")
            return None
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 diff 失败 (URL: {url}): {e}")
        return None
    except Exception as e:
        logger.error(f"获取 diff 时出现意外错误: {e}")
        return None

def get_readme(owner, repo, token=None):
    """
    获取仓库的README.md内容
    
    参数:
    - owner: 仓库所有者
    - repo: 仓库名
    - token: GitHub token (可选)
    
    返回:
    - README内容 (str) 或 None
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'commit-fetcher',
    }
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        response = requests.get(url, headers=headers)
        
        # 检查API限制
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers['X-RateLimit-Remaining'])
            if remaining == 0:
                reset_time = int(response.headers['X-RateLimit-Reset'])
                wait_time = reset_time - time.time()
                if wait_time > 0:
                    logger.info(f"API限制达到，等待 {wait_time:.0f} 秒")
                    time.sleep(wait_time + 1)
                    # 重试一次
                    response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        # 内容在'content'字段，是Base64编码的
        import base64
        content = base64.b64decode(data['content']).decode('utf-8')
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"获取README失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取README时出现意外错误: {e}")
        return None

def generate_readme_summary(owner, repo, token=None, model='llama2'):
    """
    从README生成中文概述
    
    参数:
    - owner: 仓库所有者
    - repo: 仓库名
    - token: GitHub token (可选)
    - model: Ollama模型名称 (默认: 'llama2')
    
    返回:
    - README中文概述 (str) 或 None
    """
    logger.info(f"正在获取 {owner}/{repo} 的README内容...")
    
    # 获取README内容
    readme_content = get_readme(owner, repo, token)
    if not readme_content:
        logger.warning("无法获取README内容")
        return None
    
    logger.info("成功获取README内容，正在生成中文概述...")
    
    # 使用Ollama生成中文概述
    prompt = f"""
        请对以下GitHub仓库的README内容进行中文概述：

        README内容：
        {readme_content[:10000]}  # 限制内容长度

        要求：
        1. 用中文进行概述
        2. 简要介绍仓库的主要功能和用途
        3. 突出仓库的核心特点
        4. 保持简洁明了，不超过200字

        请提供中文概述："""
    
    summary = call_ollama(prompt, model)
    return summary

def call_ollama(prompt, model='llama2'):
    """
    调用Ollama进行文本概括，使用Ollama Python库
    
    参数:
    - prompt: 输入提示
    - model: Ollama模型名称 (默认: 'llama2')
    """
    try:
        # 使用Ollama Python库
        client = Client(host='http://localhost:11434')
        response = client.generate(model=model, prompt=prompt, stream=False)
        return response.get('response', "")
    except Exception as e:
        logger.error(f"Ollama调用失败: {e}")
        return f"Ollama调用失败: {e}"

def summarize_commits_with_ollama(owner, repo, option=1, days=1, token=None, model='llama2'):
    """
    主函数：获取最近n天的commit，使用Ollama进行概括
    
    参数:
    - owner: 仓库所有者
    - repo: 仓库名
    - option: 处理选项 (1=直接概括, 2=基于diff生成message)
    - days: 最近多少天
    - token: GitHub token (可选)
    - model: Ollama模型名称 (默认: 'llama2')
    
    返回:
    - 概括内容 (str)
    """
    logger.info(f"开始获取 {owner}/{repo} 最近 {days} 天的commit...")
    
    # 获取commit消息
    try:
        commit_messages = get_recent_commit_messages(owner, repo, days=days, token=token)
    except Exception as e:
        return f"获取commit消息时出错: {e}"
    
    if not commit_messages:
        return f"在 {days} 天内没有找到 {owner}/{repo} 的commit"
    
    logger.info(f"找到 {len(commit_messages)} 个commit")
    
    if option == 1:
        # 选项1：直接翻译概括commit message
        return summarize_direct_option(commit_messages, owner, repo, model, token)
    elif option == 2:
        # 选项2：根据相邻commit的diff生成message
        return summarize_with_diff_option(commit_messages, owner, repo, days, token, model)
    else:
        return "无效的选项，请选择1或2"

def summarize_direct_option(commit_messages, owner, repo, model='llama2', token=None):
    """
    选项1：直接翻译概括commit message
    
    参数:
    - commit_messages: commit消息列表
    - owner: 仓库所有者
    - repo: 仓库名
    - model: Ollama模型名称 (默认: 'llama2')
    - token: GitHub token (可选)
    """
    logger.info("使用选项1：直接翻译概括commit message")
    
    # 获取README中文概述
    readme_summary = generate_readme_summary(owner, repo, token, model)
    if readme_summary:
        logger.info("成功获取README中文概述")
    
    # 将所有commit消息合并成一个文本
    combined_messages = "\n".join([f"Commit {i+1}: {msg}" for i, msg in enumerate(commit_messages)])
    
    prompt = f"""
        GitHub仓库 {owner}/{repo} 的概述：
        {readme_summary if readme_summary else '无README概述'}
        根据上述信息，请对以下来自GitHub仓库 {owner}/{repo} 的commit消息进行概括总结：

        {combined_messages}

        要求：
        1. 用中文进行概括
        2. 按功能模块或主题分类
        3. 突出重要变更
        4. 保持简洁明了

        请提供概括总结："""
    
    print("调用Ollama进行概括...")
    summary = call_ollama(prompt, model)
    return summary

def summarize_with_diff_option(commit_messages, owner, repo, days=1, token=None, model='llama2'):
    """
    选项2：根据相邻commit的diff生成message，然后与原来的commit message配对进行概括
    
    参数:
    - commit_messages: commit消息列表
    - owner: 仓库所有者
    - repo: 仓库名
    - token: GitHub token
    - model: Ollama模型名称 (默认: 'llama2')
    """
    print("使用选项2：根据diff生成message并配对概括")
    
    # 获取README中文概述
    readme_summary = generate_readme_summary(owner, repo, token, model)
    if readme_summary:
        print("成功获取README中文概述")
    
    # 为了简化，这里只处理前几个commit的diff
    if len(commit_messages) < 2:
        return "commit数量不足，无法进行diff分析"
    
    print("获取commit的详细信息以进行diff分析...")
    
    # 获取完整的commit列表以获取SHA值
    since_date = (datetime.now(tz=timezone(timedelta(hours=0))) - timedelta(days=days)).isoformat()
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
        
        if not commits:
            return "无法获取commit列表"
        if len(commits) < 2:
            return "commit数量不足，无法进行diff分析"
        
        generated_message = ""

        for i in range(len(commits)-1):
            # 获取相邻两个commit进行diff分析
            base_sha = commits[i+1]['sha']  # 较旧的commit
            head_sha = commits[i]['sha']  # 较新的commit
        
            print(f"比较commit {base_sha[:7]}...{head_sha[:7]}")
        
            # 获取diff
            diff_text = get_diff_between_commits(owner, repo, base_sha, head_sha, token=token, raw=True)
        
            if diff_text is None:
                return "无法获取diff信息"
            
            # 使用Ollama分析diff并生成message
            diff_prompt = f"""
                以下是来自GitHub仓库 {owner}/{repo} 的两个相邻commit之间的diff，该仓库的概述如下：
                
                {readme_summary if readme_summary else '无README概述'}
                
                请分析以下Git diff并生成一个简洁的commit消息描述这个变更：

                {diff_text[:65536]}  # 限制diff长度
        
                根据这个diff，生成的commit消息应该描述："""
        
            generated_message += (str(i+1) + "." + call_ollama(diff_prompt, model) + "\n")
        
        original_message = commit_messages[0] if commit_messages else "无原始消息"
        
        # 将生成的message与原始message配对，然后进行概括
        pair_prompt = f"""
            请整合以下两个commit消息并给出概括：

            原始commit消息:
            {original_message}

            基于diff生成的commit消息:
            {generated_message}

            请对这两个commit消息进行整合，并提供一个综合的概括总结：

            概括总结："""
        
        final_summary = call_ollama(pair_prompt, model)
        
        return final_summary
                
    except requests.exceptions.RequestException as e:
        return f"请求commit列表时出错: {e}"
    except Exception as e:
        return f"在diff分析过程中出错: {e}"

if __name__ == "__main__":
    owner = "ggml-org"
    repo = "llama.cpp"
    
    print("测试选项1：直接概括")
    summary1 = summarize_commits_with_ollama(owner, repo, option=1, days=1, model='granite4-64k:micro-h')
    print("选项1结果:")
    print(summary1)
    
    print("\n" + "="*50 + "\n")
    
    print("测试选项2：基于diff的分析")
    summary2 = summarize_commits_with_ollama(owner, repo, option=2, days=1, model='granite4-64k:micro-h')
    print("选项2结果:")
    print(summary2)
