import os, json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'media'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.secret_key = os.environ.get('APP_KEY', 'change-me-to-random')
db = SQLAlchemy(app)

class Content(db.Model):
    __tablename__ = 'content'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    media_path = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    affiliate_tags = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    platform_id = db.Column(db.String(255), nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='pending')
    posted_at = db.Column(db.DateTime, nullable=True)
    post_url = db.Column(db.String(500), nullable=True)

class PlatformSetting(db.Model):
    __tablename__ = 'platform_setting'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    api_key = db.Column(db.Text, nullable=True)
    api_secret = db.Column(db.Text, nullable=True)
    extra = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=False)

class Stat(db.Model):
    __tablename__ = 'stat'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    orders = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Float, default=0.0)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    platform_ref = db.Column(db.String(255), nullable=True)
    user = db.Column(db.String(255), nullable=True)
    product = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
with app.app_context():
    db.create_all()
    for name in ['telegram','whatsapp','instagram','youtube','tiktok']:
        if not PlatformSetting.query.filter_by(name=name).first():
            db.session.add(PlatformSetting(name=name, enabled=False))
    db.session.commit()

@app.route('/')
def index():
    return jsonify({'ok': True, 'admin': 'placeholder'})

@app.route('/api/content', methods=['GET'])
def api_content_list():
    q = request.args.get('q','')
    obj = Content.query
    if q:
        obj = obj.filter(Content.title.contains(q) | Content.body.contains(q))
    items = obj.order_by(Content.id.desc()).limit(20).all()
    return jsonify({'total': obj.count(), 'items': [{'id': i.id, 'title': i.title, 'status': i.status, 'category': i.category, 'created_at': i.created_at.isoformat()} for i in items]})

@app.route('/api/content', methods=['POST'])
def api_content_create():
    data = request.get_json(True) or request.form
    c = Content(title=data.get('title',''), body=data.get('body',''), category=data.get('category'), affiliate_tags=json.dumps(data.get('affiliate_tags',[])))
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id})

@app.route('/api/content/<int:content_id>', methods=['PUT'])
def api_content_update(content_id):
    c = Content.query.get_or_404(content_id)
    data = request.get_json(True) or request.form
    for field in ['title','body','category']:
        if field in data:
            setattr(c, field, data[field])
    if 'affiliate_tags' in data:
        c.affiliate_tags = json.dumps(data['affiliate_tags'])
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/content/<int:content_id>', methods=['DELETE'])
def api_content_delete(content_id):
    c = Content.query.get_or_404(content_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    f = request.files.get('file')
    if not f:
        return jsonify({'error':'no file'}), 400
    path = os.path.join(app.config['UPLOAD_FOLDER'], datetime.utcnow().strftime('%Y%m%d%H%M%S_') + os.path.basename(f.filename))
    f.save(path)
    return jsonify({'path': path})

@app.route('/api/schedule', methods=['GET'])
def api_schedule_list():
    rows = Schedule.query.order_by(Schedule.scheduled_at.desc()).limit(50).all()
    return jsonify({'items': [{'id': r.id, 'content_id': r.content_id, 'platform': r.platform, 'status': r.status, 'scheduled_at': r.scheduled_at.isoformat(), 'post_url': r.post_url} for r in rows]})

@app.route('/api/schedule', methods=['POST'])
def api_schedule_create():
    data = request.get_json(True) or request.form
    s = Schedule(content_id=data['content_id'], platform=data['platform'], scheduled_at=datetime.fromisoformat(data['scheduled_at']), platform_id=data.get('platform_id',''))
    db.session.add(s)
    db.session.commit()
    return jsonify({'id': s.id})

@app.route('/api/schedule/<int:sid>/cancel', methods=['POST'])
def api_schedule_cancel(sid):
    s = Schedule.query.get_or_404(sid)
    s.status = 'cancelled'
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/stats')
def api_stats():
    platform = request.args.get('platform')
    q = Stat.query
    if platform:
        q = q.filter_by(platform=platform)
    rows = q.order_by(Stat.date.desc()).limit(30).all()
    return jsonify({'items': [{'platform': r.platform, 'date': r.date.isoformat(), 'views': r.views, 'clicks': r.clicks, 'orders': r.orders, 'revenue': r.revenue} for r in rows]})

@app.route('/api/orders')
def api_orders():
    rows = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    return jsonify({'items': [{'id': r.id, 'platform': r.platform, 'user': r.user, 'product': r.product, 'amount': r.amount, 'status': r.status, 'created_at': r.created_at.isoformat()} for r in rows]})

@app.route('/api/settings', methods=['GET'])
def api_settings_get():
    rows = PlatformSetting.query.all()
    return jsonify({'items': [{'id': r.id, 'name': r.name, 'enabled': r.enabled, 'api_key': '***' if r.api_key else None, 'api_secret': '***' if r.api_secret else None} for r in rows]})

@app.route('/api/settings/<int:sid>', methods=['PUT'])
def api_settings_put(sid):
    s = PlatformSetting.query.get_or_404(sid)
    data = request.get_json(True) or request.form
    for field in ['api_key','api_secret','extra']:
        if field in data:
            setattr(s, field, data[field])
    if 'enabled' in data:
        s.enabled = bool(data['enabled'])
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/post/now', methods=['POST'])
def api_post_now():
    data = request.get_json(True) or request.form
    cid = int(data['content_id'])
    target = data['platform']
    c = Content.query.get_or_404(cid)
    media = c.media_path or ''
    body = c.body or ''
    title = c.title or ''
    tags = json.loads(c.affiliate_tags or '[]')
    with app.app_context():
        class _C:
            pass
        obj = _C()
        obj.title = c.title
        obj.body = c.body
        obj.media_path = c.media_path
        if target == 'telegram':
            from telegram_sender import send_media as send_tg
            res = send_tg(obj)
        elif target == 'instagram':
            if media.lower().endswith('.mp4'):
                from ig_publisher import publish_reel
                res = publish_reel(media, caption=body, tags=tags)
            else:
                from ig_publisher import publish_carousel
                res = publish_carousel([media], caption=body, tags=tags)
        elif target == 'youtube':
            if media.lower().endswith('.mp4'):
                from yt_publisher import upload_shorts
                res = upload_shorts(media, title=title, description=body, tags=tags)
            else:
                res = {'ok': False, 'error': 'YT needs mp4'}
        else:
            res = {'ok': False, 'error': 'unsupported'}
    if res.get('ok'):
        s = Schedule(content_id=cid, platform=target, scheduled_at=datetime.utcnow(), status='posted', posted_at=datetime.utcnow(), post_url=res.get('url') or res.get('permalink_url',''))
        db.session.add(s)
        c.status = 'published'
        db.session.commit()
    return jsonify(res)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
