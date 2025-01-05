import os
import requests
import sys

# 通知配置
config = {
    "telegram": {
        "bot_token": os.getenv("TG_BOT_TOKEN"),  # Telegram Bot Token
        "chat_id": os.getenv("TG_USER_ID"),     # Telegram Chat ID
    },
    "wecom": {
        "webhook_url": os.getenv("WECOM_WEBHOOK_URL"),  # 企业微信 Webhook URL
    },
    "dingding": {
        "webhook_url": os.getenv("DD_WEBHOOK_URL"),     # 钉钉 Webhook URL
    },
}


def send_notify(title, message, method="telegram"):
    """
    发送通知消息
    :param title: 通知标题
    :param message: 通知内容
    :param method: 通知方式 (telegram, wecom, dingding)
    """
    full_message = f"【{title}】\n{message}"

    if method == "telegram":
        send_telegram(full_message)
    elif method == "wecom":
        send_wecom(full_message)
    elif method == "dingding":
        send_dingding(full_message)
    else:
        print(f"未知的通知方式: {method}")


def send_telegram(message):
    """通过 Telegram 发送通知"""
    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]

    if not bot_token or not chat_id:
        print("Telegram 配置未正确设置！")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print("Telegram 通知发送成功！", response.json())
    except Exception as e:
        print(f"Telegram 通知发送失败: {e}")


def send_wecom(message):
    """通过企业微信发送通知"""
    webhook_url = config["wecom"]["webhook_url"]

    if not webhook_url:
        print("企业微信 Webhook 配置未正确设置！")
        return

    data = {"msgtype": "text", "text": {"content": message}}

    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        print("企业微信通知发送成功！", response.json())
    except Exception as e:
        print(f"企业微信通知发送失败: {e}")


def send_dingding(message):
    """通过钉钉发送通知"""
    webhook_url = config["dingding"]["webhook_url"]

    if not webhook_url:
        print("钉钉 Webhook 配置未正确设置！")
        return

    data = {"msgtype": "text", "text": {"content": message}}

    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        print("钉钉通知发送成功！", response.json())
    except Exception as e:
        print(f"钉钉通知发送失败: {e}")


if __name__ == "__main__":
    # 如果通过命令行调用
    if len(sys.argv) > 2:
        title = sys.argv[1]
        message = sys.argv[2]
        method = sys.argv[3] if len(sys.argv) > 3 else "telegram"
        send_notify(title, message, method)
    else:
        print("用法: python sfsy250106_notify.py <标题> <消息> [通知方式]")
