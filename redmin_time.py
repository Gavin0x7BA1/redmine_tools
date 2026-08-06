# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import dingding_bot, requests, sys
import chinese_calendar as cal
from datetime import date
import time, json, random, os
import argparse, logging, traceback

# 安装环境(python 3.14.0):
# pip install playwright
# playwright install chromium

# ========== 配置 ==========
USERNAME = "wukong"
PASSWORD = "O2cewK8*vcthI9Q#6iabJvOLEZDt4!yQ"
BASE_URL = "http://1.2.3.4/redmine/projects/touch_fish/time_entries/new"
BOT_MSG = True
BOT_HOOK="https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxx"
BOT_KEY="SECxxxxxxxxxxx"
HEADLESS = True          # 调通后可设为 True 后台运行
# ==========================

LOG_FILE = "redmine_time.log"
logger = logging.getLogger("redmine_time")


def setup_logging(debug: bool):
    """配置日志：debug=True时输出到控制台+文件，否则仅输出到文件"""
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    # 清空已有 handler，避免重复添加
    logger.handlers = []

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件 handler（始终启用，记录 INFO 及以上）
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 控制台 handler（debug 模式启用）
    if debug:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    
def input_time(page):
    """填写 8h 并提交工时"""
    logger.info("开始填写工时...")
    page.fill("#time_entry_hours", "8")
    logger.debug(" filled hours: 8")
    page.select_option("#time_entry_comments", index=0)
    logger.debug(" selected comment index 0")
    page.select_option("#time_entry_activity_id", "34")
    logger.debug(" selected activity id 34")
    page.click('input[name="commit"]')
    logger.info("点击提交按钮，等待 10 秒...")
    page.wait_for_timeout(10_000)
    page.close()
    logger.info("页面已关闭")

def login(page):
    """登录入口"""
    logger.info("检测到登录页，开始登录...")
    page.fill("#username", USERNAME)
    logger.debug(f" filled username: {USERNAME}")
    page.fill("#password", PASSWORD)
    logger.debug(" filled password: ***")
    page.click("#login-submit")
    logger.info("点击登录，等待跳转...")
    page.wait_for_load_state("networkidle")  # 等跳转完成
    # 如果登录按钮还在，说明登录失败
    if page.locator("#login-submit").count():
        logger.warning("登录失败，页面仍有登录按钮，准备重试...")
        page.reload()
        login(page)
    else:
        logger.info("登录成功")
        input_time(page)

def main():
    logger.info("=" * 40)
    logger.info("脚本启动")
    logger.info(f"今天是: {date.today()}, 是否工作日: {cal.is_workday(date.today())}")
    
    try:
        with sync_playwright() as p:
            logger.info(f"启动浏览器, headless={HEADLESS}")
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            logger.info(f"访问: {BASE_URL}")
            page.goto(BASE_URL)
            page.wait_for_load_state("networkidle")  # 等跳转完成
            logger.info("页面加载完成")

            # 判断是否需要登录
            login_btn_count = page.locator("#login-submit").count()
            logger.debug(f"登录按钮数量: {login_btn_count}")
            if login_btn_count:
                login(page)
            else:
                logger.info("无需登录，直接填写工时")
                input_time(page)

            browser.close()
            logger.info("浏览器已关闭")
            
            if BOT_MSG:
                logger.info("准备发送钉钉消息...")
                question, opts = get_question_form_json()
                logger.debug(f"question: {question[:50]}...")
                logger.debug(f"answer: {opts[:50]}...")
                dingding_bot.send_msg(question, BOT_HOOK, BOT_KEY)
                logger.info("问题已发送，等待 10 分钟后发送答案...")
                time.sleep(600)
                dingding_bot.send_msg(opts, BOT_HOOK, BOT_KEY)
                logger.info("答案已发送")
            else:
                logger.info("BOT_MSG=False，跳过钉钉消息")
                
        logger.info("脚本执行完毕")
    except Exception as e:
        logger.error(f"脚本执行异常: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redmine 自动打卡脚本")
    parser.add_argument("--debug", "-d", action="store_true", help="开启 debug 日志输出到控制台")
    args = parser.parse_args()
    
    # setup_logging(args.debug)
    setup_logging(True)
    
    if cal.is_workday(date.today()):
        try:
            main()
        except Exception:
            sys.exit(1)
    else:
        logger.info("今天不是工作日，跳过打卡")
    sys.exit(0)
