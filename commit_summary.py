#!/bin/env python3
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from croniter import croniter

try:
    from serverchan_sdk import sc_send
except ImportError:
    # 如果serverchan_sdk不可用，创建一个模拟函数
    def sc_send(sendkey, title, desp, options=None):
        print(f"[ServerChan模拟] {title}")
        print(f"内容: {desp}")
        return {"code": 0, "message": "模拟发送成功"}

# 导入原有的功能函数
from ollama_read_commit import summarize_commits_with_ollama


def setup_logging(level="INFO", log_file=None):
    """设置日志配置"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 配置日志处理器
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def load_config(config_path):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")


def validate_repository_config(repo_config):
    """验证仓库配置"""
    required_fields = ['owner', 'repo', 'option', 'days', 'schedule']
    
    for field in required_fields:
        if field not in repo_config:
            raise ValueError(f"仓库配置缺少必要字段: {field}")
    
    if repo_config['option'] not in [1, 2]:
        raise ValueError("option 必须是 1 或 2")
    
    if not isinstance(repo_config['days'], int) or repo_config['days'] <= 0:
        raise ValueError("days 必须是正整数")
    
    # 验证cron表达式
    try:
        croniter(repo_config['schedule'])
    except Exception as e:
        raise ValueError(f"无效的cron表达式: {e}")


def check_schedule(repo_config, current_time=None, executed_cache=None):
    """检查是否应该执行总结任务"""
    if current_time is None:
        current_time = datetime.now()
    
    if not repo_config.get('enabled', True):
        return False
    
    # 使用执行缓存来避免重复执行
    if executed_cache is None:
        executed_cache = {}
    
    repo_key = f"{repo_config['owner']}/{repo_config['repo']}"
    
    # 计算当前调度周期的标识（基于cron表达式）
    cron = croniter(repo_config['schedule'], current_time)
    prev_run = cron.get_prev(datetime)
    current_period_key = prev_run.strftime('%Y%m%d%H%M')
    
    # 检查是否已经在当前周期执行过
    if repo_key in executed_cache and executed_cache[repo_key] == current_period_key:
        return False
    
    # 检查是否在计划执行时间附近（5分钟内）
    time_diff = (current_time - prev_run).total_seconds() / 60  # 转换为分钟
    should_execute = 0 <= time_diff <= 5  # 5分钟窗口
    
    if should_execute:
        # 标记为已执行
        executed_cache[repo_key] = current_period_key
    
    return should_execute


def send_notification(sendkey, title, content, tags=None):
    """发送ServerChan通知"""
    try:
        if not sendkey:
            logging.warning("未配置ServerChan sendkey，跳过通知发送")
            return False
        
        # 构建通知内容
        desp = content
        options = {}
        if tags:
            options["tags"] = tags
        
        response = sc_send(sendkey, title, desp, options)
        logging.info(f"通知发送结果: {response}")
        return True
    
    except Exception as e:
        logging.error(f"发送通知失败: {e}")
        return False


def process_repository(repo_config, global_config, logger):
    """处理单个仓库的总结任务"""
    owner = repo_config['owner']
    repo = repo_config['repo']
    option = repo_config['option']
    days = repo_config['days']
    
    logger.info(f"开始处理仓库: {owner}/{repo}")
    
    try:
        # 获取GitHub token
        token = global_config.get('github', {}).get('token')
        
        # 获取Ollama配置
        ollama_config = global_config.get('ollama', {})
        model = ollama_config.get('model', 'llama2')
        
        # 执行总结
        summary = summarize_commits_with_ollama(
            owner=owner,
            repo=repo,
            option=option,
            days=days,
            token=token,
            model=model
        )
        
        if summary and "在" in summary and "天内没有找到" in summary:
            logger.info(f"仓库 {owner}/{repo} 在 {days} 天内没有新的commit")
            return None
        
        logger.info(f"成功生成 {owner}/{repo} 的总结")
        
        # 构建通知标题
        title = f"[{owner}/{repo}] Commit总结 - {datetime.now().strftime('%Y-%m-%d')}"
        
        return {
            'title': title,
            'content': summary,
            'repo': f"{owner}/{repo}"
        }
    
    except Exception as e:
        logger.error(f"处理仓库 {owner}/{repo} 时出错: {e}")
        return None


def run_polling_mode(config, logger, args):
    """运行轮询模式"""
    polling_config = config.get('polling', {})
    if not polling_config.get('enabled', False):
        logger.info("轮询模式未启用")
        return
    
    interval = polling_config.get('interval', 60)  # 默认60秒
    daemon = polling_config.get('daemon', False)
    
    logger.info(f"启动轮询模式，间隔: {interval}秒, 守护进程: {daemon}")
    
    # 初始化执行缓存
    executed_cache = {}
    
    if daemon:
        logger.info("运行在守护进程模式")
        try:
            while True:
                try:
                    executed_cache = run_single_cycle(config, logger, args, executed_cache)
                    logger.info(f"等待 {interval} 秒后进行下一次检查...")
                    time.sleep(interval)
                except KeyboardInterrupt:
                    logger.info("接收到键盘中断，退出守护进程模式")
                    break
                except Exception as e:
                    logger.error(f"轮询周期执行出错: {e}")
                    logger.info(f"等待 {interval} 秒后重试...")
                    time.sleep(interval)
        except Exception as e:
            logger.error(f"守护进程模式出错: {e}")
    else:
        # 非守护进程模式，允许键盘中断
        try:
            while True:
                executed_cache = run_single_cycle(config, logger, args, executed_cache)
                logger.info(f"等待 {interval} 秒后进行下一次检查...")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("用户中断轮询模式")


def run_single_cycle(config, logger, args, executed_cache=None):
    """运行单个轮询周期"""
    if executed_cache is None:
        executed_cache = {}
    
    logger.info("开始轮询检查...")
    
    # 获取配置
    serverchan_config = config.get('serverchan', {})
    sendkey = serverchan_config.get('sendkey', '')
    repositories = config.get('repositories', [])
    
    if not repositories:
        logger.error("配置文件中没有配置任何仓库")
        return
    
    # 处理仓库
    results = []
    current_time = datetime.now()
    
    for repo_config in repositories:
        owner = repo_config['owner']
        repo = repo_config['repo']
        repo_full_name = f"{owner}/{repo}"
        
        # 检查是否应该处理该仓库
        if args.repo and args.repo != repo_full_name:
            continue
        
        # 使用修复后的check_schedule函数
        if not check_schedule(repo_config, current_time, executed_cache):
            logger.debug(f"跳过 {repo_full_name} (未到达调度时间或已执行)")
            continue
        
        # 覆盖天数设置
        if args.days:
            repo_config['days'] = args.days
        
        # 处理仓库
        result = process_repository(repo_config, config, logger)
        if result:
            results.append(result)
    
    # 发送通知
    if results and sendkey:
        logger.info(f"准备发送 {len(results)} 个仓库的总结通知")
        
        # 合并所有结果
        all_content = []
        for result in results:
            all_content.append(f"## {result['title']}")
            all_content.append(result['content'])
            all_content.append("")  # 空行分隔
        
        combined_content = "\n".join(all_content)
        combined_title = f"GitHub Commit总结 - {current_time.strftime('%Y-%m-%d %H:%M')}"
        
        # 添加标签
        tags = "GitHub|Commit总结"
        
        success = send_notification(sendkey, combined_title, combined_content, tags)
        if success:
            logger.info("通知发送成功")
        else:
            logger.error("通知发送失败")
    
    return executed_cache

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GitHub Commit Summary Tool')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-k', '--sendkey', help='ServerChan sendkey (会覆盖配置文件中的值)')
    parser.add_argument('--check-schedule', action='store_true', help='检查定时任务但不执行')
    parser.add_argument('--run-all', action='store_true', help='执行所有仓库的总结')
    parser.add_argument('--repo', help='只处理指定的仓库 (格式: owner/repo)')
    parser.add_argument('--days', type=int, help='覆盖默认的天数设置')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    parser.add_argument('--polling', action='store_true', help='启用轮询模式')
    parser.add_argument('--daemon', action='store_true', help='启用守护进程模式')
    
    args = parser.parse_args()
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 设置日志
        log_config = config.get('logging', {})
        log_level = args.log_level or log_config.get('level', 'INFO')
        log_file = log_config.get('file')
        
        logger = setup_logging(log_level, log_file)
        logger.info("GitHub Commit Summary Tool 启动")
        
        # 处理sendkey参数
        if args.sendkey:
            config['serverchan']['sendkey'] = args.sendkey
        
        # 获取ServerChan配置
        serverchan_config = config.get('serverchan', {})
        sendkey = serverchan_config.get('sendkey', '')
        
        if not sendkey:
            logger.warning("未配置ServerChan sendkey，将不会发送通知")
        
        # 获取仓库配置
        repositories = config.get('repositories', [])
        if not repositories:
            logger.error("配置文件中没有配置任何仓库")
            return 1
        
        # 验证仓库配置
        for repo_config in repositories:
            try:
                validate_repository_config(repo_config)
            except ValueError as e:
                logger.error(f"仓库配置验证失败: {e}")
                return 1
        
        # 处理轮询模式参数
        if args.polling or args.daemon or config['polling']['enabled'] or config['polling']['daemon']:
            # 命令行参数优先级高于配置文件
            config['polling']['enabled'] = True
            if args.daemon:
                config['polling']['daemon'] = True
            return run_polling_mode(config, logger, args)
        
        # 检查定时任务模式
        if args.check_schedule:
            logger.info("检查定时任务调度...")
            current_time = datetime.now()
            
            for repo_config in repositories:
                owner = repo_config['owner']
                repo = repo_config['repo']
                should_run = check_schedule(repo_config, current_time)
                
                status = "应该执行" if should_run else "跳过"
                logger.info(f"{owner}/{repo}: {status} (schedule: {repo_config['schedule']})")
            
            return 0
        
        # 单次执行模式
        run_single_cycle(config, logger, args)
        return 0
    
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())