#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软考成绩查询通知监控程序
监控 https://www.ruankao.org.cn/index/work/1.html
当出现"2026年上半年计算机软件资格考试成绩查询通知"时发送通知
"""

import requests
import time
import yaml
import logging
import smtplib
import json
import hashlib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ===================== 日志配置 =====================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "monitor.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ===================== 配置加载 =====================
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===================== 状态持久化 =====================
STATE_FILE = os.path.join(LOG_DIR, ".state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"notified": False, "last_hash": "", "found_urls": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===================== 网页抓取 =====================
TARGET_URL = "https://www.ruankao.org.cn/index/work/1.html"
# 备用：也检查通知公告首页
BACKUP_URLS = [
    "https://www.ruankao.org.cn/index/work/1.html",
    "https://www.ruankao.org.cn/article/list/1.html",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url, timeout=30):
    """抓取页面内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=True)
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        logger.error(f"请求失败 {url}: {e}")
        return None


def parse_notifications(html):
    """
    解析页面中的通知列表，提取标题和链接
    适配 ruankao.org.cn 的页面结构
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # 策略1: 查找所有 <a> 标签中包含通知标题的
    for a_tag in soup.find_all("a", href=True):
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if title and len(title) > 5:
            full_url = urljoin(TARGET_URL, href)
            items.append({"title": title, "url": full_url})

    # 策略2: 查找 li 标签中的链接（常见列表结构）
    for li in soup.find_all("li"):
        a_tag = li.find("a", href=True)
        if a_tag:
            title = a_tag.get_text(strip=True)
            href = a_tag["href"]
            if title and len(title) > 5:
                full_url = urljoin(TARGET_URL, href)
                if not any(item["url"] == full_url for item in items):
                    items.append({"title": title, "url": full_url})

    # 策略3: 查找 div 带 class 含 list/item/article 的容器
    for container in soup.find_all(["div", "ul", "section"],
                                    class_=lambda x: x and any(
                                        kw in str(x).lower()
                                        for kw in ["list", "item", "article", "news", "notice"]
                                    )):
        for a_tag in container.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag["href"]
            if title and len(title) > 5:
                full_url = urljoin(TARGET_URL, href)
                if not any(item["url"] == full_url for item in items):
                    items.append({"title": title, "url": full_url})

    return items


def check_keyword(title, keywords):
    """检查标题是否包含所有关键字"""
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() not in title_lower:
            return False
    return True


# ===================== 通知发送 =====================

def send_email(config, subject, body):
    """通过SMTP发送邮件通知"""
    email_cfg = config["email"]
    if not email_cfg.get("enabled", False):
        logger.info("邮件通知未启用")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = email_cfg["sender"]
    msg["To"] = email_cfg["receiver"]
    msg["Subject"] = subject

    # 纯文本
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # HTML 格式
    html_body = f"""
    <html>
    <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; 
                    border-radius: 8px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; color: white; text-align: center;">
                <h2 style="margin: 0;">🎯 软考成绩通知</h2>
            </div>
            <div style="padding: 20px;">
                <p style="font-size: 16px; color: #333;">{body}</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    此邮件由飞牛NAS上的软考监控程序自动发送<br>
                    发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if email_cfg.get("use_ssl", True):
            server = smtplib.SMTP_SSL(email_cfg["smtp_server"], email_cfg.get("smtp_port", 465))
        else:
            server = smtplib.SMTP(email_cfg["smtp_server"], email_cfg.get("smtp_port", 587))
            server.starttls()

        server.login(email_cfg["sender"], email_cfg["password"])
        server.sendmail(email_cfg["sender"], email_cfg["receiver"], msg.as_string())
        server.quit()
        logger.info(f"✅ 邮件发送成功 -> {email_cfg['receiver']}")
        return True
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {e}")
        return False


