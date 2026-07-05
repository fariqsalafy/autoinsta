#!/usr/bin/env python3
from telegram_sender import bot_ready, send_rich_preview
from app import app, db, Content
from datetime import datetime
import sys

def usage():
    print('Usage: python instagramhub.py [ready|send-telegram|generate]')
    sys.exit(1)

cmd = sys.argv[1] if len(sys.argv) > 1 else 'ready'
with app.app_context():
    db.create_all()
    if cmd == 'ready':
        for it in Content.query.filter_by(status='ready').order_by(Content.id.desc()).all():
            print(f"{it.id} {it.title}")
    elif cmd == 'generate':
        for it in Content.query.filter_by(status='draft').order_by(Content.id.desc()).limit(3).all():
            it.status = 'ready'
            it.updated_at = datetime.utcnow()
            print(f"ready {it.id} {it.title}")
        db.session.commit()
    elif cmd == 'send-telegram':
        for it in Content.query.order_by(Content.id.desc()).limit(3).all():
            item = {
                'title': it.title,
                'body': it.body,
                'media_path': it.media_path or '',
                'affiliate_tags': it.affiliate_tags or '[]',
            }
            print('sent', it.id, bool(send_rich_preview(item)))
    else:
        usage()
