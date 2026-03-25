from flask import Flask, render_template, request, redirect, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cinta-kita-2024-secret-key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

PIN = os.environ.get('PIN', '090225')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image TEXT NOT NULL,
        caption TEXT,
        date TEXT,
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    defaults = {
        'pin': PIN,
        'love_start_date': '2024-09-08',
        'site_title': 'Our Private World ❤️',
        'letter_content': 'Halo Reni sayang...',
        'secret_message': 'Aku sayang kamu! ❤️',
        'theme_primary': '#ff6b9d',
        'theme_secondary': '#ffa3c4',
        'locations': 'Tempat Pertama::Taman Kota::🌅\nTempat Jalan::Kedai Kopi Kita::☕\nTempat Spesial::Mana aja::💕',
        'chat_history': 'reni|Hai|08:30\naku|Hai Reni!|08:32\nreni|Kangen|08:33',
        'quiz_data': 'Tanggal pacar kita?|8 September|15 Agustus|1 Oktober|20 Juli|0'
    }
    
    for key, value in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    conn.commit()
    conn.close()

def get_setting(key, default=''):
    conn = get_db_connection()
    result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return result['value'] if result else default

def check_login():
    return session.get('logged_in', False)

@app.route('/')
def index():
    if check_login():
        return redirect('/home')
    site_title = get_setting('site_title', 'Our Private World ❤️')
    theme = {
        'primary': get_setting('theme_primary', '#ff6b9d'),
        'secondary': get_setting('theme_secondary', '#ffa3c4'),
    }
    return render_template('login.html', site_title=site_title, theme=theme)

@app.route('/login', methods=['POST'])
def login():
    pin = request.form.get('pin', '')
    if pin == get_setting('pin', PIN) or pin == PIN:
        session['logged_in'] = True
        session['login_time'] = datetime.now().isoformat()
        return {'success': True, 'message': 'Login berhasil'}
    return {'success': False, 'message': 'PIN salah'}

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/home')
def home():
    if not check_login():
        return redirect('/')
    
    love_start = get_setting('love_start_date', '2024-09-08')
    try:
        start_date = datetime.strptime(love_start, '%Y-%m-%d')
        love_days = (datetime.now() - start_date).days
    except:
        love_days = 0
    
    conn = get_db_connection()
    photos = conn.execute('SELECT * FROM gallery ORDER BY created_at DESC').fetchall()
    conn.close()
    
    locations = []
    loc_str = get_setting('locations', '')
    for line in loc_str.strip().split('\n'):
        parts = line.split('::')
        if len(parts) >= 3:
            locations.append({'name': parts[0], 'cafe': parts[1], 'desc': parts[2], 'emoji': parts[2]})
        elif len(parts) == 2:
            locations.append({'name': parts[0], 'desc': parts[1], 'emoji': '📍'})
    
    chat_history = []
    chat_str = get_setting('chat_history', '')
    for line in chat_str.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 3:
            chat_history.append({'sender': parts[0], 'text': parts[1], 'time': parts[2]})
    
    site_title = get_setting('site_title', 'Our Private World ❤️')
    theme = {
        'primary': get_setting('theme_primary', '#ff6b9d'),
        'secondary': get_setting('theme_secondary', '#ffa3c4'),
    }
    
    hour = datetime.now().hour
    if 6 <= hour < 12: time_period = 'morning'
    elif 12 <= hour < 17: time_period = 'afternoon'
    elif 17 <= hour < 20: time_period = 'evening'
    else: time_period = 'night'
    
    return render_template('home.html', photos=photos, locations=locations, chat_history=chat_history, 
                          love_days=love_days, site_title=site_title, theme=theme, time_period=time_period)

@app.route('/letter')
def letter():
    if not check_login():
        return redirect('/')
    
    letter_content = get_setting('letter_content', 'Belum ada surat...')
    theme = {
        'primary': get_setting('theme_primary', '#ff6b9d'),
        'secondary': get_setting('theme_secondary', '#ffa3c4'),
    }
    hour = datetime.now().hour
    time_period = 'morning' if 6 <= hour < 12 else 'afternoon' if 12 <= hour < 17 else 'evening' if 17 <= hour < 20 else 'night'
    return render_template('letter.html', letter_content=letter_content, theme=theme, time_period=time_period)

@app.route('/random-memory')
def random_memory():
    if not check_login():
        return jsonify({'success': False})
    conn = get_db_connection()
    photos = conn.execute('SELECT * FROM gallery ORDER BY RANDOM() LIMIT 1').fetchall()
    conn.close()
    if photos:
        return jsonify({'success': True, 'image': photos[0]['image'], 'caption': photos[0]['caption'], 'date': photos[0]['date']})
    return jsonify({'success': False})

@app.route('/secret')
def secret():
    if not check_login():
        return jsonify({'message': ''})
    return jsonify({'message': get_setting('secret_message', 'Aku sayang kamu! ❤️')})

@app.route('/quiz', methods=['POST'])
def quiz():
    if not check_login():
        return jsonify({'success': False})
    return jsonify({'success': True, 'message': 'Betul! ❤️'})

@app.route('/admin')
def admin():
    if not check_login():
        return redirect('/')
    
    conn = get_db_connection()
    photos = conn.execute('SELECT * FROM gallery ORDER BY created_at DESC').fetchall()
    settings = {}
    for row in conn.execute('SELECT key, value FROM settings'):
        settings[row['key']] = row['value']
    conn.close()
    
    theme = {
        'primary': settings.get('theme_primary', '#ff6b9d'),
        'secondary': settings.get('theme_secondary', '#ffa3c4'),
    }
    
    return render_template('admin.html', photos=photos, settings=settings, theme=theme)

@app.route('/admin/gallery/add', methods=['POST'])
def admin_gallery_add():
    if not check_login():
        return redirect('/')
    
    if 'photo' not in request.files:
        return redirect('/admin')
    
    file = request.files['photo']
    if file.filename == '':
        return redirect('/admin')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        caption = request.form.get('caption', '')
        date = request.form.get('date', '')
        location = request.form.get('location', '')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO gallery (image, caption, date, location) VALUES (?, ?, ?, ?)',
                    (filename, caption, date, location))
        conn.commit()
        conn.close()
    
    return redirect('/admin')

@app.route('/admin/gallery/delete/<int:id>')
def admin_gallery_delete(id):
    if not check_login():
        return redirect('/')
    
    conn = get_db_connection()
    photo = conn.execute('SELECT image FROM gallery WHERE id = ?', (id,)).fetchone()
    if photo:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo['image']))
        except:
            pass
        conn.execute('DELETE FROM gallery WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/settings', methods=['POST'])
def admin_settings():
    if not check_login():
        return redirect('/')
    
    for key in ['pin', 'love_start_date', 'site_title', 'letter_content', 'secret_message', 
                'theme_primary', 'theme_secondary', 'locations', 'chat_history', 'quiz_data']:
        value = request.form.get(key, '')
        conn = get_db_connection()
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    
    return redirect('/admin')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)