def send_webhook(config, title, url, message):
    """通过Webhook发送通知（支持企业微信/钉钉/Server酱/Bark等）"""
    webhook_cfg = config.get("webhook", {})
    if not webhook_cfg.get("enabled", False):
        return False

    webhook_type = webhook_cfg.get("type", "generic")
    webhook_url = webhook_cfg.get("url", "")

    if not webhook_url:
        return False

    try:
        if webhook_type == "wechat_work":
            # 企业微信机器人
            payload = {
                "msgtype": "text",
                "text": {"content": f"🎯 软考成绩通知\n\n{message}\n\n链接: {url}"}
            }
        elif webhook_type == "dingtalk":
            # 钉钉机器人
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "软考成绩通知",
                    "text": f"## 🎯 软考成绩通知\n\n{message}\n\n[点击查看]({url})"
                }
            }
        elif webhook_type == "serverchan":
            # Server酱
            payload = {
                "title": f"软考成绩通知: {title}",
                "desp": f"{message}\n\n[点击查看详情]({url})"
            }
        elif webhook_type == "bark":
            # Bark (iOS推送)
            payload = {
                "title": "软考成绩通知",
                "body": message,
                "url": url,
            }
        else:
            # 通用Webhook
            payload = {
                "title": title,
                "url": url,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }

        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ Webhook通知发送成功 ({webhook_type})")
            return True
        else:
            logger.error(f"❌ Webhook返回异常: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Webhook发送失败: {e}")
        return False


def send_notifications(config, matched_items):
    """发送所有配置的通知渠道"""
    for item in matched_items:
        title = item["title"]
        url = item["url"]
        message = f"检测到新通知：{title}\n\n请前往查询成绩！\n链接：{url}"

        subject = f"🎯 软考成绩通知 - {title}"
        body = f"检测到新通知：\n\n【{title}】\n\n👉 查看详情：{url}\n\n请尽快前往查询成绩！"

        send_email(config, subject, body)
        send_webhook(config, title, url, message)


# ===================== 主循环 =====================

def run_check(config):
    """执行一次检查"""
    state = load_state()
    keywords = config.get("keywords", ["2026年上半年", "成绩查询"])
    check_interval = config.get("check_interval_seconds", 300)

    logger.info(f"🔍 开始检查... 关键字: {keywords}")

    all_matched = []
    all_items = []

    for url in BACKUP_URLS:
        logger.info(f"正在抓取: {url}")
        html = fetch_page(url)
        if html is None:
            continue

        items = parse_notifications(html)
        logger.info(f"解析到 {len(items)} 条通知")
        all_items.extend(items)

        for item in items:
            if check_keyword(item["title"], keywords):
                logger.info(f"🎯 匹配到: {item['title']} -> {item['url']}")
                # 检查是否已经通知过
                url_hash = hashlib.md5(item["url"].encode()).hexdigest()
                if url_hash not in state.get("found_urls", []):
                    all_matched.append(item)
                    state.setdefault("found_urls", []).append(url_hash)

    if all_matched:
        logger.info(f"🎉 发现 {len(all_matched)} 条新匹配通知！")
        send_notifications(config, all_matched)
        state["notified"] = True
        save_state(state)

        # 如果配置了找到后停止
        if config.get("stop_after_found", False):
            logger.info("已配置 stop_after_found=true，程序将退出")
            return False
    else:
        logger.info("未发现新的匹配通知")

    save_state(state)
    return True


def main():
    logger.info("=" * 60)
    logger.info("🚀 软考成绩通知监控程序启动")
    logger.info("=" * 60)

    config = load_config()
    check_interval = config.get("check_interval_seconds", 300)

    logger.info(f"监控目标: {TARGET_URL}")
    logger.info(f"检查关键字: {config.get('keywords', [])}")
    logger.info(f"检查间隔: {check_interval}秒")
    logger.info(f"邮件通知: {'启用' if config.get('email', {}).get('enabled') else '未启用'}")
    logger.info(f"Webhook通知: {'启用' if config.get('webhook', {}).get('enabled') else '未启用'}")
    logger.info("=" * 60)

    while True:
        try:
            should_continue = run_check(config)
            if not should_continue:
                break
        except KeyboardInterrupt:
            logger.info("收到退出信号，程序结束")
            break
        except Exception as e:
            logger.error(f"检查过程出错: {e}", exc_info=True)

        logger.info(f"⏳ 等待 {check_interval} 秒后再次检查...\n")
        time.sleep(check_interval)


if __name__ == "__main__":
    main()