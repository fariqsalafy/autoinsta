"""Official Telegram publisher wrapper

Env:
- DLBOT_TOKEN
- DLBOT_CHAT_ID
"""
from dotenv import load_dotenv
import os, requests
import json, textwrap
from urllib.parse import quote

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('INSTAGRAMHUB_BOT_TOKEN') or os.getenv('DLBOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('INSTAGRAMHUB_CHAT_ID') or os.getenv('DLBOT_CHAT_ID')
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ''
TELEGRAM_TEST_URL = f"{TELEGRAM_API_BASE}/getMe"


def bot_ready():
    if not TELEGRAM_API_BASE:
        print('DLBOT_TOKEN missing in .env')
        return False
    try:
        r = requests.get(TELEGRAM_TEST_URL, timeout=15)
        if r.status_code == 200 and r.json().get('ok'):
            print('Bot ready. Chat ID:', TELEGRAM_CHAT_ID)
            return True
    except Exception as e:
        print('Telegram connection error:', e)
    return False


def send_text(text):
    if not TELEGRAM_API_BASE or not TELEGRAM_CHAT_ID:
        print('Bot not configured.')
        return None
    try:
        r = requests.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
                'reply_markup': json.dumps({
                    'inline_keyboard': [[{
                        'text': 'Bagikan ke Instagram',
                        'url': f'https://www.instagram.com/create/share/'
                    }]]
                })
            },
            timeout=30,
        )
        print('Response:', r.json())
        return r.json()
    except Exception as e:
        print('Telegram send error:', e)
        return None


def send_media(message, media_path=None):
    if not TELEGRAM_API_BASE or not TELEGRAM_CHAT_ID:
        print('Bot not configured.')
        return None

    caption = message.get('text', '') + '\n\n🟢 Tap foto ini, lalu pilih Bagikan ke Instagram.'
    if len(caption) > 1024:
        caption = caption[:1020] + '...'

    # 1) Try photo
    if media_path:
        try:
            with open(media_path, 'rb') as fh:
                r = requests.post(
                    f"{TELEGRAM_API_BASE}/sendPhoto",
                    data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'},
                    files={'photo': (os.path.basename(media_path), fh, 'image/jpeg')},
                    timeout=60,
                )
            data = r.json()
            if data.get('ok'):
                return data
        except Exception as e:
            print('sendPhoto failed:', e)

    # 2) Fallback text with IG button
    return send_text(caption)


def _chunks(text, size=4000):
    lines = text.splitlines()
    buf, l = [], 0
    out = []
    for line in lines:
        need = len(line) + 1
        if buf and l + need > size:
            out.append('\n'.join(buf))
            buf, l = [], 0
        buf.append(line)
        l += need
    if buf:
        out.append('\n'.join(buf))
    return out


def format_content_item(item):
    if not item:
        return ''
    tags = item.get('affiliate_tags') or []
    try:
        tags = json.loads(tags)
    except Exception:
        tags = [str(tags)]

    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [t.strip() for t in tags.split(',') if t.strip()]

    hashtags = ' '.join(['#' + t.strip().lstrip('#') for t in tags[:8]])
    title = (item.get('title') or 'KisahMu').title()
    body = item.get('body') or ''
    caption = (
        f"<b>{title}</b>\n\n"
        f"{body}\n\n"
        f"{hashtags}\n\n"
        f"<a href='https://www.instagram.com/kisahmu356/'>Follow @kisahmu356</a>"
    )
    csv = item.get('created_at') or ''
    return {
        'title': title,
        'caption': caption,
        'media_path': item.get('media_path') or '',
        'hashtags': hashtags,
        'item': item,
    }


def format_full(c):
    if not c:
        return '', ''
    title = (c.get('title') or 'KisahMu').title()
    body = c.get('body') or ''
    tags = c.get('affiliate_tags') or []
    try:
        tags = json.loads(tags)
    except Exception:
        tags = [t.strip() for t in str(tags).split(',') if t.strip()]

    hashtags = ' '.join(['#' + t.strip().lstrip('#') for t in tags[:10]])
    caption = (
        f"<b>{title}</b>\n\n"
        f"{body}\n\n"
        f"{hashtags}\n\n"
        f"Follow @kisahmu356 untuk inspirasimu tiap hari."
    )
    return caption, c.get('media_path') or ''


def send_rich_preview(item):
    if not TELEGRAM_API_BASE or not TELEGRAM_CHAT_ID:
        print('Bot not configured.')
        return None
    caption, media = format_full(item)
    if len(caption) > 1024:
        caption = caption[:1021] + '...'
    buttons = [[{'text': 'Buka @kisahmu356', 'url': 'https://www.instagram.com/kisahmu356/'},
                {'text': 'Buat Post IG', 'url': 'https://fariqsalafy.github.io/autoinsta/'} ]]
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': caption,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({'inline_keyboard': buttons})
    }
    try:
        if media:
            local_path = media if str(media).startswith('/') else '/sdcard/Hermes Project/autoinsta/' + str(media)
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    photo_bytes = f.read()
                photo_payload = {**payload, 'photo': ('preview.jpg', photo_bytes, 'image/jpeg')}
                r = requests.post(
                    f"{TELEGRAM_API_BASE}/sendPhoto",
                    data={k: v for k, v in photo_payload.items() if k != 'photo'},
                    files={'photo': photo_payload['photo']},
                    timeout=60,
                )
                data = r.json()
                if data.get('ok'):
                    return data
    except Exception as e:
        print('sendPhoto failed:', e)

    try:
        r = requests.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={**payload, 'text': caption + '\n\n[media tidak ditemukan]'},
            timeout=30
        )
        return r.json()
    except Exception as e:
        print('sendMessage failed:', e)
        return None


if __name__ == '__main__':
    if not bot_ready():
        print('Bot not ready. Check DLBOT_TOKEN and DLBOT_CHAT_ID.')