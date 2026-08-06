"""
发送钉钉机器人消息（加签版）
用法:
    import dingding_bot
    dingding_bot.send_msg("晚安 玛卡巴卡~", "https://oapi.dingtalk.com/robot/send?access_token=xxx", "SECxxx")
"""
import base64, hashlib, hmac, json, time, urllib.parse
import requests   # 非标准库，需 pip install requests

def send_msg(msg: str, hook: str, secret: str, timeout: int = 10) -> dict:
    # 1. 构造签名
    timestamp = str(round(time.time() * 1000))
    sign_str  = f"{timestamp}\n{secret}"
    sign_bin  = hmac.new(
        secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(sign_bin))

    # 2. 拼最终 URL
    url = f"{hook}&timestamp={timestamp}&sign={sign}"

    # 3. 发送
    resp = requests.post(
        url,
        data=json.dumps({"msgtype": "text", "text": {"content": msg}}),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()