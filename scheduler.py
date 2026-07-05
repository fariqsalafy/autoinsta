import os, json, time, threading
from datetime import datetime
from app import app, db
from ig_publisher import publish_reel, publish_carousel
from yt_publisher import upload_shorts
from telegram_sender import send_media


def _run_jobs():
    with app.app_context():
        while True:
            try:
                rows = (
                    Schedule.query.filter(Schedule.status == 'pending')
                    .filter(Schedule.scheduled_at <= datetime.utcnow())
                    .all()
                )
                for job in rows:
                    content = Content.query.get(job.content_id)
                    if not content:
                        job.status = 'failed'
                        db.session.commit()
                        continue

                    media = content.media_path or ''
                    body = content.body or ''
                    tags = json.loads(content.affiliate_tags or '[]')
                    try:
                        if job.platform == 'telegram':
                            res = send_media(content)
                        elif job.platform == 'instagram':
                            if media.lower().endswith('.mp4'):
                                res = publish_reel(media, caption=body, tags=tags)
                            else:
                                res = publish_carousel([media], caption=body, tags=tags)
                        elif job.platform == 'youtube':
                            if media.lower().endswith('.mp4'):
                                res = upload_shorts(media, title=content.title or '', description=body, tags=tags)
                            else:
                                res = {'ok': False, 'error': 'YT needs mp4'}
                        else:
                            res = {'ok': False, 'error': 'unsupported platform'}

                        if res.get('ok'):
                            job.status = 'posted'
                            job.posted_at = datetime.utcnow()
                            job.post_url = res.get('url') or res.get('permalink_url') or ''
                            content.status = 'published'
                        else:
                            job.status = 'failed'
                    except Exception as exc:
                        job.status = 'failed'
                    finally:
                        db.session.commit()
            except Exception:
                pass
            time.sleep(30 * 60)


def start_background():
    t = threading.Thread(target=_run_jobs, daemon=True)
    t.start()
    return t
