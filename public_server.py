"""
Public Download Server for L8teTools File Sharing.

This is a lightweight, standalone Flask server that ONLY serves shared file
downloads. It runs on a separate port/domain so that share links work without
Cloudflare Access authentication.

SECURITY:
- No login, no sessions, no cookies
- No access to tools, dashboards, static files, or any app features
- Only two functional routes: /s/<token> (preview) and /s/<token>/download
- All other routes return 404
- No directory listing, no file enumeration
- Tokens are validated as hex UUIDs before DB lookup
- File paths are validated to stay within the upload folder
- Security headers on every response
- No error details leaked to the client
"""

import os
import re
import tempfile
from flask import Flask, render_template, send_file, request, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

# Strict token format: 32-char hex (UUID without dashes)
TOKEN_PATTERN = re.compile(r'^[a-f0-9]{32}$')


# ── Models (minimal read/write mirror — only what's needed) ─────────────
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), nullable=True)


class SharedFile(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    expires_at = db.Column(db.DateTime, nullable=True)
    expiration_mode = db.Column(db.String(20), default='time')
    max_downloads = db.Column(db.Integer, default=-1)
    download_count = db.Column(db.Integer, default=0)
    first_accessed_at = db.Column(db.DateTime, nullable=True)
    access_window_hours = db.Column(db.Integer, default=4)

    user = db.relationship('User', backref=db.backref('shared_files', lazy=True))


# ── App factory ─────────────────────────────────────────────────────────
def create_public_app():
    app = Flask(__name__,
                template_folder='templates/public',
                static_folder=None)  # No static files served at all

    # Must match the main app's DB path
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'l8te_uploads')

    # No sessions/cookies needed on this server
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

    db.init_app(app)

    # ── Security headers on every response ───────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
            "font-src https://fonts.gstatic.com; "
            "script-src 'self' https://cdn.tailwindcss.com; "
            "img-src 'self'; "
            "connect-src 'none'; "
            "frame-ancestors 'none';"
        )
        # Prevent caching of download pages (tokens can expire)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    # ── Block all HTTP methods except GET ────────────────────────────
    @app.before_request
    def block_non_get():
        if request.method != 'GET':
            abort(405)

    # ── Helpers ──────────────────────────────────────────────────────
    def validate_token(token):
        """Validate token is a proper hex UUID. Prevents injection/fuzzing."""
        if not TOKEN_PATTERN.match(token):
            return None
        return token

    def validate_filepath(filepath):
        """Ensure file path is within the upload folder (no traversal)."""
        upload_folder = os.path.realpath(app.config['UPLOAD_FOLDER'])
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(upload_folder):
            return None
        return real_path

    def delete_shared_file(file_obj):
        try:
            if os.path.exists(file_obj.filepath):
                os.remove(file_obj.filepath)
        except Exception:
            pass
        db.session.delete(file_obj)
        db.session.commit()

    def check_expiration(f):
        """Returns an error tuple (message, status_code) if expired, else None."""
        if f.expires_at and datetime.now() > f.expires_at:
            delete_shared_file(f)
            return ("Dieser Link ist abgelaufen.", 410)
        if f.max_downloads != -1 and f.download_count >= f.max_downloads:
            delete_shared_file(f)
            return ("Download-Limit erreicht.", 410)
        return None

    def get_shared_file(token):
        """Validate token, look up file, check expiration. Returns (file, error_response)."""
        if not validate_token(token):
            return None, (render_template('download_404.html'), 404)

        f = SharedFile.query.get(token)
        if not f:
            return None, (render_template('download_404.html'), 404)

        # Validate file path hasn't been tampered with
        if not validate_filepath(f.filepath):
            return None, (render_template('download_404.html'), 404)

        expired = check_expiration(f)
        if expired:
            return None, (render_template('download_expired.html', message=expired[0]), expired[1])

        # Open mode: start timer on first view
        if f.expiration_mode == 'open':
            if not f.first_accessed_at:
                f.first_accessed_at = datetime.now()
                f.expires_at = datetime.now() + timedelta(hours=f.access_window_hours)
                db.session.commit()
            elif datetime.now() > f.expires_at:
                delete_shared_file(f)
                return None, (render_template('download_expired.html',
                                              message="Link nach dem Öffnen abgelaufen."), 410)

        return f, None

    # ── Routes (ONLY download-related) ───────────────────────────────
    @app.route('/s/<token>')
    def shared_file_view(token):
        f, error = get_shared_file(token)
        if error:
            return error

        # File size
        file_size_str = "Unbekannt"
        try:
            size_bytes = os.path.getsize(f.filepath)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024:
                    file_size_str = f"{size_bytes:.2f} {unit}"
                    break
                size_bytes /= 1024
        except Exception:
            pass

        return render_template('download_page.html', file=f, file_size_str=file_size_str)

    @app.route('/s/<token>/download')
    def shared_file_download(token):
        f, error = get_shared_file(token)
        if error:
            return error

        # Double-check file exists on disk
        if not os.path.isfile(f.filepath):
            delete_shared_file(f)
            return render_template('download_404.html'), 404

        f.download_count += 1
        db.session.commit()

        try:
            return send_file(f.filepath, as_attachment=True, download_name=f.filename)
        except Exception:
            return render_template('download_404.html'), 500

    # ── Landing page (no info leaked) ────────────────────────────────
    @app.route('/')
    def index():
        return render_template('download_landing.html')

    # ── Block everything else ────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('download_404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('download_404.html'), 405

    @app.errorhandler(500)
    def server_error(e):
        return render_template('download_404.html'), 500

    return app


app = create_public_app()

if __name__ == '__main__':
    port = int(os.environ.get('PUBLIC_SHARE_PORT', 5001))
    app.run(host='0.0.0.0', port=port)
