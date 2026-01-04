import os
import io
import zipfile
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import tempfile
from PIL import Image
import img2pdf
import fitz  # PyMuPDF
from pillow_heif import register_heif_opener
import cairosvg
from pdf2docx import Converter as PDF2Docx
import markdown2
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

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    with app.app_context():
        db.create_all()

        # SQLite Migration: Add is_admin column if it doesn't exist
        try:
            db.session.execute(db.text('ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
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
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Ungültiger Benutzername oder Passwort', 'error')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

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

    @app.route('/tools/shortlinks')
    @login_required
    def shortlinks():
        user_links = Shortlink.query.filter_by(user_id=current_user.id).order_by(Shortlink.created_at.desc()).all()
        domain = SystemConfig.query.filter_by(key='shortener_domain').first().value
        return render_template('tools/shortlinks.html', links=user_links, domain=domain)

    @app.route('/settings')
    @login_required
    def settings():
        domain = SystemConfig.query.filter_by(key='shortener_domain').first().value
        all_users = []
        if current_user.is_admin:
            all_users = User.query.all()
        
        version = "v.0.0.0"
        try:
            with open('version.txt', 'r') as f:
                version = f.read().strip()
        except:
            pass
            
        return render_template('settings.html', domain=domain, users=all_users, version=version)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
