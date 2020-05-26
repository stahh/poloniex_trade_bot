import requests
from frontend.settings import TELEGRAM_TOKEN, CHANNEL


class SendMessageException(Exception):
    ...


def send_telegram(title, text):
    if not TELEGRAM_TOKEN or not CHANNEL:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        message = f'<b>{title}</b>\n<pre>{text}</pre>'

        r = requests.post(url=url, data={
            "chat_id": CHANNEL,
            "text": message,
            "parse_mode": 'HTML'
        })
        if r.status_code != 200:
            raise SendMessageException(f"Send to telegram error: {r.json()}")
    except SendMessageException as e:
        raise e
    except Exception:
        pass
