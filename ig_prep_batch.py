"""IG prep batch tool - works without running HTTP server.

Usage:
  python3 ig_prep_batch.py preview        -> preview semua konten
  python3 ig_prep_batch.py ready          -> preview konten draft/ready
  python3 ig_prep_batch.py send-telegram  -> kirim preview ke Telegram bot
  python3 ig_prep_batch.py 1 2 3          -> preview berdasarkan content_id
"""
import os, sys, json
from datetime import datetime

import requests

try:
    from app import app, db, Content
except Exception:
    app = None


def _env(name, default=''):
    v = os.environ.get(name, '')
    if v:
        return v
    try:
        with open('.env') as fh:
            for line in fh:
                line = line.strip()
                if line.startswith('#'):
                    continue
                if '=' in line:
                    k, x, rest = line.partition('=')
                    if k == name and x == '=':
                        return rest
    except FileNotFoundError:
        pass
    return default


def telegram_send(token, chat_id, text):
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': text},
            timeout=30,
        )
    except Exception as e:
        print('Telegram send failed:', e)


def _make_caption(item):
    raw = item.get('affiliate_tags')
    tags = []
    if raw:
        if isinstance(raw, str):
            try:
                tags = json.loads(raw)
            except json.JSONDecodeError:
                s = raw.replace("'", '"').split(',')
                tags = [t.strip() for t in s if t.strip()]
        else:
            tags = list(raw)
    hashtags = ' '.join(['#' + t.strip().lstrip('#') for t in tags[:8]])
    body = item.get('body') or ''
    return f"{body}\n\n{hashtags}\n\nFollow @kisahmu356 untuk kisah inspiratif Nabi Muhammad SAW sehari-hari."


def load(cid):
    if app is None:
        raise RuntimeError('app.py not importable')
    with app.app_context():
        c = Content.query.get(cid)
        if not c:
            return None
        return {
            'id': c.id,
            'title': c.title or '',
            'body': c.body or '',
            'media_path': c.media_path or '',
            'status': c.status or 'draft',
            'category': c.category,
            'affiliate_tags': c.affiliate_tags,
        }


def preview_n(n=30):
    if app is None:
        raise RuntimeError('app.py not importable')
    out = []
    with app.app_context():
        rows = Content.query.order_by(Content.id.desc()).limit(n).all()
        for c in rows:
            out.append({
                'id': c.id,
                'title': c.title or '',
                'body': c.body or '',
                'media_path': c.media_path or '',
                'status': c.status or 'draft',
                'category': c.category,
                'affiliate_tags': c.affiliate_tags,
            })
    return out


def render(items):
    for item in items:
        caption = _make_caption(item)
        title = (item.get('title') or 'KisahMu').title()
        print('---')
        print('ID:', item['id'])
        print('JUDUL:', title)
        print('MEDIA:', item.get('media_path') or '(tidak ada)')
        print('CAPTION:\n', caption)
        print('STATUS:', item.get('status'))


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else 'preview'

    if cmd == 'send-telegram':
        token = _env('DLBOT_TOKEN', '')
        chat_id = _env('DLBOT_CHAT_ID', '')
        if not token or not chat_id:
            print('Butuh DLBOT_TOKEN dan DLBOT_CHAT_ID di .env atau env var.')
            return
        items = preview_n(50)
        ready = [it for it in items if (it.get('status') or 'draft') in ('draft', 'ready')]
        if not ready:
            print('Tidak ada konten draft/ready untuk dikirim.')
            return
        print(f'Mengirim {len(ready)} preview ke Telegram...')
        session = requests.Session()
        for item in ready:
            caption = _make_caption(item) + f"\n\nID: {item['id']} | media: {item.get('media_path') or 'upload manual'}"
            telegram_send = lambda t, cid, txt: session.post(
                f"https://api.telegram.org/bot{t}/sendMessage",
                json={'chat_id': cid, 'text': txt},
                timeout=30,
            )
            try:
                res = telegram_send(token, chat_id, caption)
                print('sent', item['id'], res.status_code)
            except Exception as e:
                print('failed', item['id'], e)
        print('send-telegram done')
        return

    ids = []
    unknown = []
    if args[1:]:
        ids = [int(x) for x in args[1:]]
        items = []
        for cid in ids:
            item = load(cid)
            if item:
                items.append(item)
            else:
                unknown.append(cid)
    else:
        items = preview_n(30)
    if unknown:
        print('Tidak ditemukan:', unknown)
    render(items)
    print(f'\nSiap {len(items)} konten untuk preview.')


if __name__ == '__main__':
    main()
