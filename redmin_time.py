# -*- coding: utf-8 -*-
"""
Redmine 自动填写工时脚本。

通过 Windows 任务计划程序调用，仅在工作日执行。
配置从同目录下的 config.toml 读取，敏感信息（账号、密码、钉钉密钥等）不再硬编码。
"""

import argparse
import logging
import random
import sys
import tomllib
import traceback
from datetime import date
from pathlib import Path

import chinese_calendar as cal
from playwright.sync_api import sync_playwright


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")
DEFAULT_LOG_FILE = Path(__file__).with_name("redmine_time.log")

logger = logging.getLogger("redmine_time")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """加载 TOML 配置文件；文件不存在或解析失败时抛出异常。"""
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with path.open("rb") as f:
        return tomllib.load(f)


def setup_logging(*, debug: bool, log_file: Path):
    """配置日志：debug=True 时同时输出到控制台，否则仅写入文件。"""
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    logger.handlers = []

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if debug:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)


def fill_time_entry(
    page,
    hours: str,
    comment_index: int,
    activity_id: str,
    activity_type: str = "功能开发",
    use_ai: bool = True,
):
    """填写工时并提交。"""
    logger.info("开始填写工时...")
    page.fill("#time_entry_hours", str(hours))
    logger.debug(" filled hours: %s", hours)

    page.select_option("#time_entry_comments", index=comment_index)
    logger.debug(" selected comment index %s", comment_index)

    page.select_option("#time_entry_activity_id", activity_id)
    logger.debug(" selected activity id %s", activity_id)

    # Redmine 自定义字段
    page.select_option("#time_entry_custom_field_values_116", activity_type)
    logger.debug(" selected activity type: %s", activity_type)

    ai_value = "1" if use_ai else "0"
    page.locator(
        f'input[name="time_entry[custom_field_values][117]"][value="{ai_value}"]'
    ).check()
    logger.debug(" selected use_ai: %s", use_ai)

    non_ai_hours = random.randint(1, int(hours)) * 0.5
    page.fill("#time_entry_custom_field_values_118", str(non_ai_hours))
    logger.debug(" filled non-AI hours: %s", non_ai_hours)

    page.click('input[name="commit"]')
    logger.info("点击提交按钮，等待页面响应...")
    page.wait_for_load_state("networkidle")
    logger.info("工时提交完成")


def login(page, username: str, password: str, max_retries: int = 2) -> bool:
    """执行登录，最多重试 max_retries 次。返回是否成功。"""
    for attempt in range(1, max_retries + 1):
        logger.info("第 %d/%d 次尝试登录...", attempt, max_retries)
        page.fill("#username", username)
        logger.debug(" filled username: %s", username)
        page.fill("#password", password)
        logger.debug(" filled password: ***")

        page.click("#login-submit")
        page.wait_for_load_state("networkidle")

        if not page.locator("#login-submit").count():
            logger.info("登录成功")
            return True

        logger.warning("登录失败，页面仍存在登录按钮")
        if attempt < max_retries:
            page.reload()

    logger.error("登录失败，已达最大重试次数")
    return False


def send_goodnight(hook: str, secret: str, username: str):
    """打卡完成后发送钉钉消息。"""
    import dingding_bot

    logger.info("准备发送钉钉消息...")
    msg = f"晚安，{username}~"
    dingding_bot.send_msg(msg, hook, secret)
    logger.info("钉钉消息已发送")


def run_once(config: dict, *, debug: bool):
    """执行一次完整的打卡流程。"""
    redmine = config.get("redmine", {})
    username = redmine["username"]
    password = redmine["password"]
    base_url = redmine["base_url"]
    hours = redmine.get("hours", 8)
    comment_index = redmine.get("comment_index", 0)
    activity_id = redmine.get("activity_id", "34")
    # debug 模式强制显示浏览器窗口，方便排查问题
    headless = not debug and redmine.get("headless", True)

    custom_fields = config.get("custom_fields", {})
    activity_type = custom_fields.get("activity_type", "功能开发")
    use_ai = custom_fields.get("use_ai", True)

    dingtalk = config.get("dingtalk", {})
    bot_enabled = dingtalk.get("enabled", False)
    bot_hook = dingtalk.get("hook", "")
    bot_secret = dingtalk.get("secret", "")

    with sync_playwright() as p:
        logger.info("启动浏览器, headless=%s", headless)
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            logger.info("访问: %s", base_url)
            page.goto(base_url)
            page.wait_for_load_state("networkidle")
            logger.info("页面加载完成")

            if page.locator("#login-submit").count():
                if not login(page, username, password):
                    raise RuntimeError("Redmine 登录失败")

            fill_time_entry(
                page,
                hours,
                comment_index,
                activity_id,
                activity_type=activity_type,
                use_ai=use_ai,
            )
        finally:
            page.close()
            browser.close()
            logger.info("浏览器已关闭")

    if bot_enabled:
        try:
            send_goodnight(bot_hook, bot_secret, username)
        except Exception as e:
            logger.error("钉钉消息发送失败: %s", e)
            logger.error(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description="Redmine 自动填写工时脚本")
    parser.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--debug", "-d", action="store_true", help="开启 debug 模式：日志输出到控制台并显示浏览器窗口")
    args = parser.parse_args()

    config = load_config(args.config)

    debug = args.debug or config.get("log", {}).get("debug", False)
    log_file = Path(config.get("log", {}).get("file", DEFAULT_LOG_FILE))
    setup_logging(debug=debug, log_file=log_file)

    logger.info("=" * 40)
    logger.info("脚本启动")
    logger.info("今天是: %s, 是否工作日: %s", date.today(), cal.is_workday(date.today()))

    if not cal.is_workday(date.today()):
        logger.info("今天不是工作日，跳过打卡")
        return

    try:
        run_once(config, debug=debug)
        logger.info("脚本执行完毕")
    except Exception as e:
        logger.error("脚本执行异常: %s", e)
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
