# GitHub Commit Summary Tool

自动监控GitHub仓库的commit变更，使用Ollama进行智能总结，并通过ServerChan推送通知。

## 功能特点

- 🔍 支持多个GitHub仓库同时监控
- 🤖 使用Ollama AI模型进行commit总结
- 📱 通过ServerChan推送通知到微信
- ⏰ 支持cron表达式定时任务
- 📝 两种总结模式：直接概括和基于diff分析
- 🔄 支持命令行参数灵活配置
- 📊 完整的日志记录功能

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd information-summary

# 安装依赖
pip install -r requirements.txt
```

## 配置

### 1. 配置文件 (config.json)

```json
{
  "repositories": [
    {
      "owner": "ggml-org",
      "repo": "llama.cpp",
      "option": 1,
      "days": 1,
      "schedule": "0 9 * * *",
      "enabled": true
    }
  ],
  "ollama": {
    "host": "http://localhost:11434",
    "model": "granite4-64k:micro-h"
  },
  "github": {
    "token": "your-github-token"
  },
  "serverchan": {
    "sendkey": "your-serverchan-sendkey"
  },
  "logging": {
    "level": "INFO",
    "file": "commit-summary.log"
  }
}
```

#### 配置说明

- **repositories**: 仓库配置列表
  - `owner`: 仓库所有者
  - `repo`: 仓库名称
  - `option`: 总结模式 (1=直接概括, 2=基于diff)
  - `days`: 总结最近多少天的commit
  - `schedule`: cron表达式，定义执行时间
  - `enabled`: 是否启用该仓库监控

- **ollama**: Ollama配置
  - `host`: Ollama服务地址
  - `model`: 使用的AI模型

- **github**: GitHub配置
  - `token`: GitHub访问令牌（可选，提高API限制）

- **serverchan**: ServerChan配置
  - `sendkey`: ServerChan发送密钥

- **logging**: 日志配置
  - `level`: 日志级别
  - `file`: 日志文件路径

### 2. Cron表达式说明

- `0 9 * * *`: 每天上午9点
- `0 10 * * 1`: 每周一上午10点
- `0 */6 * * *`: 每6小时一次
- `0 0 * * *`: 每天午夜

## 使用方法

### 基本用法

```bash
# 检查定时任务（不执行）
python commit_summary.py --check-schedule

# 执行所有仓库的总结
python commit_summary.py --run-all

# 指定配置文件
python commit_summary.py -c myconfig.json

# 指定ServerChan sendkey
python commit_summary.py -k your-sendkey

# 只处理特定仓库
python commit_summary.py --repo ggml-org/llama.cpp

# 覆盖天数设置
python commit_summary.py --days 7

# 设置日志级别
python commit_summary.py --log-level DEBUG
```

### 定时任务设置

添加到crontab：

```bash
# 每30分钟检查一次
*/30 * * * * cd /path/to/information-summary && python commit_summary.py

# 每天早上9点执行
0 9 * * * cd /path/to/information-summary && python commit_summary.py --run-all
```

### Systemd服务

创建服务文件 `/etc/systemd/system/commit-summary.service`:

```ini
[Unit]
Description=GitHub Commit Summary Tool
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/information-summary
ExecStart=/usr/bin/python3 commit_summary.py
```

创建定时器文件 `/etc/systemd/system/commit-summary.timer`:

```ini
[Unit]
Description=Run GitHub Commit Summary every 30 minutes
Requires=commit-summary.service

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

启用定时器：

```bash
sudo systemctl enable commit-summary.timer
sudo systemctl start commit-summary.timer
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-c, --config` | 配置文件路径 | `-c config.json` |
| `-k, --sendkey` | ServerChan sendkey | `-k your-key` |
| `--check-schedule` | 检查定时任务但不执行 | `--check-schedule` |
| `--run-all` | 执行所有仓库的总结 | `--run-all` |
| `--repo` | 只处理指定仓库 | `--repo owner/repo` |
| `--days` | 覆盖天数设置 | `--days 7` |
| `--log-level` | 日志级别 | `--log-level DEBUG` |

## 依赖要求

- Python 3.10+
- Ollama服务运行中
- 网络连接（访问GitHub API）

## 注意事项

1. **GitHub API限制**: 未认证请求每小时限制60次，使用token可提高到5000次
2. **Ollama服务**: 确保Ollama服务正在运行，并且有所需的模型
3. **ServerChan**: 需要注册并获取sendkey才能接收推送
4. **网络环境**: 确保能够访问GitHub和Ollama服务

## 故障排除

### 常见问题

1. **Ollama连接失败**
   - 检查Ollama服务是否运行：`systemctl status ollama`
   - 检查端口是否开放：`curl http://localhost:11434`

2. **GitHub API限制**
   - 添加GitHub token到配置文件
   - 减少请求频率

3. **ServerChan推送失败**
   - 检查sendkey是否正确
   - 检查网络连接

4. **定时任务不执行**
   - 检查时区设置
   - 验证cron表达式
   - 查看日志文件

## 更新日志

- v1.0.0: 初始版本，支持基本功能
- v1.1.0: 添加定时任务和配置文件支持
- v1.2.0: 添加ServerChan推送和日志功能

## 许可证

MIT License