import os
import io
import zipfile
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import img2pdf
import fitz  # PyMuPDF

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    with app.app_context():
        db.create_all()

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
            if target_format == 'pdf':
                # Convert multiple images/PDFs to one single PDF
                pdf_bytes = []
                for file in files:
                    filename = file.filename.lower()
                    file_data = file.read()
                    
                    if filename.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff')):
                        # Convert Image to PDF bytes
                        img = Image.open(io.BytesIO(file_data))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG')
                        pdf_bytes.append(img2pdf.convert(img_byte_arr.getvalue()))
                    elif filename.endswith('.pdf'):
                        pdf_bytes.append(file_data)
                
                # Combine all PDF bytes into one
                doc = fitz.open()
                for pb in pdf_bytes:
                    temp_doc = fitz.open("pdf", pb)
                    doc.insert_pdf(temp_doc)
                    temp_doc.close()
                
                output.write(doc.tobytes())
                doc.close()
                output.seek(0)
                return send_file(output, mimetype='application/pdf', as_attachment=True, download_name="converted.pdf")

            elif target_format in ['png', 'jpg', 'webp']:
                # Convert files to images, return as ZIP if multiple
                with zipfile.ZipFile(output, 'w') as zf:
                    for i, file in enumerate(files):
                        filename = file.filename.lower()
                        file_data = file.read()
                        
                        if filename.endswith('.pdf'):
                            # Extract pages from PDF as images
                            pdf_doc = fitz.open("pdf", file_data)
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap()
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                img_byte_arr = io.BytesIO()
                                img.save(img_byte_arr, format=target_format.upper())
                                zf.writestr(f"file_{i}_page_{page_num}.{target_format}", img_byte_arr.getvalue())
                            pdf_doc.close()
                        else:
                            # Convert existing image
                            img = Image.open(io.BytesIO(file_data))
                            if target_format == 'jpg' and img.mode != 'RGB':
                                img = img.convert('RGB')
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=target_format.upper())
                            zf.writestr(f"file_{i}.{target_format}", img_byte_arr.getvalue())
                
                output.seek(0)
                return send_file(output, mimetype='application/zip', as_attachment=True, download_name="converted_images.zip")

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
