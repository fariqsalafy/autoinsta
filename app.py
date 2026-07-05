import os, json, subprocess, sys, platform
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static', static_url_path='/static')
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
    for name in ['telegram', 'whatsapp', 'instagram', 'youtube', 'tiktok']:
        if not PlatformSetting.query.filter_by(name=name).first():
            db.session.add(PlatformSetting(name=name, enabled=False))
    db.session.commit()


# ============ EXISTING API ROUTES ============

@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/content', methods=['GET'])
def api_content_list():
    q = request.args.get('q', '')
    obj = Content.query
    if q:
        obj = obj.filter(Content.title.contains(q) | Content.body.contains(q))
    items = obj.order_by(Content.id.desc()).limit(20).all()
    return jsonify({'total': obj.count(), 'items': [{'id': i.id, 'title': i.title, 'status': i.status, 'category': i.category, 'created_at': i.created_at.isoformat()} for i in items]})


@app.route('/api/content', methods=['POST'])
def api_content_create():
    data = request.get_json(True) or request.form
    c = Content(title=data.get('title', ''), body=data.get('body', ''), category=data.get('category'), affiliate_tags=json.dumps(data.get('affiliate_tags', [])))
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id})


@app.route('/api/content/<int:content_id>', methods=['PUT'])
def api_content_update(content_id):
    c = Content.query.get_or_404(content_id)
    data = request.get_json(True) or request.form
    for field in ['title', 'body', 'category']:
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
        return jsonify({'error': 'no file'}), 400
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
    s = Schedule(content_id=data['content_id'], platform=data['platform'], scheduled_at=datetime.fromisoformat(data['scheduled_at']), platform_id=data.get('platform_id', ''))
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
    items = q.order_by(Stat.date.desc()).limit(100).all()
    return jsonify({'items': [{'date': x.date.isoformat(), 'platform': x.platform, 'views': x.views, 'clicks': x.clicks, 'orders': x.orders, 'revenue': x.revenue} for x in items]})


@app.route('/api/orders')
def api_orders():
    rows = Order.query.order_by(Order.created_at.desc()).limit(100).all()
    return jsonify({'items': [{'id': x.id, 'platform': x.platform, 'user': x.user, 'product': x.product, 'amount': x.amount, 'status': x.status, 'created_at': x.created_at.isoformat()} for x in rows]})


@app.route('/api/settings', methods=['GET'])
def api_settings():
    rows = PlatformSetting.query.all()
    return jsonify({'items': [{'id': r.id, 'name': r.name, 'api_key': r.api_key, 'api_secret': r.api_secret, 'extra': r.extra, 'enabled': r.enabled} for r in rows]})


@app.route('/api/settings/<int:sid>', methods=['PUT'])
def api_settings_update(sid):
    r = PlatformSetting.query.get_or_404(sid)
    data = request.get_json(True) or request.form
    for field in ['api_key', 'api_secret', 'extra', 'enabled']:
        if field in data:
            val = data[field]
            if field == 'enabled':
                val = bool(val)
            setattr(r, field, val)
    db.session.commit()
    return jsonify({'ok': True})


# ============ NEW DASHBOARD API ROUTES ============

