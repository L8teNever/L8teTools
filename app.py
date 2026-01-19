import os
import io
import zipfile
import yt_dlp
import imageio_ffmpeg
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import tempfile
import uuid
import whois
import requests
import holidays
from datetime import datetime, timedelta
from PIL import Image, ExifTags
import img2pdf
import fitz  # PyMuPDF
from pillow_heif import register_heif_opener
import cairosvg
from pdf2docx import Converter as PDF2Docx
import markdown2
import glob
import time
from apscheduler.schedulers.background import BackgroundScheduler

try:
    import moviepy.editor as mp
except ImportError:
    import moviepy as mp

register_heif_opener()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Security improvements
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_PROTECTION = 'strong'
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Shortlink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    target_url = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('shortlinks', lazy=True))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('notes', lazy=True))

class WikiEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    category = db.Column(db.String(100), default='General')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('wiki_entries', lazy=True))

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255))

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    question = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    allow_suggestions = db.Column(db.Boolean, default=False)
    anonymous_voting = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('polls', lazy=True))
    options = db.relationship('PollOption', backref='poll', cascade="all, delete-orphan", lazy=True)

class PollOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    
    votes = db.relationship('PollVote', backref='option', cascade="all, delete-orphan", lazy=True)

class PollVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_option_id = db.Column(db.Integer, db.ForeignKey('poll_option.id'), nullable=False)
    voter_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class WordCloud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('word_clouds', lazy=True))
    entries = db.relationship('WordCloudEntry', backref='word_cloud', cascade="all, delete-orphan", lazy=True)

class WordCloudEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word_cloud_id = db.Column(db.Integer, db.ForeignKey('word_cloud.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    voter_name = db.Column(db.String(100), default='Anonym')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config['SECRET_KEY'] == 'dev-secret-key-change-this':
        import logging
        logging.warning("SECURITY WARNING: Using default SECRET_KEY. Please change this in your environment variables for better security.")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.session_protection = "strong"

    with app.app_context():
        db.create_all()

        # SQLite Migration: Add is_admin column if it doesn't exist
        try:
            db.session.execute(db.text('ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
            db.session.commit()
        except:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE poll ADD COLUMN allow_suggestions BOOLEAN DEFAULT 0'))
            db.session.execute(db.text('ALTER TABLE poll ADD COLUMN anonymous_voting BOOLEAN DEFAULT 0'))
            db.session.commit()
        except:
            db.session.rollback()

        # Ensure default domain exists
        domain_config = SystemConfig.query.filter_by(key='shortener_domain').first()
        if not domain_config:
            db.session.add(SystemConfig(key='shortener_domain', value='tools.l8tenever.de'))
            db.session.commit()
        
        # Optional: Promote first user to admin if no admin exists
        if not User.query.filter_by(is_admin=True).first():
            first_user = User.query.first()
            if first_user:
                first_user.is_admin = True
                db.session.commit()

        # Ensure retention config exists
        retention_config = SystemConfig.query.filter_by(key='file_retention_minutes').first()
        if not retention_config:
            # Default: 1440 minutes = 24 hours
            db.session.add(SystemConfig(key='file_retention_minutes', value='1440'))
            db.session.commit()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                remember = True if request.form.get('remember') else False
                session.permanent = remember
                login_user(user, remember=remember)
                return redirect(url_for('dashboard'))
            else:
                flash('Ungültiger Benutzername oder Passwort', 'error')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/offline')
    def offline():
        return render_template('offline.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html', user=current_user)

    @app.route('/tools/password-generator')
    @login_required
    def password_generator():
        return render_template('tools/password_generator.html')

    @app.route('/tools/qr-generator')
    @login_required
    def qr_generator():
        return render_template('tools/qr_generator.html')

    @app.route('/tools/file-converter')
    @login_required
    def file_converter():
        return render_template('tools/file_converter.html')

    @app.route('/tools/wheel-of-fortune')
    @login_required
    def wheel_of_fortune():
        return render_template('tools/wheel_of_fortune.html')

    @app.route('/tools/dice-roller')
    @login_required
    def dice_roller():
        return render_template('tools/dice_roller.html')

    @app.route('/tools/score-tracker')
    @login_required
    def score_tracker():
        return render_template('tools/score_tracker.html', user=current_user)

    @app.route('/tools/color-picker')
    @login_required
    def color_picker():
        return render_template('tools/color_picker.html')

    @app.route('/tools/polls')
    @login_required
    def polls_tool():
        user_polls = Poll.query.filter_by(user_id=current_user.id).order_by(Poll.created_at.desc()).all()
        return render_template('tools/polls.html', polls=user_polls)

    @app.route('/tools/word-clouds')
    @login_required
    def word_clouds_tool():
        clouds = WordCloud.query.filter_by(user_id=current_user.id).order_by(WordCloud.created_at.desc()).all()
        return render_template('tools/word_clouds.html', clouds=clouds)

    @app.route('/tools/shortlinks')
    @login_required
    def shortlinks():
        user_links = Shortlink.query.filter_by(user_id=current_user.id).order_by(Shortlink.created_at.desc()).all()
        domain = SystemConfig.query.filter_by(key='shortener_domain').first().value
        return render_template('tools/shortlinks.html', links=user_links, domain=domain)

    @app.route('/tools/video-downloader')
    @login_required
    def video_downloader():
        return render_template('tools/video_downloader.html')

    @app.route('/api/tools/video-downloader/download', methods=['POST'])
    @login_required
    def api_video_download():
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'mp4') # 'mp4' or 'mp3'

        if not url:
            return jsonify({'error': 'URL erforderlich'}), 400

        try:
            download_dir = os.path.join(tempfile.gettempdir(), 'l8te_downloads')
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            ydl_opts = {
                'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                'ffmpeg_location': ffmpeg_path,
                'quiet': True,
                'no_warnings': True,
            }

            if format_type == 'mp3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # If mp3, the extension might have changed
                if format_type == 'mp3':
                    file_path = os.path.splitext(file_path)[0] + '.mp3'

                if not os.path.exists(file_path):
                    # Fallback check if filename preparation didn't match actual output
                    basename = os.path.splitext(os.path.basename(file_path))[0]
                    matches = glob.glob(os.path.join(download_dir, f"{basename}*"))
                    if matches:
                        file_path = matches[0]
                    else:
                        return jsonify({'error': 'Datei nach Download nicht gefunden'}), 500

                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path)
                )

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/settings')
    @login_required
    def settings():
        domain_conf = SystemConfig.query.filter_by(key='shortener_domain').first()
        domain = domain_conf.value if domain_conf else "tools.l8tenever.de"
        
        retention_conf = SystemConfig.query.filter_by(key='file_retention_minutes').first()
        retention_minutes = int(retention_conf.value) if retention_conf else 1440

        all_users = []
        if current_user.is_admin:
            all_users = User.query.all()
        
        version = "v.0.0.0"
        try:
            with open('version.txt', 'r') as f:
                version = f.read().strip()
        except:
            pass
            
        return render_template('settings.html', domain=domain, retention_minutes=retention_minutes, users=all_users, version=version)

    @app.route('/api/settings/retention', methods=['POST'])
    @login_required
    def api_update_retention():
        if not current_user.is_admin:
            return jsonify({'error': 'Nur Admins können dies ändern'}), 403
            
        data = request.json
        try:
            minutes = int(data.get('minutes', 1440))
            if minutes < 0: 
                return jsonify({'error': 'Ungültiger Wert'}), 400
            
            config = SystemConfig.query.filter_by(key='file_retention_minutes').first()
            if not config:
                config = SystemConfig(key='file_retention_minutes', value=str(minutes))
                db.session.add(config)
            else:
                config.value = str(minutes)
                
            db.session.commit()
            return jsonify({'message': 'Aufbewahrungszeitraum aktualisiert'})
        except ValueError:
            return jsonify({'error': 'Muss eine Zahl sein'}), 400

    @app.route('/api/settings/password', methods=['POST'])
    @login_required
    def api_change_password():
        data = request.json
        new_password = data.get('password')
        if not new_password or len(new_password) < 4:
            return jsonify({'error': 'Passwort zu kurz'}), 400
        
        current_user.set_password(new_password)
        db.session.commit()
        return jsonify({'message': 'Passwort geändert'})

    @app.route('/api/settings/create-user', methods=['POST'])
    @login_required
    def api_create_user():
        # Optional: only allow if current user is admin, or always allow? 
        # User requested: "auch neue acc erstllen" - usually for admins or if open.
        # I'll check is_admin.
        if not current_user.is_admin:
            return jsonify({'error': 'Nur Admins können Benutzer erstellen'}), 403
            
        data = request.json
        username = data.get('username')
        password = data.get('password')
        is_admin = data.get('is_admin', False)

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Benutzer existiert bereits'}), 400
        
        new_user = User(username=username)
        new_user.set_password(password)
        new_user.is_admin = is_admin
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': f'Benutzer {username} erstellt'})

    @app.route('/api/settings/domain', methods=['POST'])
    @login_required
    def api_update_domain():
        if not current_user.is_admin:
            return jsonify({'error': 'Nur Admins können die Domain ändern'}), 403
        
        data = request.json
        new_domain = data.get('domain', '').strip()
        if not new_domain:
            return jsonify({'error': 'Domain darf nicht leer sein'}), 400
            
        config = SystemConfig.query.filter_by(key='shortener_domain').first()
        config.value = new_domain
        db.session.commit()
        return jsonify({'message': 'Domain aktualisiert'})

    @app.route('/tools/playground')
    @login_required
    def playground():
        return render_template('tools/playground.html')

    @app.route('/tools/unit-converter')
    @login_required
    def unit_converter():
        return render_template('tools/unit_converter.html')

    @app.route('/tools/diff-checker')
    @login_required
    def diff_checker():
        return render_template('tools/diff_checker.html')

    @app.route('/tools/case-converter')
    @login_required
    def case_converter():
        return render_template('tools/case_converter.html')

    @app.route('/tools/word-counter')
    @login_required
    def word_counter():
        return render_template('tools/word_counter.html')

    @app.route('/tools/exif-remover')
    @login_required
    def exif_remover():
        return render_template('tools/exif_remover.html')

    @app.route('/api/tools/exif/analyze', methods=['POST'])
    @login_required
    def api_exif_analyze():
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400

        try:
            # Save temp file
            ext = os.path.splitext(file.filename)[1]
            temp_name = f"l8te_exif_{uuid.uuid4()}{ext}"
            temp_path = os.path.join(tempfile.gettempdir(), temp_name)
            file.save(temp_path)

            # Analyze EXIF
            img = Image.open(temp_path)
            exif_data = {}
            raw_exif = img.getexif()
            
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    # Handle binary data safely
                    if isinstance(value, bytes):
                        try:
                            value = value.decode()
                        except:
                            value = '<binary data>'
                    exif_data[tag_id] = {'name': tag_name, 'value': str(value)}

            return jsonify({
                'token': temp_name,
                'exif': exif_data,
                'has_exif': bool(exif_data)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tools/exif/process', methods=['POST'])
    @login_required
    def api_exif_process():
        try:
            data = request.json
            token = data.get('token')
            action = data.get('action') # 'clean' or 'save'
            updates = data.get('updates', {})

            if not token:
                return jsonify({'error': 'Token fehlt'}), 400

            temp_path = os.path.join(tempfile.gettempdir(), token)
            if not os.path.exists(temp_path):
                return jsonify({'error': 'Datei nicht gefunden (Session abgelaufen)'}), 404

            img = Image.open(temp_path)
            
            if action == 'clean':
                # Remove all EXIF - create new image without it
                data = list(img.getdata())
                image_without_exif = Image.new(img.mode, img.size)
                image_without_exif.putdata(data)
                
                output = io.BytesIO()
                image_without_exif.save(output, format=img.format or 'JPEG')
                output.seek(0)
                
                return send_file(
                    output,
                    mimetype=Image.MIME[img.format or 'JPEG'],
                    as_attachment=True,
                    download_name=f"clean_{token}"
                )
            
            elif action == 'save':
                # Update EXIF
                exif = img.getexif()
                for tag_id, value in updates.items():
                    try:
                        # Try to remove if empty
                        if value == "":
                            del exif[int(tag_id)]
                        else:
                            exif[int(tag_id)] = value
                    except:
                        pass # Ignore errors for now
                
                output = io.BytesIO()
                img.save(output, format=img.format or 'JPEG', exif=exif)
                output.seek(0)
                
                return send_file(
                    output,
                    mimetype=Image.MIME[img.format or 'JPEG'],
                    as_attachment=True,
                    download_name=f"edited_{token}"
                )

            return jsonify({'error': 'Ungültige Aktion'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/tools/my-ip')
    @login_required
    def my_ip():
        return render_template('tools/my_ip.html')

    @app.route('/tools/whois')
    @login_required
    def whois_lookup():
        return render_template('tools/whois.html')

    @app.route('/tools/mac-lookup')
    @login_required
    def mac_lookup():
        return render_template('tools/mac_lookup.html')

    @app.route('/tools/bmi-calculator')
    @login_required
    def bmi_calculator():
        return render_template('tools/bmi_calculator.html')

    @app.route('/tools/text-sorter')
    @login_required
    def text_sorter():
        return render_template('tools/text_sorter.html')

    @app.route('/tools/regex-replacer')
    @login_required
    def regex_replacer():
        return render_template('tools/regex_replacer.html')

    @app.route('/tools/list-comparator')
    @login_required
    def list_comparator():
        return render_template('tools/list_comparator.html')

    @app.route('/tools/morse-code')
    @login_required
    def morse_code():
        return render_template('tools/morse_code.html')

    @app.route('/tools/workday-calculator')
    @login_required
    def workday_calculator():
        return render_template('tools/workday_calculator.html')

    @app.route('/tools/prefix-suffix')
    @login_required
    def prefix_suffix():
        return render_template('tools/prefix_suffix.html')

    @app.route('/tools/notes')
    @login_required
    def notes_tool():
        return render_template('tools/notes.html')

    @app.route('/tools/wiki')
    @login_required
    def wiki_tool():
        return render_template('tools/wiki.html')

    @app.route('/api/tools/my-ip', methods=['GET'])
    @login_required
    def api_get_my_ip():
        # Try to get the real IP if behind proxy
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr
        return jsonify({'ip': ip})

    @app.route('/api/tools/whois', methods=['POST'])
    @login_required
    def api_whois():
        domain = request.json.get('domain')
        if not domain:
            return jsonify({'error': 'Domain erforderlich'}), 400
        try:
            w = whois.whois(domain)
            # Convert datetime objects to string
            result = {}
            for key, value in w.items():
                if value is None:
                    continue
                if isinstance(value, list):
                    # Handle list of datetimes or strings
                    new_list = []
                    for item in value:
                        if hasattr(item, 'isoformat'):
                            new_list.append(item.isoformat())
                        else:
                            new_list.append(str(item))
                    result[key] = new_list
                elif hasattr(value, 'isoformat'):
                    result[key] = value.isoformat()
                else:
                    result[key] = str(value)
            
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': f'Konnte Domain nicht abrufen: {str(e)}'}), 500

    @app.route('/api/tools/mac-lookup', methods=['POST'])
    @login_required
    def api_mac_lookup():
        mac = request.json.get('mac')
        if not mac:
            return jsonify({'error': 'MAC-Adresse erforderlich'}), 400
        
        try:
            # Use macvendors.com API
            res = requests.get(f"https://api.macvendors.com/{mac}")
            if res.status_code == 200:
                return jsonify({'vendor': res.text})
            elif res.status_code == 404:
                return jsonify({'vendor': 'Hersteller nicht gefunden'})
            else:
                return jsonify({'vendor': 'Fehler bei der Abfrage'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tools/workdays', methods=['POST'])
    @login_required
    def api_calculate_workdays():
        data = request.json
        start_str = data.get('start')
        end_str = data.get('end')
        state = data.get('state', 'DE') # Default to Germany, or maybe a specific state

        if not start_str or not end_str:
            return jsonify({'error': 'Start- und Enddatum erforderlich'}), 400

        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

            if start_date > end_date:
                start_date, end_date = end_date, start_date

            de_holidays = holidays.DE() # Germany holidays
            
            total_days = (end_date - start_date).days + 1
            workdays = 0
            weekends = 0
            public_holidays = 0
            
            mondays = 0
            
            current = start_date
            while current <= end_date:
                is_weekend = current.weekday() >= 5 # 5=Sat, 6=Sun
                is_holiday = current in de_holidays
                
                if current.weekday() == 0:
                    mondays += 1

                if is_weekend:
                    weekends += 1
                elif is_holiday:
                    public_holidays += 1
                else:
                    workdays += 1
                
                current += timedelta(days=1)

            return jsonify({
                'total_days': total_days,
                'workdays': workdays,
                'weekends': weekends,
                'public_holidays': public_holidays,
                'mondays': mondays
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Notes API
    @app.route('/api/notes', methods=['GET'])
    @login_required
    def api_get_notes():
        notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc()).all()
        return jsonify([{
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'updated_at': n.updated_at.isoformat()
        } for n in notes])

    @app.route('/api/notes', methods=['POST'])
    @login_required
    def api_create_note():
        data = request.json
        title = data.get('title', 'Neue Notiz')
        content = data.get('content', '')
        
        note = Note(title=title, content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'updated_at': note.updated_at.isoformat()
        })

    @app.route('/api/notes/<int:note_id>', methods=['PUT'])
    @login_required
    def api_update_note(note_id):
        note = Note.query.get_or_404(note_id)
        if note.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
            
        data = request.json
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        db.session.commit()
        
        return jsonify({'message': 'Gespeichert'})

    @app.route('/api/notes/<int:note_id>', methods=['DELETE'])
    @login_required
    def api_delete_note(note_id):
        note = Note.query.get_or_404(note_id)
        if note.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
            
        db.session.delete(note)
        db.session.commit()
        return jsonify({'message': 'Gelöscht'})

    # Wiki API
    @app.route('/api/wiki', methods=['GET'])
    @login_required
    def api_get_wiki_entries():
        entries = WikiEntry.query.filter_by(user_id=current_user.id).order_by(WikiEntry.category, WikiEntry.title).all()
        return jsonify([{
            'id': e.id,
            'title': e.title,
            'category': e.category,
            'updated_at': e.updated_at.isoformat()
        } for e in entries])

    @app.route('/api/wiki/<int:entry_id>', methods=['GET'])
    @login_required
    def api_get_wiki_entry(entry_id):
        entry = WikiEntry.query.get_or_404(entry_id)
        if entry.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
            
        html_content = markdown2.markdown(entry.content or "", extras=["fenced-code-blocks", "tables", "break-on-newline"])
        
        return jsonify({
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'category': entry.category,
            'html': html_content,
            'updated_at': entry.updated_at.isoformat()
        })

    @app.route('/api/wiki', methods=['POST'])
    @login_required
    def api_create_wiki_entry():
        data = request.json
        title = data.get('title', 'Neuer Eintrag')
        content = data.get('content', '')
        category = data.get('category', 'Allgemein')
        
        entry = WikiEntry(title=title, content=content, category=category, user_id=current_user.id)
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({'id': entry.id, 'message': 'Erstellt'})

    @app.route('/api/wiki/<int:entry_id>', methods=['PUT'])
    @login_required
    def api_update_wiki_entry(entry_id):
        entry = WikiEntry.query.get_or_404(entry_id)
        if entry.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
            
        data = request.json
        entry.title = data.get('title', entry.title)
        entry.content = data.get('content', entry.content)
        entry.category = data.get('category', entry.category)
        
        db.session.commit()
        
        # Return updated HTML for preview update
        html_content = markdown2.markdown(entry.content or "", extras=["fenced-code-blocks", "tables", "break-on-newline"])
        return jsonify({'message': 'Gespeichert', 'html': html_content})

    @app.route('/api/wiki/<int:entry_id>', methods=['DELETE'])
    @login_required
    def api_delete_wiki_entry(entry_id):
        entry = WikiEntry.query.get_or_404(entry_id)
        if entry.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
            
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Gelöscht'})

    @app.route('/api/settings/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def api_delete_user(user_id):
        if not current_user.is_admin:
            return jsonify({'error': 'Nicht autorisiert'}), 403
        
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'error': 'Du kannst dich nicht selbst löschen'}), 400
        
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Benutzer gelöscht'})

    @app.route('/api/settings/users/<int:user_id>/reset-password', methods=['POST'])
    @login_required
    def api_reset_user_password(user_id):
        if not current_user.is_admin:
            return jsonify({'error': 'Nicht autorisiert'}), 403
        
        user = User.query.get_or_404(user_id)
        data = request.json
        new_password = data.get('password')
        
        if not new_password or len(new_password) < 4:
            return jsonify({'error': 'Passwort zu kurz'}), 400
            
        user.set_password(new_password)
        db.session.commit()
        return jsonify({'message': f'Passwort für {user.username} zurückgesetzt'})

    @app.route('/api/shortlinks', methods=['POST'])
    @login_required
    def api_add_shortlink():
        data = request.json
        slug = data.get('slug', '').strip().lower()
        target = data.get('target', '').strip()

        if not slug or not target:
            return jsonify({'error': 'Slug und Ziel-URL sind erforderlich'}), 400
        
        # Simple validation: no slashes in slug
        if '/' in slug:
            return jsonify({'error': 'Slug darf keine Schrägstriche enthalten'}), 400

        # Check if slug exists
        existing = Shortlink.query.filter_by(slug=slug).first()
        if existing:
            return jsonify({'error': 'Dieser Slug ist bereits vergeben'}), 400

        new_link = Shortlink(slug=slug, target_url=target, user_id=current_user.id)
        db.session.add(new_link)
        db.session.commit()
        return jsonify({'message': 'Shortlink erstellt'})

    # Polls API
    @app.route('/api/polls', methods=['POST'])
    @login_required
    def api_create_poll():
        data = request.json
        title = data.get('title', '').strip()
        question = data.get('question', '').strip()
        options_text = data.get('options', [])
        allow_suggestions = data.get('allow_suggestions', False)
        anonymous_voting = data.get('anonymous_voting', False)

        if not title or not question or not options_text:
            return jsonify({'error': 'Titel, Frage und Optionen sind erforderlich'}), 400
        
        if len(options_text) < 2 and not allow_suggestions:
            return jsonify({'error': 'Mindestens zwei Optionen sind erforderlich (oder Vorschläge erlauben)'}), 400

        # Generate unique slug
        import string
        import random
        poll_slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        while Poll.query.filter_by(slug=poll_slug).first():
            poll_slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        poll = Poll(
            title=title, 
            question=question, 
            user_id=current_user.id, 
            slug=poll_slug,
            allow_suggestions=allow_suggestions,
            anonymous_voting=anonymous_voting
        )
        db.session.add(poll)
        db.session.flush() # Get poll ID

        for opt_text in options_text:
            if opt_text.strip():
                opt = PollOption(poll_id=poll.id, text=opt_text.strip())
                db.session.add(opt)
        
        db.session.commit()
        return jsonify({'message': 'Umfrage erstellt', 'slug': poll_slug})

    @app.route('/api/polls/<int:poll_id>', methods=['DELETE'])
    @login_required
    def api_delete_poll(poll_id):
        poll = Poll.query.get_or_404(poll_id)
        if poll.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
        
        db.session.delete(poll)
        db.session.commit()
        return jsonify({'message': 'Umfrage gelöscht'})

    @app.route('/poll/<slug>')
    def view_poll(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        return render_template('tools/poll_view.html', poll=poll)

    @app.route('/api/poll/<slug>/vote', methods=['POST'])
    def api_poll_vote(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        if not poll.is_active:
            return jsonify({'error': 'Diese Umfrage ist nicht mehr aktiv'}), 400
            
        data = request.json
        option_id = data.get('option_id')
        voter_name = data.get('name', '').strip()

        if not option_id or not voter_name:
            return jsonify({'error': 'Name und Option sind erforderlich'}), 400

        option = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first()
        if not option:
            return jsonify({'error': 'Ungültige Option'}), 400

        vote = PollVote(poll_option_id=option.id, voter_name=voter_name)
        db.session.add(vote)
        db.session.commit()

        return jsonify({'message': 'Stimme abgegeben'})

    @app.route('/api/poll/<slug>/results')
    def api_poll_results(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        
        results = []
        for opt in poll.options:
            results.append({
                'id': opt.id,
                'text': opt.text,
                'votes': len(opt.votes)
            })
        
        return jsonify({
            'title': poll.title,
            'question': poll.question,
            'results': results,
            'total_votes': sum(r['votes'] for r in results)
        })

    @app.route('/api/poll/<slug>/suggest', methods=['POST'])
    def api_poll_suggest(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        if not poll.is_active:
            return jsonify({'error': 'Diese Umfrage ist nicht mehr aktiv'}), 400
        if not poll.allow_suggestions:
            return jsonify({'error': 'Vorschläge sind für diese Umfrage nicht erlaubt'}), 403
            
        data = request.json
        suggestion_text = data.get('suggestion', '').strip()
        voter_name = data.get('name', '').strip()

        if not suggestion_text:
            return jsonify({'error': 'Vorschlag darf nicht leer sein'}), 400
        
        if not poll.anonymous_voting and not voter_name:
            return jsonify({'error': 'Name ist erforderlich'}), 400

        # Check if option already exists
        existing = PollOption.query.filter_by(poll_id=poll.id, text=suggestion_text).first()
        if existing:
            return jsonify({'error': 'Dieser Vorschlag existiert bereits'}), 400

        # Create new option
        new_opt = PollOption(poll_id=poll.id, text=suggestion_text)
        db.session.add(new_opt)
        db.session.flush()

        # Add initial vote 
        vote = PollVote(poll_option_id=new_opt.id, voter_name=voter_name or 'Anonym')
        db.session.add(vote)
        db.session.commit()

        return jsonify({'message': 'Vorschlag hinzugefügt', 'option_id': new_opt.id})

    # Word Cloud API
    @app.route('/api/word-clouds', methods=['POST'])
    @login_required
    def api_create_word_cloud():
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()

        if not title:
            return jsonify({'error': 'Titel ist erforderlich'}), 400

        # Generate unique slug
        import string
        import random
        slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        while WordCloud.query.filter_by(slug=slug).first():
            slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        cloud = WordCloud(title=title, description=description, user_id=current_user.id, slug=slug)
        db.session.add(cloud)
        db.session.commit()
        return jsonify({'message': 'Word Cloud erstellt', 'slug': slug})

    @app.route('/api/word-clouds/<int:cloud_id>', methods=['DELETE'])
    @login_required
    def api_delete_word_cloud(cloud_id):
        cloud = WordCloud.query.get_or_404(cloud_id)
        if cloud.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
        
        db.session.delete(cloud)
        db.session.commit()
        return jsonify({'message': 'Word Cloud gelöscht'})

    @app.route('/wordcloud/<slug>')
    def view_word_cloud(slug):
        cloud = WordCloud.query.filter_by(slug=slug).first_or_404()
        return render_template('tools/word_cloud_view.html', cloud=cloud)

    @app.route('/api/wordcloud/<slug>/submit', methods=['POST'])
    def api_word_cloud_submit(slug):
        cloud = WordCloud.query.filter_by(slug=slug).first_or_404()
        if not cloud.is_active:
            return jsonify({'error': 'Diese Word Cloud ist nicht mehr aktiv'}), 400
            
        data = request.json
        word = data.get('word', '').strip().lower()
        name = data.get('name', 'Anonym').strip()

        if not word:
            return jsonify({'error': 'Wort darf nicht leer sein'}), 400
        
        if len(word) > 30:
            return jsonify({'error': 'Wort ist zu lang'}), 400

        entry = WordCloudEntry(word_cloud_id=cloud.id, word=word, voter_name=name)
        db.session.add(entry)
        db.session.commit()

        return jsonify({'message': 'Wort hinzugefügt'})

    @app.route('/api/wordcloud/<slug>/data')
    def api_word_cloud_data(slug):
        cloud = WordCloud.query.filter_by(slug=slug).first_or_404()
        
        from sqlalchemy import func
        entries = db.session.query(
            WordCloudEntry.word, 
            func.count(WordCloudEntry.id).label('count')
        ).filter(WordCloudEntry.word_cloud_id == cloud.id).group_by(WordCloudEntry.word).all()
        
        return jsonify({
            'title': cloud.title,
            'description': cloud.description,
            'words': [{'text': e.word, 'size': e.count} for e in entries]
        })

    @app.route('/api/shortlinks/<int:link_id>', methods=['DELETE'])
    @login_required
    def api_delete_shortlink(link_id):
        link = Shortlink.query.get_or_404(link_id)
        if link.user_id != current_user.id:
            return jsonify({'error': 'Nicht autorisiert'}), 403
        
        db.session.delete(link)
        db.session.commit()
        return jsonify({'message': 'Shortlink gelöscht'})

    @app.route('/api/convert', methods=['POST'])
    @login_required
    def api_convert():
        if 'files' not in request.files:
            return jsonify({'error': 'Keine Dateien hochgeladen'}), 400
        
        files = request.files.getlist('files')
        target_format = request.form.get('targetFormat', 'pdf').lower()
        
        if not files:
            return jsonify({'error': 'Keine Dateien ausgewählt'}), 400

        output = io.BytesIO()
        
        try:
            # 1. Image & Document Unification to PDF
            if target_format == 'pdf':
                pdf_bytes = []
                for file in files:
                    filename = file.filename.lower()
                    file_data = file.read()
                    
                    if filename.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.heic')):
                        img = Image.open(io.BytesIO(file_data))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG')
                        pdf_bytes.append(img2pdf.convert(img_byte_arr.getvalue()))
                    elif filename.endswith('.svg'):
                        svg_pdf = cairosvg.svg2pdf(bytestring=file_data)
                        pdf_bytes.append(svg_pdf)
                    elif filename.endswith(('.md', '.txt')):
                        doc = fitz.open()
                        page = doc.new_page()
                        text = file_data.decode('utf-8', errors='ignore')
                        page.insert_text((50, 50), text)
                        pdf_bytes.append(doc.tobytes())
                        doc.close()
                    elif filename.endswith('.pdf'):
                        pdf_bytes.append(file_data)
                
                doc = fitz.open()
                for pb in pdf_bytes:
                    temp_doc = fitz.open("pdf", pb)
                    doc.insert_pdf(temp_doc)
                    temp_doc.close()
                
                output.write(doc.tobytes())
                doc.close()
                output.seek(0)
                return send_file(output, mimetype='application/pdf', as_attachment=True, download_name="converted.pdf")

            # 2. Image formats (PNG, JPG, WEBP)
            elif target_format in ['png', 'jpg', 'webp']:
                with zipfile.ZipFile(output, 'w') as zf:
                    for i, file in enumerate(files):
                        filename = file.filename.lower()
                        file_data = file.read()
                        
                        if filename.endswith('.pdf'):
                            pdf_doc = fitz.open("pdf", file_data)
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap()
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                img_byte_arr = io.BytesIO()
                                img.save(img_byte_arr, format=target_format.upper())
                                zf.writestr(f"file_{i}_page_{page_num}.{target_format}", img_byte_arr.getvalue())
                            pdf_doc.close()
                        elif filename.endswith('.svg'):
                            png_bytes = cairosvg.svg2png(bytestring=file_data)
                            img = Image.open(io.BytesIO(png_bytes))
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=target_format.upper())
                            zf.writestr(f"file_{i}.{target_format}", img_byte_arr.getvalue())
                        else:
                            img = Image.open(io.BytesIO(file_data))
                            if target_format in ['jpg', 'jpeg'] and img.mode != 'RGB':
                                img = img.convert('RGB')
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=target_format.upper())
                            zf.writestr(f"file_{i}.{target_format}", img_byte_arr.getvalue())
                
                output.seek(0)
                if len(files) == 1 and not files[0].filename.lower().endswith('.pdf'):
                    # Just send the single file instead of ZIP if possible
                    # But for simplicity, zip is fine for multi-task tool
                    pass
                return send_file(output, mimetype='application/zip', as_attachment=True, download_name="converted_images.zip")

            # 3. Document formats (DOCX, TXT)
            elif target_format in ['docx', 'txt']:
                with zipfile.ZipFile(output, 'w') as zf:
                    for i, file in enumerate(files):
                        filename = file.filename.lower()
                        file_data = file.read()
                        
                        if target_format == 'docx' and filename.endswith('.pdf'):
                            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf_in:
                                tf_in.write(file_data)
                                tf_in_path = tf_in.name
                            tf_out_path = tf_in_path.replace('.pdf', '.docx')
                            try:
                                cv = PDF2Docx(tf_in_path)
                                cv.convert(tf_out_path)
                                cv.close()
                                with open(tf_out_path, 'rb') as f:
                                    zf.writestr(f"file_{i}.docx", f.read())
                            finally:
                                if os.path.exists(tf_in_path): os.remove(tf_in_path)
                                if os.path.exists(tf_out_path): os.remove(tf_out_path)
                        elif target_format == 'txt':
                            if filename.endswith('.pdf'):
                                pdf_doc = fitz.open("pdf", file_data)
                                text = ""
                                for page in pdf_doc:
                                    text += page.get_text()
                                zf.writestr(f"file_{i}.txt", text.encode('utf-8'))
                                pdf_doc.close()
                            else:
                                zf.writestr(f"file_{i}.txt", file_data)
                output.seek(0)
                return send_file(output, mimetype='application/zip', as_attachment=True, download_name="converted_docs.zip")

            # 4. Media formats (Audio, Video)
            elif target_format in ['mp3', 'wav', 'ogg', 'mp4', 'mov']:
                with zipfile.ZipFile(output, 'w') as zf:
                    for i, file in enumerate(files):
                        filename = file.filename.lower()
                        file_data = file.read()
                        ext = os.path.splitext(filename)[1]
                        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf_in:
                            tf_in.write(file_data)
                            tf_in_path = tf_in.name
                        
                        tf_out_path = tf_in_path + f".{target_format}"
                        
                        try:
                            if target_format in ['mp3', 'wav', 'ogg']:
                                try:
                                    clip = mp.AudioFileClip(tf_in_path)
                                except:
                                    clip = mp.VideoFileClip(tf_in_path).audio
                                clip.write_audiofile(tf_out_path)
                                clip.close()
                            else:
                                clip = mp.VideoFileClip(tf_in_path)
                                clip.write_videofile(tf_out_path, codec="libx264")
                                clip.close()
                            
                            with open(tf_out_path, 'rb') as f:
                                zf.writestr(f"file_{i}.{target_format}", f.read())
                        finally:
                            if os.path.exists(tf_in_path): os.remove(tf_in_path)
                            if os.path.exists(tf_out_path): os.remove(tf_out_path)

                output.seek(0)
                return send_file(output, mimetype='application/zip', as_attachment=True, download_name="converted_media.zip")

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/<path:slug>')
    def catch_all_redirect(slug):
        # Check if the slug exists in our shortlinks
        link = Shortlink.query.filter_by(slug=slug.lower()).first()
        if link:
            return redirect(link.target_url)
        # If not found, you might want to show a 404 or redirect back to index
        return redirect(url_for('index'))

    return app

app = create_app()

def cleanup_job():
    with app.app_context():
        try:
            retention_conf = SystemConfig.query.filter_by(key='file_retention_minutes').first()
            if not retention_conf:
                return
            
            minutes = int(retention_conf.value)
            
            # If retention is 0 (Immediate), we still clean up files older than 5 mins to catch abandoned ones
            min_age_minutes = max(minutes, 5) if minutes == 0 else minutes
            
            cutoff_time = time.time() - (min_age_minutes * 60)
            
            temp_dir = tempfile.gettempdir()
            # Only delete L8teTools related files
            files = glob.glob(os.path.join(temp_dir, "l8te_*"))
            
            count = 0
            for f in files:
                try:
                    if os.path.getmtime(f) < cutoff_time:
                        os.remove(f)
                        count += 1
                except:
                    pass
            
            # Also clean local downloads dir
            download_dir = os.path.join(tempfile.gettempdir(), 'l8te_downloads')
            if os.path.exists(download_dir):
                for f in glob.glob(os.path.join(download_dir, "*")):
                    try:
                        if os.path.getmtime(f) < cutoff_time:
                            os.remove(f)
                            count += 1
                    except:
                        pass

            if count > 0:
                print(f"[Cleanup] Removed {count} old temporary files.")
                
        except Exception as e:
            print(f"[Cleanup] Error: {e}")

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_job, trigger="interval", minutes=60)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
