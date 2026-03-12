

import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, g, request, redirect, url_for,
                   session, flash, render_template_string)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
import os
app.secret_key = 'gympro_secret_key_2024'
DB_PATH = os.environ.get('DB_PATH', '/tmp/gym.db')

PLANS = {
    'basic':    {'name': 'Базовый',  'price': 2500,
                 'features': ['Тренажёрный зал', '2 групповых занятия/мес', 'Раздевалки']},
    'standard': {'name': 'Стандарт', 'price': 4500,
                 'features': ['Тренажёрный зал', 'Безлимитные занятия', 'Бассейн', '1 персональная/мес']},
    'premium':  {'name': 'Премиум',  'price': 7500,
                 'features': ['Всё из Стандарт', '4 персональных/мес', 'Сауна', 'Приоритет записи']},
}
DAYS  = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
TYPES = ['Силовая', 'Кардио', 'Йога', 'HIIT', 'Пилатес', 'Растяжка', 'Бокс', 'Персональная']



def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'client',
            phone      TEXT DEFAULT '',
            birth_date TEXT DEFAULT '',
            height     TEXT DEFAULT '',
            weight     TEXT DEFAULT '',
            goal       TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS workouts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            trainer_id  INTEGER,
            type        TEXT NOT NULL,
            day         TEXT NOT NULL,
            time        TEXT NOT NULL,
            duration    TEXT NOT NULL,
            room        TEXT DEFAULT '',
            max_spots   INTEGER DEFAULT 20,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (trainer_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            workout_id  INTEGER NOT NULL,
            enrolled_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, workout_id),
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (workout_id) REFERENCES workouts(id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER UNIQUE NOT NULL,
            plan       TEXT NOT NULL,
            status     TEXT DEFAULT 'active',
            start_date TEXT,
            end_date   TEXT,
            frozen_at  TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    existing = c.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if not existing:
        c.execute(
            "INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,'admin',?)",
            ('Администратор', 'admin@gym.ru',
             generate_password_hash('admin123'), '+7(000)000-00-00')
        )
        print("Создан администратор: admin@gym.ru / admin123")
    conn.commit()
    conn.close()


init_db()

def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    return cur.fetchone() if one else cur.fetchall()

def run(sql, args=()):
    db = get_db()
    db.execute(sql, args)
    db.commit()


def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return wrap

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrap(*a, **kw):
            if session.get('role') not in roles:
                return redirect(url_for('login'))
            return f(*a, **kw)
        return wrap
    return decorator



CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0b0b;--sf:#111;--card:#171717;--brd:#252525;--brd2:#2e2e2e;--tx:#ebebeb;--mt:#7a7a7a;--dm:#333;--ac:#c0392b;--acl:#e74c3c;--acd:#c0392b18;--gr:#27ae60;--grd:#27ae6018;--yw:#d4a017;--ywd:#d4a01718;--bl:#2980b9;--bld:#2980b918;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;background:var(--bg);color:var(--tx);font-family:'IBM Plex Sans',sans-serif;font-size:14px;-webkit-font-smoothing:antialiased;}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:var(--sf)}::-webkit-scrollbar-thumb{background:var(--brd2)}
a{color:inherit;text-decoration:none;}
button,input,select,textarea{font-family:inherit;font-size:14px;}
input,select,textarea{background:var(--sf);color:var(--tx);border:1px solid var(--brd);padding:10px 14px;border-radius:3px;outline:none;transition:border-color .15s;width:100%;}
input:focus,select:focus,textarea:focus{border-color:var(--ac);}
input::placeholder,textarea::placeholder{color:var(--dm);}
select option{background:var(--card);}
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:11px 16px;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--mt);border-bottom:1px solid var(--brd);}
td{padding:13px 16px;border-bottom:1px solid var(--brd);vertical-align:middle;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:#ffffff04;}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.fade{animation:fadeUp .25s ease forwards;}
.layout{display:flex;min-height:100vh;}
.sidebar{width:230px;background:var(--sf);border-right:1px solid var(--brd);padding:20px 10px;display:flex;flex-direction:column;flex-shrink:0;position:fixed;top:0;left:0;height:100vh;overflow-y:auto;z-index:200;transition:transform .25s cubic-bezier(.4,0,.2,1);}.sidebar.sb-off{transform:translateX(-100%);}.sb-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:199;}.sb-overlay.on{display:block;}
.logo{display:flex;align-items:center;gap:10px;padding:4px 10px 24px;}
.logo-box{width:34px;height:34px;background:var(--ac);border-radius:3px;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:12px;color:#fff;flex-shrink:0;}
.logo-txt{font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:15px;letter-spacing:1px;}
.nav-sec{padding:0 10px;font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--dm);margin:18px 0 8px;}
.nav-a{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:3px;color:var(--mt);font-size:14px;font-weight:500;transition:all .15s;cursor:pointer;}
.nav-a:hover{background:#ffffff06;color:var(--tx);}
.nav-a.on{background:var(--acd);color:var(--acl);}
.nav-ico{width:15px;text-align:center;font-size:12px;}
.sb-bot{margin-top:auto;padding-top:16px;border-top:1px solid var(--brd);}
.main{flex:1;overflow-y:auto;min-width:0;transition:margin-left .25s cubic-bezier(.4,0,.2,1);}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:18px 28px;border-bottom:1px solid var(--brd);background:var(--sf);position:sticky;top:0;z-index:10;}
.tb-title{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;letter-spacing:.5px;}
.tb-user{display:flex;align-items:center;gap:9px;font-size:13px;color:var(--mt);}
.avatar{width:30px;height:30px;background:var(--acd);border:1px solid #c0392b30;border-radius:3px;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;color:var(--acl);}
.content{padding:28px;}
.ph{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;}
.ptitle{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:700;letter-spacing:-.5px;}
.psub{color:var(--mt);font-size:13px;margin-top:5px;}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:9px 17px;border-radius:3px;font-size:13px;font-weight:600;border:none;transition:all .15s;white-space:nowrap;cursor:pointer;}
.bp{background:var(--ac);color:#fff;}.bp:hover{background:var(--acl);}
.bo{background:transparent;color:var(--mt);border:1px solid var(--brd);}.bo:hover{border-color:var(--mt);color:var(--tx);}
.bg{background:transparent;color:var(--mt);border:none;padding:8px 13px;}.bg:hover{color:var(--tx);background:#ffffff06;}
.bd{background:transparent;color:var(--acl);border:1px solid var(--acd);}.bd:hover{background:var(--acd);}
.bs{background:var(--grd);color:var(--gr);border:1px solid #27ae6028;}.bs:hover{background:#27ae6022;}
.btn-sm{padding:6px 12px;font-size:12px;}
.btn:disabled{opacity:.35;cursor:not-allowed;pointer-events:none;}
.card{background:var(--card);border:1px solid var(--brd);border-radius:5px;padding:22px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;}
.g4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:14px;}
.sc{background:var(--card);border:1px solid var(--brd);border-radius:5px;padding:18px 22px;}
.slbl{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--mt);margin-bottom:9px;}
.sval{font-family:'IBM Plex Mono',monospace;font-size:30px;font-weight:700;letter-spacing:-1px;line-height:1;}
.ssub{font-size:12px;color:var(--mt);margin-top:5px;}
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:3px;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;}
.bgr{background:var(--grd);color:var(--gr);}
.bre{background:var(--acd);color:var(--acl);}
.bbl{background:var(--bld);color:var(--bl);}
.byw{background:var(--ywd);color:var(--yw);}
.bdm{background:#ffffff0a;color:var(--mt);}
.divider{height:1px;background:var(--brd);margin:20px 0;}
.fg{display:flex;flex-direction:column;gap:5px;margin-bottom:15px;}
.fl{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--mt);}
.ferr{font-size:12px;color:var(--acl);margin-top:3px;}
.fhint{font-size:12px;color:var(--mt);margin-top:3px;}
.tw{background:var(--card);border:1px solid var(--brd);border-radius:5px;overflow:hidden;}
.stitle{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:700;letter-spacing:.5px;color:var(--tx);margin-bottom:14px;}
.flash-w{padding:0 28px;margin-top:14px;}
.flash{padding:11px 16px;border-radius:3px;font-size:14px;margin-bottom:8px;}
.f-ok{background:var(--grd);color:var(--gr);border:1px solid #27ae6028;}
.f-err{background:var(--acd);color:var(--acl);border:1px solid #c0392b28;}
.progress{height:4px;background:var(--brd);border-radius:2px;overflow:hidden;margin-top:6px;}
.pf{height:100%;border-radius:2px;}
.empty{text-align:center;padding:50px 20px;color:var(--mt);}
.etxt{font-family:'IBM Plex Mono',monospace;font-size:13px;letter-spacing:.5px;}
.mono{font-family:'IBM Plex Mono',monospace;}
.fb{display:flex;align-items:center;gap:9px;margin-bottom:18px;}
.fb input{max-width:260px;}
.sec-lbl{font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--dm);padding-bottom:10px;border-bottom:1px solid var(--brd);margin-bottom:15px;}
.err-box{background:#1a0808;border:1px solid #c0392b28;color:var(--acl);padding:10px 14px;border-radius:3px;font-size:13px;margin-bottom:18px;}
@media(max-width:720px){
  .g2{grid-template-columns:1fr!important;}
  .g3{grid-template-columns:1fr!important;}
  .g4{grid-template-columns:1fr 1fr!important;}
  .content{padding:14px!important;}
  .topbar{padding:12px 14px!important;}
  .ptitle{font-size:17px!important;}
  .sval{font-size:24px!important;}
  td{padding:10px 12px!important;}
  th{padding:9px 12px!important;}
}
</style>
"""

def base_layout(content, page_title="", topbar_title=""):
    role = session.get('role','')
    name = session.get('name','')
    email= session.get('email','')
    av   = (name[:2].upper()) if name else 'U'

    # nav items per role
    if role == 'admin':
        nav = f"""
        <span class="nav-sec">Управление</span>
        <a href="/admin" class="nav-a {'on' if request.path=='/admin' else ''}"><span class="nav-ico">▣</span>Дашборд</a>
        <a href="/admin/users" class="nav-a {'on' if '/admin/users' in request.path else ''}"><span class="nav-ico">◈</span>Пользователи</a>
        <a href="/admin/workouts" class="nav-a {'on' if '/admin/workouts' in request.path else ''}"><span class="nav-ico">◉</span>Тренировки</a>
        <a href="/admin/subs" class="nav-a {'on' if '/admin/subs' in request.path else ''}"><span class="nav-ico">◎</span>Абонементы</a>
        """
    elif role == 'trainer':
        nav = f"""
        <span class="nav-sec">Тренер</span>
        <a href="/trainer" class="nav-a {'on' if request.path=='/trainer' else ''}"><span class="nav-ico">▣</span>Мои занятия</a>
        """
    else:
        nav = f"""
        <span class="nav-sec">Кабинет</span>
        <a href="/cabinet" class="nav-a {'on' if request.path=='/cabinet' else ''}"><span class="nav-ico">▣</span>Главная</a>
        <a href="/cabinet/schedule" class="nav-a {'on' if '/schedule' in request.path else ''}"><span class="nav-ico">◉</span>Расписание</a>
        <a href="/cabinet/my-workouts" class="nav-a {'on' if '/my-workouts' in request.path else ''}"><span class="nav-ico">◈</span>Мои записи</a>
        <a href="/cabinet/subscription" class="nav-a {'on' if '/subscription' in request.path else ''}"><span class="nav-ico">◎</span>Абонемент</a>
        <a href="/cabinet/profile" class="nav-a {'on' if '/profile' in request.path else ''}"><span class="nav-ico">○</span>Профиль</a>
        """

    flashes = ''
    for cat, msg in session.pop('_flashes', []) if False else []:
        pass
    # use get_flashed_messages via jinja - we'll handle differently
    flash_html = '{% with msgs=get_flashed_messages(with_categories=true) %}{% if msgs %}<div class="flash-w">{% for cat,msg in msgs %}<div class="flash {{ "f-ok" if cat=="success" else "f-err" }}">{{msg}}</div>{% endfor %}</div>{% endif %}{% endwith %}'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title} — GymPro</title>{CSS}</head>
<body>
<div class="layout">
<aside class="sidebar">
  <div class="logo"><div class="logo-box">GP</div><div class="logo-txt">GYMPRO</div></div>
  {nav}
  <div class="sb-bot">
    <div style="padding:0 10px;margin-bottom:10px;">
      <div style="font-size:13px;font-weight:600;">{name}</div>
      <div style="font-size:12px;color:var(--mt);margin-top:2px;">{role}</div>
    </div>
    <a href="/logout" class="nav-a"><span class="nav-ico">→</span>Выйти</a>
  </div>
</aside>
<div class="main">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:12px;"><button id="sb-btn" onclick="sbToggle()" style="background:none;border:none;cursor:pointer;padding:4px 6px;display:flex;flex-direction:column;gap:4px;flex-shrink:0;"><span style="display:block;width:18px;height:2px;background:var(--mt);border-radius:2px;"></span><span style="display:block;width:18px;height:2px;background:var(--mt);border-radius:2px;"></span><span style="display:block;width:13px;height:2px;background:var(--mt);border-radius:2px;"></span></button><span class="tb-title">{topbar_title}</span></div>
    <div class="tb-user"><div class="avatar">{av}</div></div>
  </div>
  {flash_html}
  <div class="content fade">{content}</div>
</div>
</div>
<div class="sb-overlay" id="sb-ov" onclick="sbClose()"></div>
<script>
var _sbOpen = true;
function sbToggle() {{
  var sb = document.querySelector('.sidebar');
  var ov = document.getElementById('sb-ov');
  var mn = document.querySelector('.main');
  if (_sbOpen) {{
    sb.classList.add('sb-off');
    ov.classList.remove('on');
    mn.style.marginLeft = '0';
    _sbOpen = false;
  }} else {{
    sb.classList.remove('sb-off');
    mn.style.marginLeft = '';
    if (window.innerWidth <= 720) ov.classList.add('on');
    _sbOpen = true;
  }}
}}
function sbClose() {{
  var sb = document.querySelector('.sidebar');
  var ov = document.getElementById('sb-ov');
  sb.classList.add('sb-off');
  ov.classList.remove('on');
  document.querySelector('.main').style.marginLeft = '0';
  _sbOpen = false;
}}
if (window.innerWidth <= 720) {{
  document.querySelector('.sidebar').classList.add('sb-off');
  document.querySelector('.main').style.marginLeft = '0';
  _sbOpen = false;
}}
</script>
</body></html>"""

def render(content, page_title="", topbar_title=""):
    return render_template_string(base_layout(content, page_title, topbar_title))


LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Вход — GymPro</title>""" + CSS + """
<style>
body{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;}
.wrap{width:370px;max-width:100%;}
.llogo{text-align:center;margin-bottom:36px;}
.lbox{width:46px;height:46px;background:var(--ac);border-radius:3px;display:inline-flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:15px;color:#fff;margin-bottom:14px;}
h1{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:700;letter-spacing:2px;}
p{color:var(--mt);font-size:13px;margin-top:5px;}
.box{background:var(--sf);border:1px solid var(--brd);border-radius:5px;padding:28px;}
.fl{display:block;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--mt);margin-bottom:5px;}
.fg{margin-bottom:14px;}
.sbtn{display:block;width:100%;padding:12px;background:var(--ac);color:#fff;border:none;border-radius:3px;font-size:14px;font-weight:600;cursor:pointer;transition:background .15s;margin-top:6px;}
.sbtn:hover{background:var(--acl);}
.err{background:#1a0808;border:1px solid #c0392b28;color:var(--acl);padding:10px 14px;border-radius:3px;font-size:13px;margin-bottom:14px;}
.hint{background:#0e0e0e;border:1px solid #1e1e1e;border-radius:3px;padding:12px;margin-top:18px;}
.ht{font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--dm);margin-bottom:9px;}
.hr{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a1a1a;font-size:12px;}
.hr:last-child{border-bottom:none;}
.link{color:var(--ac);font-size:13px;}
.link:hover{color:var(--acl);}
</style></head>
<body>
<div class="wrap">
  <div class="llogo">
    <div class="lbox">GP</div>
    <h1>GYMPRO</h1>
    <p>Система управления спортзалом</p>
  </div>
  <div class="box">
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <form method="POST">
      <div class="fg"><label class="fl">Email</label><input type="email" name="email" placeholder="your@email.ru" required autofocus></div>
      <div class="fg"><label class="fl">Пароль</label><input type="password" name="password" placeholder="••••••••" required></div>
      <button type="submit" class="sbtn">Войти</button>
    </form>
    <div style="text-align:center;margin-top:18px;font-size:13px;color:var(--mt);">
      Нет аккаунта? <a href="/register" class="link">Зарегистрироваться</a>
    </div>
  </div>

</div>
</body></html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Регистрация — GymPro</title>""" + CSS + """
<style>
body{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:30px 16px;}
.wrap{width:460px;max-width:100%;}
.lhdr{display:flex;align-items:center;gap:10px;margin-bottom:28px;}
.lbox{width:34px;height:34px;background:var(--ac);border-radius:3px;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:12px;color:#fff;}
h1{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;letter-spacing:1.5px;}
.box{background:var(--sf);border:1px solid var(--brd);border-radius:5px;padding:28px;}
.btitle{font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:700;margin-bottom:4px;}
.bsub{color:var(--mt);font-size:13px;margin-bottom:22px;}
.fl{display:block;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--mt);margin-bottom:5px;}
.fg{margin-bottom:0;}
.sec{font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--dm);padding-bottom:9px;border-bottom:1px solid var(--brd);margin:18px 0 14px;}
.sbtn{display:block;width:100%;padding:12px;background:var(--ac);color:#fff;border:none;border-radius:3px;font-size:14px;font-weight:600;cursor:pointer;transition:background .15s;margin-top:20px;}
.sbtn:hover{background:var(--acl);}
.err{background:#1a0808;border:1px solid #c0392b28;color:var(--acl);padding:10px 14px;border-radius:3px;font-size:13px;margin-bottom:16px;}
.link{color:var(--ac);font-size:13px;}.link:hover{color:var(--acl);}
</style></head>
<body>
<div class="wrap">
  <div class="lhdr"><div class="lbox">GP</div><h1>GYMPRO</h1></div>
  <div class="box">
    <div class="btitle">Регистрация</div>
    <div class="bsub">Создайте аккаунт клиента</div>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <form method="POST">
      <div class="sec">Основные данные</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Имя и фамилия *</label><input type="text" name="name" required placeholder="Иван Петров"></div>
        <div class="fg"><label class="fl">Телефон</label><input type="tel" name="phone" placeholder="+7 (999) 000-00-00"></div>
      </div>
      <div style="margin-bottom:13px;"><label class="fl">Email *</label><input type="email" name="email" required placeholder="ivan@mail.ru"></div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Пароль *</label><input type="password" name="password" required placeholder="Минимум 6 символов"></div>
        <div class="fg"><label class="fl">Повторите пароль *</label><input type="password" name="password2" required placeholder="Повторите пароль"></div>
      </div>
      <div style="margin-bottom:0;"><label class="fl">Дата рождения</label><input type="date" name="birth_date"></div>
      <div class="sec">Параметры (необязательно)</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Рост (см)</label><input type="number" name="height" placeholder="175"></div>
        <div class="fg"><label class="fl">Вес (кг)</label><input type="number" name="weight" placeholder="70"></div>
      </div>
      <div><label class="fl">Цель тренировок</label><input type="text" name="goal" placeholder="Похудение, набор массы..."></div>
      <button type="submit" class="sbtn">Создать аккаунт</button>
    </form>
    <div style="text-align:center;margin-top:16px;font-size:13px;color:var(--mt);">
      Уже есть аккаунт? <a href="/login" class="link">Войти</a>
    </div>
  </div>
</div>
</body></html>"""

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role','client')
        return redirect(url_for({'admin':'admin_dash','trainer':'trainer_dash'}.get(role,'cabinet_dash')))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        u = q("SELECT * FROM users WHERE email=?", (request.form['email'].lower(),), one=True)
        if u and check_password_hash(u['password'], request.form['password']):
            session['user_id'] = u['id']
            session['name']    = u['name']
            session['role']    = u['role']
            session['email']   = u['email']
            return redirect(url_for('index'))
        error = 'Неверный email или пароль'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        name      = request.form.get('name','').strip()
        email     = request.form.get('email','').strip().lower()
        pwd       = request.form.get('password','')
        pwd2      = request.form.get('password2','')
        phone     = request.form.get('phone','')
        bd        = request.form.get('birth_date','')
        height    = request.form.get('height','')
        weight    = request.form.get('weight','')
        goal      = request.form.get('goal','')
        if not name or not email or not pwd:
            error = 'Заполните все обязательные поля'
        elif pwd != pwd2:
            error = 'Пароли не совпадают'
        elif len(pwd) < 6:
            error = 'Пароль минимум 6 символов'
        else:
            existing = q("SELECT id FROM users WHERE email=?", (email,), one=True)
            if existing:
                error = 'Пользователь с таким email уже существует'
            else:
                run("INSERT INTO users (name,email,password,role,phone,birth_date,height,weight,goal) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, email, generate_password_hash(pwd), 'client', phone, bd, height, weight, goal))
                u = q("SELECT * FROM users WHERE email=?", (email,), one=True)
                session['user_id'] = u['id']
                session['name']    = u['name']
                session['role']    = 'client'
                session['email']   = u['email']
                flash('Добро пожаловать! Аккаунт создан.', 'success')
                return redirect(url_for('cabinet_dash'))
    return render_template_string(REGISTER_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
@role_required('admin')
def admin_dash():
    users    = q("SELECT role FROM users")
    workouts = q("SELECT id FROM workouts")
    subs     = q("SELECT plan,status FROM subscriptions")
    revenue  = sum(PLANS[s['plan']]['price'] for s in subs if s['status']=='active' and s['plan'] in PLANS)
    stats = {
        'u': len(users), 'cl': sum(1 for u in users if u['role']=='client'),
        'tr': sum(1 for u in users if u['role']=='trainer'),
        'w': len(workouts), 'as': sum(1 for s in subs if s['status']=='active'),
        'rev': revenue
    }
    ru = q("SELECT * FROM users ORDER BY created_at DESC LIMIT 5")
    rw = q("""SELECT w.*,u.name as tname,
              (SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
              FROM workouts w LEFT JOIN users u ON w.trainer_id=u.id
              ORDER BY w.created_at DESC LIMIT 5""")
    c = f"""
    <div class="ph"><div><div class="ptitle">Обзор системы</div><div class="psub">Актуальная статистика</div></div></div>
    <div class="g4" style="margin-bottom:22px;">
      <div class="sc"><div class="slbl">Пользователей</div><div class="sval">{stats['u']}</div><div class="ssub">{stats['cl']} клиентов, {stats['tr']} тренеров</div></div>
      <div class="sc"><div class="slbl">Тренировок</div><div class="sval">{stats['w']}</div><div class="ssub">в расписании</div></div>
      <div class="sc"><div class="slbl">Активных абон.</div><div class="sval">{stats['as']}</div></div>
      <div class="sc"><div class="slbl">Выручка/мес</div><div class="sval" style="font-size:22px;">{stats['rev']:,} ₽</div></div>
    </div>
    <div class="g2">
      <div>
        <div class="stitle">Последние пользователи</div>
        <div class="tw" style="margin-top:12px;">
          <table><thead><tr><th>Пользователь</th><th>Роль</th><th>Дата</th></tr></thead><tbody>
    """
    for u in ru:
        role_b = {'admin':'<span class="badge bre">Админ</span>','trainer':'<span class="badge bbl">Тренер</span>'}.get(u['role'],'<span class="badge bdm">Клиент</span>')
        c += f"<tr><td><div style='font-weight:600'><a href='/admin/users/{u['id']}'>{u['name']}</a></div><div style='font-size:12px;color:var(--mt)'>{u['email']}</div></td><td>{role_b}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{u['created_at'][:10]}</td></tr>"
    if not ru:
        c += "<tr><td colspan='3'><div class='empty'><div class='etxt'>Нет пользователей</div></div></td></tr>"
    c += f"</tbody></table></div><div style='margin-top:12px'><a href='/admin/users' class='btn bo btn-sm'>Все пользователи</a></div></div>"
    c += "<div><div class='stitle'>Последние тренировки</div><div class='tw' style='margin-top:12px'><table><thead><tr><th>Название</th><th>День</th><th>Мест</th></tr></thead><tbody>"
    for w in rw:
        pct = int(w['enrolled']/w['max_spots']*100) if w['max_spots'] else 0
        clr = 'var(--ac)' if w['enrolled']>=w['max_spots'] else 'var(--gr)'
        c += f"<tr><td><div style='font-weight:600'><a href='/admin/workouts/{w['id']}'>{w['name']}</a></div><div style='font-size:12px;color:var(--mt)'>{w['tname'] or '—'}</div></td><td style='color:var(--mt)'>{w['day']}</td><td><span class='mono' style='font-size:13px'>{w['enrolled']}/{w['max_spots']}</span><div class='progress' style='width:70px'><div class='pf' style='width:{pct}%;background:{clr}'></div></div></td></tr>"
    if not rw:
        c += "<tr><td colspan='3'><div class='empty'><div class='etxt'>Нет тренировок</div></div></td></tr>"
    c += "</tbody></table></div><div style='margin-top:12px'><a href='/admin/workouts' class='btn bo btn-sm'>Все тренировки</a></div></div></div>"
    return render(c, "Дашборд", "Дашборд")

@app.route('/admin/users')
@role_required('admin')
def admin_users():
    rf = request.args.get('role','all')
    sq = request.args.get('q','').lower()
    users = q("SELECT * FROM users ORDER BY created_at DESC")
    if rf != 'all': users = [u for u in users if u['role']==rf]
    if sq: users = [u for u in users if sq in u['name'].lower() or sq in u['email'].lower()]
    reset = f"<a href='/admin/users' class='btn bg btn-sm'>Сбросить</a>" if sq or rf!='all' else ""
    rows = ""
    for u in users:
        rb = {'admin':'<span class="badge bre">Администратор</span>','trainer':'<span class="badge bbl">Тренер</span>'}.get(u['role'],'<span class="badge bdm">Клиент</span>')
        del_btn = f"<form method='POST' action='/admin/users/{u['id']}/delete' onsubmit=\"return confirm('Удалить {u['name']}?')\"><button class='btn bd btn-sm'>Удалить</button></form>" if u['id']!=session['user_id'] else ""
        rows += f"<tr><td><div style='font-weight:600'>{u['name']}</div><div style='font-size:12px;color:var(--mt);font-family:monospace'>{u['email']}</div></td><td>{rb}</td><td style='color:var(--mt)'>{u['phone'] or '—'}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{u['created_at'][:10]}</td><td><div style='display:flex;gap:6px'><a href='/admin/users/{u['id']}' class='btn bg btn-sm'>Подробнее</a>{del_btn}</div></td></tr>"
    if not rows:
        rows = "<tr><td colspan='5'><div class='empty'><div class='etxt'>Пользователи не найдены</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Пользователи</div><div class="psub">{len(users)} записей</div></div><a href="/admin/users/create" class="btn bp">+ Добавить</a></div>
    <div class="fb">
      <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <input name="q" value="{sq}" placeholder="Поиск..." style="max-width:240px;">
        <select name="role" style="width:auto;" onchange="this.form.submit()">
          <option value="all" {"selected" if rf=="all" else ""}>Все роли</option>
          <option value="client" {"selected" if rf=="client" else ""}>Клиенты</option>
          <option value="trainer" {"selected" if rf=="trainer" else ""}>Тренеры</option>
          <option value="admin" {"selected" if rf=="admin" else ""}>Администраторы</option>
        </select>
        <button type="submit" class="btn bo btn-sm">Найти</button>
        {reset}
      </form>
    </div>
    <div class="tw"><table><thead><tr><th>Пользователь</th><th>Роль</th><th>Телефон</th><th>Зарегистрирован</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Пользователи", "Пользователи")

@app.route('/admin/users/create', methods=['GET','POST'])
@role_required('admin')
def admin_create_user():
    error = None
    if request.method == 'POST':
        name  = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        pwd   = request.form.get('password','')
        role  = request.form.get('role','client')
        if not name or not email or not pwd:
            error = 'Заполните все обязательные поля'
        elif len(pwd) < 6:
            error = 'Пароль минимум 6 символов'
        else:
            ex = q("SELECT id FROM users WHERE email=?", (email,), one=True)
            if ex:
                error = 'Пользователь с таким email уже существует'
            else:
                run("INSERT INTO users (name,email,password,role,phone,birth_date,height,weight,goal) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, email, generate_password_hash(pwd), role,
                     request.form.get('phone',''), request.form.get('birth_date',''),
                     request.form.get('height',''), request.form.get('weight',''), request.form.get('goal','')))
                flash(f'Пользователь {name} создан', 'success')
                return redirect(url_for('admin_users'))
    err_html = f"<div class='err-box'>{error}</div>" if error else ""
    c = f"""
    <div class="ph"><div><div class="ptitle">Новый пользователь</div><div class="psub">Создание любой роли, включая администраторов</div></div><a href="/admin/users" class="btn bo">Назад</a></div>
    <div style="max-width:540px;"><div class="card">
    {err_html}
    <form method="POST">
      <div class="sec-lbl">Основные данные</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Имя и фамилия *</label><input type="text" name="name" required placeholder="Иван Петров"></div>
        <div class="fg"><label class="fl">Роль *</label><select name="role"><option value="client">Клиент</option><option value="trainer">Тренер</option><option value="admin">Администратор</option></select></div>
      </div>
      <div style="margin-bottom:13px;"><label class="fl">Email *</label><input type="email" name="email" required placeholder="user@email.ru"></div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Пароль *</label><input type="password" name="password" required placeholder="Минимум 6 символов"></div>
        <div class="fg"><label class="fl">Телефон</label><input type="tel" name="phone" placeholder="+7(999)000-00-00"></div>
      </div>
      <div style="margin-bottom:13px;"><label class="fl">Дата рождения</label><input type="date" name="birth_date"></div>
      <div class="sec-lbl" style="margin-top:18px;">Физические параметры</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Рост (см)</label><input type="number" name="height" placeholder="175"></div>
        <div class="fg"><label class="fl">Вес (кг)</label><input type="number" name="weight" placeholder="70"></div>
      </div>
      <div style="margin-bottom:0;"><label class="fl">Цель тренировок</label><input type="text" name="goal" placeholder="Похудение, набор массы..."></div>
      <div class="divider"></div>
      <div style="display:flex;gap:9px;"><button type="submit" class="btn bp">Создать пользователя</button><a href="/admin/users" class="btn bg">Отмена</a></div>
    </form>
    </div></div>"""
    return render(c, "Создать пользователя", "Создать пользователя")

@app.route('/admin/users/<int:uid>')
@role_required('admin')
def admin_user_detail(uid):
    u   = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not u: flash('Не найден','error'); return redirect(url_for('admin_users'))
    sub = q("SELECT * FROM subscriptions WHERE user_id=?", (uid,), one=True)
    enr = q("""SELECT w.*,u2.name as tname FROM enrollments en
               JOIN workouts w ON en.workout_id=w.id
               LEFT JOIN users u2 ON w.trainer_id=u2.id
               WHERE en.user_id=?""", (uid,))
    rb = {'admin':'<span class="badge bre">Администратор</span>','trainer':'<span class="badge bbl">Тренер</span>'}.get(u['role'],'<span class="badge bdm">Клиент</span>')
    rows_info = ""
    for lbl, val in [('Роль', rb),('Телефон', u['phone'] or '—'),('Дата рождения', u['birth_date'] or '—'),
                     ('Рост', f"{u['height']} см" if u['height'] else '—'),
                     ('Вес', f"{u['weight']} кг" if u['weight'] else '—'),
                     ('Цель', u['goal'] or '—'),('Зарегистрирован', u['created_at'][:10])]:
        rows_info += f"<div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--brd)'><span style='color:var(--mt);font-size:13px'>{lbl}</span><span style='font-size:13px'>{val}</span></div>"

    sub_html = ""
    if sub:
        plan = PLANS.get(sub['plan'],{})
        st_b = {'active':'<span class="badge bgr">Активен</span>','frozen':'<span class="badge byw">Заморожен</span>'}.get(sub['status'],'<span class="badge bre">Отменён</span>')
        sub_html = f"""
        <div style='font-family:monospace;font-size:20px;font-weight:700;margin-bottom:6px'>{plan.get('name','')}</div>
        <div style='margin-bottom:14px'>{st_b}</div>
        <div style='display:grid;gap:0;margin-bottom:14px'>
          <div style='display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--brd)'><span style='color:var(--mt);font-size:13px'>Стоимость</span><span class='mono' style='font-size:13px'>{plan.get('price',0):,} ₽/мес</span></div>
          <div style='display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--brd)'><span style='color:var(--mt);font-size:13px'>Начало</span><span class='mono' style='font-size:13px'>{sub['start_date']}</span></div>
          <div style='display:flex;justify-content:space-between;padding:9px 0'><span style='color:var(--mt);font-size:13px'>Конец</span><span class='mono' style='font-size:13px'>{sub['end_date']}</span></div>
        </div>
        <form method='POST' action='/admin/users/{uid}/cancel-sub' onsubmit="return confirm('Отменить абонемент?')"><button class='btn bd btn-sm'>Отменить абонемент</button></form>
        """
    else:
        sub_html = "<div style='color:var(--mt);font-size:13px;margin-bottom:16px'>Абонемент не оформлен</div>"

    plan_opts = ""
    for k, p in PLANS.items():
        sel = "checked" if sub and sub['plan']==k else ""
        plan_opts += f"""<label style='display:flex;align-items:center;gap:10px;padding:10px;border:1px solid var(--brd);border-radius:3px;cursor:pointer;margin-bottom:8px;'>
          <input type='radio' name='plan' value='{k}' style='width:auto;accent-color:var(--ac)' {sel}>
          <div><div style='font-weight:600;font-size:13px'>{p['name']}</div><div style='color:var(--mt);font-size:12px'>{p['price']:,} ₽/мес</div></div></label>"""

    enr_rows = ""
    for e in enr:
        enr_rows += f"<tr><td style='font-weight:500'>{e['name']}</td><td style='color:var(--mt)'>{e['tname'] or '—'}</td><td style='font-family:monospace;font-size:12px'>{e['day']}, {e['time']}</td></tr>"
    if not enr_rows:
        enr_rows = "<tr><td colspan='3'><div class='empty'><div class='etxt'>Нет записей</div></div></td></tr>"

    del_btn = f"<form method='POST' action='/admin/users/{uid}/delete' onsubmit=\"return confirm('Удалить пользователя?')\"><button class='btn bd'>Удалить</button></form>" if uid != session['user_id'] else ""
    c = f"""
    <div class="ph"><div><div class="ptitle">{u['name']}</div><div class="psub">{u['email']}</div></div><div style='display:flex;gap:9px'><a href='/admin/users' class='btn bo'>Назад</a>{del_btn}</div></div>
    <div class="g2" style="margin-bottom:22px;">
      <div class="card"><div class="stitle" style="margin-bottom:16px">Данные</div>{rows_info}</div>
      <div class="card">
        <div class="stitle" style="margin-bottom:16px">Абонемент</div>
        {sub_html}
        <div class="divider"></div>
        <div class="stitle" style="margin-bottom:12px">Назначить абонемент</div>
        <form method="POST" action="/admin/users/{uid}/set-sub">{plan_opts}<button type="submit" class="btn bp btn-sm">Назначить</button></form>
      </div>
    </div>
    <div class="stitle" style="margin-bottom:12px">Записи на тренировки ({len(enr)})</div>
    <div class="tw"><table><thead><tr><th>Тренировка</th><th>Тренер</th><th>День/Время</th></tr></thead><tbody>{enr_rows}</tbody></table></div>
    """
    return render(c, u['name'], "Профиль пользователя")

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_user(uid):
    if uid == session['user_id']:
        flash('Нельзя удалить собственный аккаунт','error')
        return redirect(url_for('admin_users'))
    u = q("SELECT name FROM users WHERE id=?", (uid,), one=True)
    if u:
        run("DELETE FROM enrollments WHERE user_id=?", (uid,))
        run("DELETE FROM subscriptions WHERE user_id=?", (uid,))
        run("DELETE FROM users WHERE id=?", (uid,))
        flash(f'Пользователь {u["name"]} удалён','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/set-sub', methods=['POST'])
@role_required('admin')
def admin_set_sub(uid):
    plan = request.form.get('plan')
    if plan in PLANS:
        start = datetime.now()
        end   = start + timedelta(days=30)
        run("DELETE FROM subscriptions WHERE user_id=?", (uid,))
        run("INSERT INTO subscriptions (user_id,plan,status,start_date,end_date) VALUES (?,?,?,?,?)",
            (uid, plan, 'active', start.strftime('%d.%m.%Y'), end.strftime('%d.%m.%Y')))
        flash('Абонемент назначен','success')
    return redirect(url_for('admin_user_detail', uid=uid))

@app.route('/admin/users/<int:uid>/cancel-sub', methods=['POST'])
@role_required('admin')
def admin_cancel_sub(uid):
    run("UPDATE subscriptions SET status='cancelled' WHERE user_id=?", (uid,))
    flash('Абонемент отменён','success')
    return redirect(url_for('admin_user_detail', uid=uid))

@app.route('/admin/workouts')
@role_required('admin')
def admin_workouts():
    df = request.args.get('day','all')
    ws = q("""SELECT w.*,u.name as tname,
              (SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
              FROM workouts w LEFT JOIN users u ON w.trainer_id=u.id
              ORDER BY w.day,w.time""")
    if df != 'all': ws = [w for w in ws if w['day']==df]
    day_opts = "".join(f"<option value='{d}' {'selected' if df==d else ''}>{d}</option>" for d in DAYS)
    reset = f"<a href='/admin/workouts' class='btn bg btn-sm'>Сбросить</a>" if df!='all' else ""
    rows = ""
    for w in ws:
        pct = int(w['enrolled']/w['max_spots']*100) if w['max_spots'] else 0
        clr = 'var(--ac)' if w['enrolled']>=w['max_spots'] else ('var(--yw)' if pct>70 else 'var(--gr)')
        rows += f"""<tr>
          <td><div style='font-weight:600'>{w['name']}</div><div style='font-size:12px;color:var(--mt)'>{w['description'] or ''}</div></td>
          <td style='color:var(--mt)'>{w['tname'] or '—'}</td>
          <td><span class='badge bdm'>{w['type']}</span></td>
          <td style='font-family:monospace;font-size:12px'>{w['day']}<br>{w['time']}, {w['duration']}</td>
          <td style='color:var(--mt)'>{w['room'] or '—'}</td>
          <td><span class='mono' style='font-size:13px'>{w['enrolled']}/{w['max_spots']}</span><div class='progress' style='width:70px'><div class='pf' style='width:{pct}%;background:{clr}'></div></div></td>
          <td><div style='display:flex;gap:6px'>
            <a href='/admin/workouts/{w['id']}' class='btn bg btn-sm'>Список</a>
            <form method='POST' action='/admin/workouts/{w["id"]}/delete' onsubmit="return confirm('Удалить тренировку?')"><button class='btn bd btn-sm'>Удалить</button></form>
          </div></td>
        </tr>"""
    if not rows:
        rows = f"<tr><td colspan='7'><div class='empty'><div class='etxt'>Тренировок нет. <a href='/admin/workouts/create' style='color:var(--acl)'>Создать первую</a></div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Расписание тренировок</div><div class="psub">{len(ws)} тренировок</div></div><a href="/admin/workouts/create" class="btn bp">+ Создать тренировку</a></div>
    <div class="fb"><form method="GET" style="display:flex;gap:8px;align-items:center;">
      <select name="day" style="width:auto;" onchange="this.form.submit()">
        <option value="all" {"selected" if df=="all" else ""}>Все дни</option>{day_opts}
      </select>{reset}
    </form></div>
    <div class="tw"><table><thead><tr><th>Название</th><th>Тренер</th><th>Тип</th><th>День/Время</th><th>Зал</th><th>Мест</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Тренировки", "Расписание тренировок")

@app.route('/admin/workouts/create', methods=['GET','POST'])
@role_required('admin')
def admin_create_workout():
    trainers = q("SELECT * FROM users WHERE role='trainer' ORDER BY name")
    error = None
    if request.method == 'POST':
        name     = request.form.get('name','').strip()
        desc     = request.form.get('description','')
        tid      = request.form.get('trainer_id')
        wtype    = request.form.get('type','')
        day      = request.form.get('day','')
        time     = request.form.get('time','')
        duration = request.form.get('duration','')
        room     = request.form.get('room','')
        spots    = request.form.get('max_spots', 20)
        if not all([name, tid, wtype, day, time, duration]):
            error = 'Заполните все обязательные поля'
        else:
            run("INSERT INTO workouts (name,description,trainer_id,type,day,time,duration,room,max_spots) VALUES (?,?,?,?,?,?,?,?,?)",
                (name, desc, int(tid), wtype, day, time, duration, room, int(spots)))
            flash(f'Тренировка "{name}" создана', 'success')
            return redirect(url_for('admin_workouts'))
    t_opts = "".join(f"<option value='{t['id']}'>{t['name']}</option>" for t in trainers)
    no_t   = "<div class='fhint' style='color:var(--acl)'>Нет тренеров. <a href='/admin/users/create' style='color:var(--acl)'>Создать тренера</a></div>" if not trainers else ""
    d_opts = "".join(f"<option value='{d}'>{d}</option>" for d in DAYS)
    ty_opts= "".join(f"<option value='{t}'>{t}</option>" for t in TYPES)
    err_html = f"<div class='err-box'>{error}</div>" if error else ""
    c = f"""
    <div class="ph"><div><div class="ptitle">Новая тренировка</div><div class="psub">Добавление в расписание</div></div><a href="/admin/workouts" class="btn bo">Назад</a></div>
    <div style="max-width:560px;"><div class="card">
    {err_html}
    <form method="POST">
      <div class="sec-lbl">Основное</div>
      <div style="margin-bottom:13px;"><label class="fl">Название *</label><input type="text" name="name" required placeholder="Силовая тренировка"></div>
      <div style="margin-bottom:13px;"><label class="fl">Описание</label><input type="text" name="description" placeholder="Краткое описание"></div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Тренер *</label><select name="trainer_id" required><option value="">Выберите тренера</option>{t_opts}</select>{no_t}</div>
        <div class="fg"><label class="fl">Тип *</label><select name="type" required><option value="">Выберите тип</option>{ty_opts}</select></div>
      </div>
      <div class="sec-lbl" style="margin-top:18px;">Расписание</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">День недели *</label><select name="day" required><option value="">Выберите день</option>{d_opts}</select></div>
        <div class="fg"><label class="fl">Время начала *</label><input type="time" name="time" required></div>
      </div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Продолжительность *</label><input type="text" name="duration" required placeholder="60 мин"></div>
        <div class="fg"><label class="fl">Зал</label><input type="text" name="room" placeholder="Зал A"></div>
      </div>
      <div style="margin-bottom:0;"><label class="fl">Максимум мест</label><input type="number" name="max_spots" value="20" min="1" max="100"></div>
      <div class="divider"></div>
      <div style="display:flex;gap:9px;"><button type="submit" class="btn bp">Создать тренировку</button><a href="/admin/workouts" class="btn bg">Отмена</a></div>
    </form>
    </div></div>"""
    return render(c, "Создать тренировку", "Создать тренировку")

@app.route('/admin/workouts/<int:wid>')
@role_required('admin')
def admin_workout_detail(wid):
    w = q("""SELECT w.*,u.name as tname,
             (SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
             FROM workouts w LEFT JOIN users u ON w.trainer_id=u.id WHERE w.id=?""", (wid,), one=True)
    if not w: flash('Не найдено','error'); return redirect(url_for('admin_workouts'))
    parts = q("""SELECT u.name,u.email,u.phone,en.enrolled_at FROM enrollments en
                 JOIN users u ON en.user_id=u.id WHERE en.workout_id=?""", (wid,))
    pct = int(w['enrolled']/w['max_spots']*100) if w['max_spots'] else 0
    clr = 'var(--ac)' if w['enrolled']>=w['max_spots'] else 'var(--gr)'
    free_b = f"<span class='badge bgr'>{w['max_spots']-w['enrolled']} свободных мест</span>" if w['enrolled']<w['max_spots'] else "<span class='badge bre'>Мест нет</span>"
    info_rows = ""
    for lbl,val in [('Тренер',w['tname'] or '—'),('Тип',w['type']),('День',w['day']),('Время',w['time']),('Длительность',w['duration']),('Зал',w['room'] or '—'),('Создана',w['created_at'][:10])]:
        info_rows += f"<div style='display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--brd)'><span style='color:var(--mt);font-size:13px'>{lbl}</span><span style='font-size:13px;font-weight:500'>{val}</span></div>"
    if w['description']:
        info_rows += f"<div style='padding:9px 0'><div style='color:var(--mt);font-size:13px;margin-bottom:5px'>Описание</div><div style='font-size:13px'>{w['description']}</div></div>"
    part_rows = "".join(f"<tr><td style='font-weight:500'>{p['name']}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{p['email']}</td><td style='color:var(--mt)'>{p['phone'] or '—'}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{p['enrolled_at'][:16]}</td></tr>" for p in parts)
    if not part_rows:
        part_rows = "<tr><td colspan='4'><div class='empty'><div class='etxt'>Нет участников</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">{w['name']}</div><div class="psub">{w['type']} — {w['day']}, {w['time']}</div></div>
    <div style="display:flex;gap:9px"><a href="/admin/workouts" class="btn bo">Назад</a>
    <form method="POST" action="/admin/workouts/{wid}/delete" onsubmit="return confirm('Удалить тренировку и все записи?')"><button class="btn bd">Удалить</button></form></div></div>
    <div class="g2" style="margin-bottom:22px;">
      <div class="card"><div class="stitle" style="margin-bottom:16px">Информация</div>{info_rows}</div>
      <div class="card">
        <div class="stitle" style="margin-bottom:16px">Заполненность</div>
        <div style="text-align:center;padding:16px 0">
          <div style="font-family:monospace;font-size:48px;font-weight:700;color:{clr};line-height:1">{w['enrolled']}</div>
          <div style="color:var(--mt);font-size:14px;margin-top:6px">из {w['max_spots']} мест</div>
        </div>
        <div class="progress" style="height:8px;margin:14px 0"><div class="pf" style="width:{pct}%;height:100%;background:{clr}"></div></div>
        <div style="text-align:center">{free_b}</div>
      </div>
    </div>
    <div class="stitle" style="margin-bottom:12px">Участники ({len(parts)})</div>
    <div class="tw"><table><thead><tr><th>Имя</th><th>Email</th><th>Телефон</th><th>Дата записи</th></tr></thead><tbody>{part_rows}</tbody></table></div>
    """
    return render(c, w['name'], "Детали тренировки")

@app.route('/admin/workouts/<int:wid>/delete', methods=['POST'])
@role_required('admin')
def admin_delete_workout(wid):
    w = q("SELECT name FROM workouts WHERE id=?", (wid,), one=True)
    if w:
        run("DELETE FROM enrollments WHERE workout_id=?", (wid,))
        run("DELETE FROM workouts WHERE id=?", (wid,))
        flash(f'Тренировка "{w["name"]}" удалена','success')
    return redirect(url_for('admin_workouts'))

@app.route('/admin/subs')
@role_required('admin')
def admin_subs():
    subs = q("""SELECT s.*,u.name as uname,u.email FROM subscriptions s
                JOIN users u ON s.user_id=u.id ORDER BY s.created_at DESC""")
    plan_stats = {}
    for k,p in PLANS.items():
        active = [s for s in subs if s['plan']==k and s['status']=='active']
        plan_stats[k] = {'name':p['name'],'price':p['price'],'count':len(active),'income':len(active)*p['price']}
    stat_cards = "".join(f"<div class='sc'><div class='slbl'>{v['name']}</div><div class='sval'>{v['count']}</div><div class='ssub'>{v['income']:,} ₽ доход</div></div>" for v in plan_stats.values())
    rows = ""
    for s in subs:
        plan_name = PLANS.get(s['plan'],{}).get('name', s['plan'])
        st_b = {'active':'<span class="badge bgr">Активен</span>','frozen':'<span class="badge byw">Заморожен</span>'}.get(s['status'],'<span class="badge bre">Отменён</span>')
        rows += f"<tr><td><div style='font-weight:500'>{s['uname']}</div><div style='font-size:12px;color:var(--mt);font-family:monospace'>{s['email']}</div></td><td>{plan_name}</td><td>{st_b}</td><td style='font-family:monospace;font-size:12px;color:var(--mt)'>{s['start_date']}</td><td style='font-family:monospace;font-size:12px;color:var(--mt)'>{s['end_date']}</td></tr>"
    if not rows:
        rows = "<tr><td colspan='5'><div class='empty'><div class='etxt'>Абонементов нет</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Абонементы</div><div class="psub">{len(subs)} записей</div></div></div>
    <div class="g3" style="margin-bottom:22px;">{stat_cards}</div>
    <div class="tw"><table><thead><tr><th>Клиент</th><th>Тариф</th><th>Статус</th><th>Начало</th><th>Конец</th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Абонементы", "Абонементы")


@app.route('/trainer')
@role_required('trainer')
def trainer_dash():
    uid = session['user_id']
    ws  = q("""SELECT w.*,(SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
               FROM workouts w WHERE w.trainer_id=? ORDER BY w.day,w.time""", (uid,))
    total = sum(w['enrolled'] for w in ws)
    stat_cards = f"""
    <div class="g3" style="margin-bottom:22px;">
      <div class="sc"><div class="slbl">Всего занятий</div><div class="sval">{len(ws)}</div></div>
      <div class="sc"><div class="slbl">Всего клиентов</div><div class="sval">{total}</div><div class="ssub">по всем занятиям</div></div>
      <div class="sc"><div class="slbl">Средняя группа</div><div class="sval">{int(total/len(ws)) if ws else 0}</div></div>
    </div>"""
    rows = ""
    for w in ws:
        pct = int(w['enrolled']/w['max_spots']*100) if w['max_spots'] else 0
        clr = 'var(--ac)' if w['enrolled']>=w['max_spots'] else 'var(--gr)'
        rows += f"""<tr>
          <td><div style='font-weight:600'>{w['name']}</div>{f"<div style='font-size:12px;color:var(--mt)'>{w['description']}</div>" if w['description'] else ''}</td>
          <td><span class='badge bdm'>{w['type']}</span></td>
          <td style='font-family:monospace;font-size:12px'>{w['day']}<br>{w['time']} ({w['duration']})</td>
          <td style='color:var(--mt)'>{w['room'] or '—'}</td>
          <td><span class='mono'>{w['enrolled']}/{w['max_spots']}</span><div class='progress' style='width:70px'><div class='pf' style='width:{pct}%;background:{clr}'></div></div></td>
          <td><a href='/trainer/workout/{w["id"]}' class='btn bo btn-sm'>Участники</a></td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'><div class='empty'><div class='etxt'>Вам не назначено ни одной тренировки</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Мои занятия</div><div class="psub">{len(ws)} тренировок в расписании</div></div></div>
    {stat_cards}
    <div class="tw"><table><thead><tr><th>Тренировка</th><th>Тип</th><th>День/Время</th><th>Зал</th><th>Записей</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Мои занятия", "Мои занятия")

@app.route('/trainer/workout/<int:wid>')
@role_required('trainer')
def trainer_workout(wid):
    w = q("""SELECT w.*,(SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
             FROM workouts w WHERE w.id=? AND w.trainer_id=?""", (wid, session['user_id']), one=True)
    if not w: flash('Не найдено','error'); return redirect(url_for('trainer_dash'))
    parts = q("""SELECT u.name,u.email,u.phone,en.enrolled_at FROM enrollments en
                 JOIN users u ON en.user_id=u.id WHERE en.workout_id=?""", (wid,))
    free  = w['max_spots'] - w['enrolled']
    free_b = f"<span class='badge bgr'>{free} свободных мест</span>" if free > 0 else "<span class='badge bre'>Мест нет</span>"
    part_rows = "".join(f"<tr><td style='font-weight:500'>{p['name']}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{p['email']}</td><td style='color:var(--mt)'>{p['phone'] or '—'}</td><td style='color:var(--mt);font-family:monospace;font-size:12px'>{p['enrolled_at'][:16]}</td></tr>" for p in parts)
    if not part_rows:
        part_rows = "<tr><td colspan='4'><div class='empty'><div class='etxt'>Нет участников</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">{w['name']}</div><div class="psub">{w['day']}, {w['time']} · {w['duration']} · {w['room'] or 'Зал не указан'}</div></div><a href="/trainer" class="btn bo">Назад</a></div>
    <div class="g3" style="margin-bottom:22px;">
      <div class="sc"><div class="slbl">Записано</div><div class="sval">{w['enrolled']}</div><div class="ssub">из {w['max_spots']} мест</div></div>
      <div class="sc"><div class="slbl">Свободно</div><div class="sval" style="color:{'var(--ac)' if free==0 else 'var(--gr)'}">{free}</div></div>
      <div class="sc"><div class="slbl">Тип занятия</div><div style="margin-top:9px"><span class='badge bdm'>{w['type']}</span></div>{f"<div style='font-size:12px;color:var(--mt);margin-top:8px'>{w['description']}</div>" if w['description'] else ''}</div>
    </div>
    <div class="stitle" style="margin-bottom:12px">Список участников</div>
    <div class="tw"><table><thead><tr><th>Имя</th><th>Email</th><th>Телефон</th><th>Дата записи</th></tr></thead><tbody>{part_rows}</tbody></table></div>
    """
    return render(c, w['name'], "Участники занятия")



@app.route('/cabinet')
@role_required('client')
def cabinet_dash():
    uid = session['user_id']
    u   = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    sub = q("SELECT * FROM subscriptions WHERE user_id=?", (uid,), one=True)
    enr = q("""SELECT w.*,u2.name as tname FROM enrollments en
               JOIN workouts w ON en.workout_id=w.id
               LEFT JOIN users u2 ON w.trainer_id=u2.id
               WHERE en.user_id=? ORDER BY w.day,w.time""", (uid,))
    if sub and sub['status']=='active':
        sub_html = f"<div style='font-family:monospace;font-size:20px;font-weight:700'>{PLANS.get(sub['plan'],{}).get('name','')}</div><div style='color:var(--mt);font-size:12px;margin-top:5px'>до {sub['end_date']}</div>"
    elif sub and sub['status']=='frozen':
        sub_html = f"<div style='font-family:monospace;font-size:20px;font-weight:700;color:var(--yw)'>Заморожен</div><div style='color:var(--mt);font-size:12px;margin-top:5px'>{PLANS.get(sub['plan'],{}).get('name','')}</div>"
    else:
        sub_html = f"<div style='color:var(--mt);font-size:14px'>Нет абонемента</div><div style='margin-top:8px'><a href='/cabinet/subscription' style='color:var(--acl);font-size:13px'>Оформить</a></div>"
    status_b = ({'active':'<span class="badge bgr">Активный клиент</span>','frozen':'<span class="badge byw">Абонемент заморожен</span>'}.get(sub['status'] if sub else '', '<span class="badge bdm">Без абонемента</span>'))
    enr_rows = "".join(f"<div style='display:flex;justify-content:space-between;align-items:center;padding:11px;background:var(--sf);border-radius:3px'><div><div style='font-weight:600;font-size:13px'>{e['name']}</div><div style='color:var(--mt);font-size:12px'>{e['tname'] or '—'} · {e['day']}</div></div><span class='mono' style='font-size:12px;color:var(--mt)'>{e['time']}</span></div>" for e in enr[:5])
    if not enr_rows:
        enr_rows = f"<div style='color:var(--mt);font-size:13px;padding:16px 0'>Нет записей. <a href='/cabinet/schedule' style='color:var(--acl)'>Просмотреть расписание</a></div>"
    info_rows = "".join(f"<div style='display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--brd)'><span style='color:var(--mt);font-size:13px'>{lbl}</span><span style='font-size:13px'>{val}</span></div>"
        for lbl,val in [('Email',u['email']),('Телефон',u['phone'] or '—'),('Дата рождения',u['birth_date'] or '—'),
                        ('Рост',f"{u['height']} см" if u['height'] else '—'),
                        ('Вес',f"{u['weight']} кг" if u['weight'] else '—'),
                        ('Цель',u['goal'] or '—')])
    c = f"""
    <div class="ph"><div><div class="ptitle">Добро пожаловать, {u['name'].split()[0]}</div><div class="psub">Личный кабинет</div></div><a href="/cabinet/profile" class="btn bo">Редактировать профиль</a></div>
    <div class="g3" style="margin-bottom:22px;">
      <div class="sc"><div class="slbl">Абонемент</div>{sub_html}</div>
      <div class="sc"><div class="slbl">Моих записей</div><div class="sval">{len(enr)}</div><div class="ssub">активных занятий</div></div>
      <div class="sc"><div class="slbl">Статус</div><div style="margin-top:9px">{status_b}</div></div>
    </div>
    <div class="g2">
      <div class="card"><div class="stitle" style="margin-bottom:16px">Мои данные</div>{info_rows}<div style="margin-top:14px"><a href="/cabinet/profile" class="btn bo btn-sm">Изменить</a></div></div>
      <div class="card"><div class="stitle" style="margin-bottom:16px">Ближайшие занятия</div><div style="display:grid;gap:8px">{enr_rows}</div>{f"<div style='margin-top:12px'><a href='/cabinet/my-workouts' class='btn bg btn-sm'>Все записи ({len(enr)})</a></div>" if len(enr)>5 else ''}</div>
    </div>
    """
    return render(c, "Личный кабинет", "Личный кабинет")

@app.route('/cabinet/schedule')
@role_required('client')
def cabinet_schedule():
    uid = session['user_id']
    df  = request.args.get('day','all')
    ws  = q("""SELECT w.*,u.name as tname,
               (SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
               FROM workouts w LEFT JOIN users u ON w.trainer_id=u.id ORDER BY w.day,w.time""")
    if df != 'all': ws = [w for w in ws if w['day']==df]
    enrolled_ids = {e['workout_id'] for e in q("SELECT workout_id FROM enrollments WHERE user_id=?", (uid,))}
    day_opts = "".join(f"<option value='{d}' {'selected' if df==d else ''}>{d}</option>" for d in DAYS)
    reset = f"<a href='/cabinet/schedule' class='btn bg btn-sm'>Сбросить</a>" if df!='all' else ""
    rows = ""
    for w in ws:
        pct = int(w['enrolled']/w['max_spots']*100) if w['max_spots'] else 0
        full= w['enrolled'] >= w['max_spots']
        if w['id'] in enrolled_ids:
            btn = f"<form method='POST' action='/cabinet/unenroll/{w['id']}'><button class='btn bo btn-sm'>Отменить</button></form>"
        elif full:
            btn = "<button class='btn btn-sm' style='background:transparent;color:var(--mt);border:1px solid var(--brd);cursor:default' disabled>Мест нет</button>"
        else:
            btn = f"<form method='POST' action='/cabinet/enroll/{w['id']}'><button class='btn bs btn-sm'>Записаться</button></form>"
        rows += f"""<tr>
          <td><div style='font-weight:600'>{w['name']}</div><div style='font-size:12px;color:var(--mt)'>{w['type']} · {w['duration']}</div>{f"<div style='font-size:12px;color:var(--mt)'>{w['description']}</div>" if w['description'] else ''}</td>
          <td style='color:var(--mt)'>{w['tname'] or '—'}</td>
          <td style='font-family:monospace;font-size:12px'>{w['day']}<br>{w['time']}</td>
          <td style='color:var(--mt)'>{w['room'] or '—'}</td>
          <td><span class='mono' style='font-size:13px'>{w['enrolled']}/{w['max_spots']}</span><div class='progress' style='width:60px'><div class='pf' style='width:{pct}%;background:{"var(--ac)" if full else "var(--gr)"}'></div></div></td>
          <td>{btn}</td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'><div class='empty'><div class='etxt'>Тренировок нет</div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Расписание</div><div class="psub">Запишитесь на тренировку</div></div></div>
    <div class="fb"><form method="GET" style="display:flex;gap:8px;align-items:center;">
      <select name="day" style="width:auto;" onchange="this.form.submit()"><option value="all" {"selected" if df=="all" else ""}>Все дни</option>{day_opts}</select>{reset}
    </form></div>
    <div class="tw"><table><thead><tr><th>Тренировка</th><th>Тренер</th><th>День/Время</th><th>Зал</th><th>Мест</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Расписание", "Расписание занятий")

@app.route('/cabinet/enroll/<int:wid>', methods=['POST'])
@role_required('client')
def cabinet_enroll(wid):
    uid = session['user_id']
    w   = q("SELECT * FROM workouts WHERE id=?", (wid,), one=True)
    if not w:
        flash('Занятие не найдено','error')
    else:
        cnt = q("SELECT COUNT(*) as c FROM enrollments WHERE workout_id=?", (wid,), one=True)['c']
        if cnt >= w['max_spots']:
            flash('Нет свободных мест','error')
        else:
            ex = q("SELECT id FROM enrollments WHERE user_id=? AND workout_id=?", (uid, wid), one=True)
            if ex:
                flash('Вы уже записаны на это занятие','error')
            else:
                run("INSERT INTO enrollments (user_id,workout_id) VALUES (?,?)", (uid, wid))
                flash('Вы успешно записаны!','success')
    return redirect(url_for('cabinet_schedule'))

@app.route('/cabinet/unenroll/<int:wid>', methods=['POST'])
@role_required('client')
def cabinet_unenroll(wid):
    run("DELETE FROM enrollments WHERE user_id=? AND workout_id=?", (session['user_id'], wid))
    flash('Запись отменена','success')
    return redirect(request.referrer or url_for('cabinet_schedule'))

@app.route('/cabinet/my-workouts')
@role_required('client')
def cabinet_my_workouts():
    enr = q("""SELECT w.*,u.name as tname,
               (SELECT COUNT(*) FROM enrollments e WHERE e.workout_id=w.id) as enrolled
               FROM enrollments en JOIN workouts w ON en.workout_id=w.id
               LEFT JOIN users u ON w.trainer_id=u.id
               WHERE en.user_id=? ORDER BY w.day,w.time""", (session['user_id'],))
    rows = "".join(f"""<tr>
      <td><div style='font-weight:600'>{e['name']}</div><div style='font-size:12px;color:var(--mt)'>{e['type']} · {e['duration']}</div></td>
      <td style='color:var(--mt)'>{e['tname'] or '—'}</td>
      <td style='font-family:monospace;font-size:12px'>{e['day']}<br>{e['time']}</td>
      <td style='color:var(--mt)'>{e['room'] or '—'}</td>
      <td><span class='mono'>{e['enrolled']}/{e['max_spots']}</span></td>
      <td><form method='POST' action='/cabinet/unenroll/{e["id"]}'><button class='btn bd btn-sm'>Отменить</button></form></td>
    </tr>""" for e in enr)
    if not rows:
        rows = f"<tr><td colspan='6'><div class='empty'><div class='etxt'>Нет записей</div><div style='margin-top:12px'><a href='/cabinet/schedule' class='btn bp btn-sm'>Посмотреть расписание</a></div></div></td></tr>"
    c = f"""
    <div class="ph"><div><div class="ptitle">Мои записи</div><div class="psub">{len(enr)} занятий</div></div><a href="/cabinet/schedule" class="btn bp">Записаться ещё</a></div>
    <div class="tw"><table><thead><tr><th>Тренировка</th><th>Тренер</th><th>День/Время</th><th>Зал</th><th>Участников</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
    """
    return render(c, "Мои записи", "Мои записи")

@app.route('/cabinet/subscription', methods=['GET'])
@role_required('client')
def cabinet_sub():
    uid = session['user_id']
    sub = q("SELECT * FROM subscriptions WHERE user_id=?", (uid,), one=True)
    cur_info = ""
    if sub:
        plan = PLANS.get(sub['plan'],{})
        st_b = {'active':'<span class="badge bgr">Активен</span>','frozen':'<span class="badge byw">Заморожен</span>'}.get(sub['status'],'<span class="badge bre">Отменён</span>')
        feats = "".join(f"<div style='padding:6px 0;font-size:13px;border-bottom:1px solid var(--brd)'><span style='color:var(--gr);margin-right:8px'>+</span>{f}</div>" for f in plan.get('features',[]))
        freeze_btn = ""
        if sub['status']=='active':
            freeze_btn = f"<form method='POST' action='/cabinet/sub/freeze' onsubmit=\"return confirm('Заморозить абонемент?')\"><button class='btn bo btn-sm'>Заморозить</button></form>"
        elif sub['status']=='frozen':
            freeze_btn = f"<form method='POST' action='/cabinet/sub/unfreeze'><button class='btn bs btn-sm'>Разморозить</button></form><div style='font-size:12px;color:var(--mt);margin-top:8px'>Срок будет продлён на дни заморозки</div>"
        cur_info = f"""
        <div class="card" style="margin-bottom:22px;max-width:520px;">
          <div class="stitle" style="margin-bottom:16px">Текущий абонемент</div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
            <div><div style="font-family:monospace;font-size:22px;font-weight:700">{plan.get('name','')}</div><div style="font-size:22px;color:var(--mt);margin-top:4px">{plan.get('price',0):,} ₽/мес</div></div>
            {st_b}
          </div>
          <div style="margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--brd)"><span style="color:var(--mt);font-size:13px">Начало</span><span class="mono" style="font-size:13px">{sub['start_date']}</span></div>
            <div style="display:flex;justify-content:space-between;padding:9px 0"><span style="color:var(--mt);font-size:13px">Конец</span><span class="mono" style="font-size:13px">{sub['end_date']}</span></div>
          </div>
          {feats}
          <div style="margin-top:16px">{freeze_btn}</div>
        </div>"""
    else:
        cur_info = "<div style='color:var(--mt);font-size:14px;margin-bottom:22px'>У вас нет активного абонемента. Выберите тариф ниже.</div>"
    plan_cards = ""
    for k, p in PLANS.items():
        active = sub and sub['plan']==k
        feats  = "".join(f"<div style='padding:5px 0;font-size:13px;border-bottom:1px solid var(--brd)'><span style='color:var(--gr);margin-right:8px'>+</span>{f}</div>" for f in p['features'])
        plan_cards += f"""
        <div class="card" style="border-color:{'var(--ac)' if active else 'var(--brd)'}">
          <div style="font-family:monospace;font-size:17px;font-weight:700;margin-bottom:5px">{p['name']}</div>
          <div style="font-size:22px;font-weight:700;margin-bottom:14px">{p['price']:,} <span style="font-size:13px;color:var(--mt)">₽/мес</span></div>
          <div class="divider" style="margin:14px 0"></div>
          {feats}
          <form method="POST" action="/cabinet/sub/buy" style="margin-top:16px">
            <input type="hidden" name="plan" value="{k}">
            <button type="submit" class="btn {'bo' if active else 'bp'}" style="width:100%">{'Текущий тариф' if active else 'Выбрать'}</button>
          </form>
        </div>"""
    c = f"""
    <div class="ph"><div><div class="ptitle">Абонемент</div><div class="psub">Управление подпиской</div></div></div>
    {cur_info}
    <div class="stitle" style="margin-bottom:14px">{'Сменить тариф' if sub else 'Выбрать тариф'}</div>
    <div class="g3">{plan_cards}</div>
    """
    return render(c, "Абонемент", "Мой абонемент")

@app.route('/cabinet/sub/buy', methods=['POST'])
@role_required('client')
def cabinet_buy_sub():
    plan = request.form.get('plan')
    if plan in PLANS:
        uid   = session['user_id']
        start = datetime.now()
        end   = start + timedelta(days=30)
        run("DELETE FROM subscriptions WHERE user_id=?", (uid,))
        run("INSERT INTO subscriptions (user_id,plan,status,start_date,end_date) VALUES (?,?,?,?,?)",
            (uid, plan, 'active', start.strftime('%d.%m.%Y'), end.strftime('%d.%m.%Y')))
        flash(f'Абонемент "{PLANS[plan]["name"]}" оформлен на 30 дней','success')
    return redirect(url_for('cabinet_sub'))

@app.route('/cabinet/sub/freeze', methods=['POST'])
@role_required('client')
def cabinet_freeze():
    run("UPDATE subscriptions SET status='frozen',frozen_at=datetime('now','localtime') WHERE user_id=? AND status='active'", (session['user_id'],))
    flash('Абонемент заморожен','success')
    return redirect(url_for('cabinet_sub'))

@app.route('/cabinet/sub/unfreeze', methods=['POST'])
@role_required('client')
def cabinet_unfreeze():
    uid = session['user_id']
    sub = q("SELECT * FROM subscriptions WHERE user_id=?", (uid,), one=True)
    if sub and sub['status']=='frozen' and sub['frozen_at']:
        frozen_since = datetime.fromisoformat(sub['frozen_at'])
        days_frozen  = (datetime.now() - frozen_since).days
        old_end      = datetime.strptime(sub['end_date'],'%d.%m.%Y')
        new_end      = old_end + timedelta(days=days_frozen)
        run("UPDATE subscriptions SET status='active',frozen_at=NULL,end_date=? WHERE user_id=?",
            (new_end.strftime('%d.%m.%Y'), uid))
    flash('Абонемент разморожен, срок продлён','success')
    return redirect(url_for('cabinet_sub'))

@app.route('/cabinet/profile', methods=['GET','POST'])
@role_required('client')
def cabinet_profile():
    uid = session['user_id']
    u   = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if request.method == 'POST':
        name = request.form.get('name', u['name']).strip()
        run("UPDATE users SET name=?,phone=?,birth_date=?,height=?,weight=?,goal=? WHERE id=?",
            (name, request.form.get('phone',''), request.form.get('birth_date',''),
             request.form.get('height',''), request.form.get('weight',''),
             request.form.get('goal',''), uid))
        session['name'] = name
        flash('Профиль обновлён','success')
        return redirect(url_for('cabinet_profile'))
    c = f"""
    <div class="ph"><div><div class="ptitle">Мой профиль</div><div class="psub">Личные данные</div></div></div>
    <div style="max-width:500px;"><div class="card">
    <form method="POST">
      <div class="sec-lbl">Личные данные</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Имя и фамилия</label><input type="text" name="name" value="{u['name']}" required></div>
        <div class="fg"><label class="fl">Телефон</label><input type="tel" name="phone" value="{u['phone'] or ''}"></div>
      </div>
      <div style="margin-bottom:13px"><label class="fl">Дата рождения</label><input type="date" name="birth_date" value="{u['birth_date'] or ''}"></div>
      <div class="sec-lbl" style="margin-top:18px;">Физические параметры</div>
      <div class="g2" style="margin-bottom:13px;">
        <div class="fg"><label class="fl">Рост (см)</label><input type="number" name="height" value="{u['height'] or ''}" placeholder="175"></div>
        <div class="fg"><label class="fl">Вес (кг)</label><input type="number" name="weight" value="{u['weight'] or ''}" placeholder="70"></div>
      </div>
      <div><label class="fl">Цель тренировок</label><input type="text" name="goal" value="{u['goal'] or ''}" placeholder="Похудение, набор массы..."></div>
      <div class="divider"></div>
      <div style="display:flex;gap:9px;align-items:center">
        <button type="submit" class="btn bp">Сохранить</button>
        <span style="font-size:13px;color:var(--mt)">Email: {u['email']}</span>
      </div>
    </form>
    </div></div>"""
    return render(c, "Профиль", "Мой профиль")


if __name__ == '__main__':
    init_db()
    print("\n GymPro запущен!")
    print(" Открыть: http://127.0.0.1:5000")
    print(" Вход:    admin@gym.ru / admin123\n")
    app.run(debug=True)