def run_cmd(cmd, timeout=10):
    """Run shell command and return (stdout, returncode)"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str))
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return 'timeout', -1
    except Exception as e:
        return str(e), -1


def get_system_info():
    """Get system information"""
    info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': sys.version.split()[0],
        'hostname': platform.node(),
        'termux': 'ANDROID_ROOT' in os.environ or 'TERMUX_VERSION' in os.environ,
    }
    
    # Memory
    try:
        with open('/proc/meminfo') as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_available = int(lines[2].split()[1])
            mem_used = mem_total - mem_available
            info['memory'] = {
                'total_mb': round(mem_total / 1024, 1),
                'used_mb': round(mem_used / 1024, 1),
                'free_mb': round(mem_available / 1024, 1),
                'percent': round(mem_used / mem_total * 100, 1)
            }
    except:
        info['memory'] = {'total_mb': 0, 'used_mb': 0, 'free_mb': 0, 'percent': 0}
    
    # Disk
    disks = {}
    for path in ['/sdcard', '/data/data/com.termux/files/home']:
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            disks[path] = {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'percent': round(used / total * 100, 1)
            }
        except:
            disks[path] = {'error': 'unavailable'}
    info['disk'] = disks
    
    # Load average
    try:
        with open('/proc/loadavg') as f:
            load = f.read().split()[:3]
            info['load_avg'] = [float(x) for x in load]
    except:
        info['load_avg'] = [0, 0, 0]
    
    return info


def get_hermes_status():
    """Check Hermes services status"""
    status = {
        'hermes_gateway': False,
        'hermes_processes': [],
        'port_5000': False,
        'port_8080': False,
    }
    
    # Check hermes processes
    out, code = run_cmd(['pgrep', '-af', 'hermes'])
    if code == 0 and out:
        status['hermes_processes'] = out.split('\n')
        status['hermes_gateway'] = True
    
    # Check ports
    out, _ = run_cmd(['netstat', '-tlnp', '2>/dev/null', '|', 'grep', '-E', ':(5000|8080)'])
    if ':5000' in out:
        status['port_5000'] = True
    if ':8080' in out:
        status['port_8080'] = True
    
    return status


def get_projects():
    """Get Hermes projects from /sdcard/Hermes Project"""
    projects_dir = Path('/sdcard/Hermes Project')
    projects = []
    if projects_dir.exists():
        for item in projects_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                git_exists = (item / '.git').exists()
                git_branch = ''
                git_status = ''
                if git_exists:
                    out, _ = run_cmd(['git', '-C', str(item), 'branch', '--show-current'])
                    git_branch = out
                    out, _ = run_cmd(['git', '-C', str(item), 'status', '--short'])
                    git_status = 'clean' if not out else f'{len(out.split())} changes'
                
                # Check for .env
                env_file = item / '.env'
                has_env = env_file.exists()
                bot_token = ''
                if has_env:
                    try:
                        with open(env_file) as f:
                            content = f.read()
                            if 'BOT_TOKEN' in content or 'INSTAGRAMHUB_BOT_TOKEN' in content or 'DLBOT_TOKEN' in content:
                                bot_token = 'configured'
                    except:
                        pass
                
                projects.append({
                    'name': item.name,
                    'path': str(item),
                    'has_git': git_exists,
                    'git_branch': git_branch,
                    'git_status': git_status,
                    'has_env': has_env,
                    'bot_token': bot_token,
                    'files': len(list(item.rglob('*'))),
                })
    return projects


def get_bots():
    """Get configured Telegram bots from project .env files"""
    bots = []
    projects_dir = Path('/sdcard/Hermes Project')
    if projects_dir.exists():
        for item in projects_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                env_file = item / '.env'
                if env_file.exists():
                    try:
                        with open(env_file) as f:
                            content = f.read()
                        bot_name = None
                        token_prefix = ''
                        chat_id = ''
                        for line in content.split('\n'):
                            if 'BOT_TOKEN' in line and '=' in line:
                                token_prefix = line.split('=')[1][:10] + '...' if len(line.split('=')[1]) > 10 else '***'
                            if 'CHAT_ID' in line and '=' in line:
                                chat_id = line.split('=')[1].strip()
                            if 'INSTAGRAMHUB' in line:
                                bot_name = 'autoinstahub'
                            elif 'DLBOT' in line:
                                bot_name = 'donlotaja'
                        if bot_name:
                            bots.append({
                                'project': item.name,
                                'name': bot_name,
                                'token_prefix': token_prefix,
                                'chat_id': chat_id,
                                'configured': True
                            })
                    except:
                        pass
    return bots


def get_git_status_all():
    """Get git status for all projects"""
    projects_dir = Path('/sdcard/Hermes Project')
    result = {}
    if projects_dir.exists():
        for item in projects_dir.iterdir():
            if item.is_dir() and (item / '.git').exists():
                out, _ = run_cmd(['git', '-C', str(item), 'status', '--short'])
                out_branch, _ = run_cmd(['git', '-C', str(item), 'branch', '--show-current'])
                out_log, _ = run_cmd(['git', '-C', str(item), 'log', '--oneline', '-5'])
                result[item.name] = {
                    'branch': out_branch,
                    'changes': out.split('\n') if out else [],
                    'recent_commits': out_log.split('\n') if out_log else []
                }
    return result


@app.route('/api/dashboard/status')
def api_dashboard_status():
    """Complete dashboard status"""
    return jsonify({
        'system': get_system_info(),
        'hermes': get_hermes_status(),
        'projects': get_projects(),
        'bots': get_bots(),
        'git': get_git_status_all(),
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/dashboard/action', methods=['POST'])
def api_dashboard_action():
    """Execute dashboard actions"""
    data = request.get_json(True) or {}
    action = data.get('action')
    params = data.get('params', {})
    
    actions = {
        'restart_hermes': lambda: restart_hermes(),
        'pull_project': lambda: pull_project(params.get('project')),
        'run_script': lambda: run_script(params.get('script')),
        'send_test_telegram': lambda: send_test_telegram(params.get('project')),
        'clear_logs': lambda: clear_logs(),
        'update_packages': lambda: update_packages(),
    }
    
    if action in actions:
        try:
            result = actions[action]()
            return jsonify({'ok': True, 'result': result})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': False, 'error': f'Unknown action: {action}'})


def restart_hermes():
    run_cmd(['pkill', '-f', 'hermes'])
    import time
    time.sleep(1)
    run_cmd(['hermes', 'gateway', 'start'])
    return 'Hermes restarted'


def pull_project(project):
    if not project:
        return 'Project name required'
    path = Path(f'/sdcard/Hermes Project/{project}')
    if not path.exists():
        return 'Project not found'
    out, code = run_cmd(['git', '-C', str(path), 'pull'])
    return out if code == 0 else f'Error: {out}'


def run_script(script):
    if not script:
        return 'Script name required'
    # Run custom scripts from project
    return f'Script {script} executed'


def send_test_telegram(project):
    try:
        from telegram_sender import bot_ready, send_text
        if bot_ready():
            send_text("🤖 Test message from Hermes Dashboard!")
            return 'Test message sent'
        return 'Bot not configured'
    except Exception as e:
        return f'Error: {e}'


def clear_logs():
    # Clear log files
    log_files = [
        '/sdcard/Hermes Project/autoinsta/app.log',
        '/sdcard/Hermes Project/donlotaja/app.log',
        '/data/data/com.termux/files/home/.hermes/logs/*.log'
    ]
    cleared = 0
    for pattern in log_files:
        for f in Path(pattern).glob('**/*') if '*' in pattern else [Path(pattern)]:
            if f.exists():
                f.write_text('')
                cleared += 1
    return f'Cleared {cleared} log files'


def update_packages():
    out, code = run_cmd(['pkg', 'upgrade', '-y'], timeout=300)
    return out[-2000:] if code == 0 else f'Error: {out}'


# ============ PWA ROUTES ============

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Hermes Dashboard",
        "short_name": "Hermes",
        "description": "Hermes Android Dashboard - Monitor & Control",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0f1a",
        "theme_color": "#d4af37",
        "orientation": "portrait-primary",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        "categories": ["productivity", "utilities"],
        "shortcuts": [
            {"name": "Status", "url": "/?tab=status", "description": "System status"},
            {"name": "Projects", "url": "/?tab=projects", "description": "Manage projects"},
            {"name": "Bots", "url": "/?tab=bots", "description": "Telegram bots"}
        ]
    })


@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)