# Redmine 自动工时填报

用于 Windows 任务计划程序自动调用，在工作日自动登录 Redmine 并填写每日工时。

## 功能

- 自动登录 Redmine 并填报工时
- 仅工作日执行（支持调休，依赖 `chinese_calendar`）
- 打卡成功后可选发送钉钉消息
- 配置从 `config.toml` 读取，敏感信息不再硬编码

## 环境要求

- Python 3.11+（脚本使用标准库 `tomllib`）
- Windows（用于任务计划程序调度）

## 安装

```bash
pip install requests
pip install chinese_calendar
pip install playwright
playwright install chromium
```

## 配置

1. 复制参考配置文件：

```bash
copy config.toml.example config.toml
```

2. 编辑 `config.toml`，填写 Redmine 账号、密码、页面地址以及钉钉机器人信息。

> **注意**：`config.toml` 已加入 `.gitignore`，不会提交到版本库，避免泄露敏感信息。

## 运行

```bash
python redmin_time.py
```

调试模式（显示浏览器窗口并输出控制台日志）：

```bash
python redmin_time.py --debug
```

使用指定配置文件：

```bash
python redmin_time.py --config /path/to/config.toml
```

## Windows 任务计划程序

1. 打开“任务计划程序”
2. 创建基本任务 → 设置触发器为“每天”
3. 操作选择“启动程序”
4. 程序/脚本填写 `python`，参数填写 `redmin_time.py`，起始于脚本所在目录
5. 建议在非工作时间段测试一次，确认能正常登录并填报

## 文件说明

| 文件 | 说明 |
|------|------|
| `redmin_time.py` | 主脚本 |
| `config.toml.example` | 配置文件模板 |
| `config.toml` | 本地配置文件（需自行创建，不提交） |
| `dingding_bot.py` | 钉钉机器人消息发送模块 |
| `redmine_time.log` | 运行日志 |
