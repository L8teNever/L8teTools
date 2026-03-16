"""
Public Download Server for L8teTools File Sharing.

This is a lightweight, standalone Flask server that ONLY serves shared file
downloads. It runs on a separate port/domain so that share links work without
Cloudflare Access authentication.

It has NO access to tools, dashboards, or any authenticated features.
"""

import os
import tempfile
from flask import Flask, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()


# ── Models (read-only mirror of main app models) ────────────────────────
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
    app = Flask(__name__, template_folder='templates/public')
    # Must match the main app's DB path (Flask resolves sqlite:///users.db to instance/users.db)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'l8te_uploads')

    db.init_app(app)

    # ── Helper ──────────────────────────────────────────────────────
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

    # ── Routes (ONLY download-related) ──────────────────────────────
    @app.route('/s/<token>')
    def shared_file_view(token):
        f = SharedFile.query.get(token)
        if not f:
            return render_template('download_404.html'), 404

        expired = check_expiration(f)
        if expired:
            return render_template('download_expired.html', message=expired[0]), expired[1]

        # Open mode: start timer on first view
        if f.expiration_mode == 'open':
            if not f.first_accessed_at:
                f.first_accessed_at = datetime.now()
                f.expires_at = datetime.now() + timedelta(hours=f.access_window_hours)
                db.session.commit()
            elif datetime.now() > f.expires_at:
                delete_shared_file(f)
                return render_template('download_expired.html',
                                       message="Link nach dem Öffnen abgelaufen."), 410

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
        f = SharedFile.query.get(token)
        if not f:
            return render_template('download_404.html'), 404

        expired = check_expiration(f)
        if expired:
            return render_template('download_expired.html', message=expired[0]), expired[1]

        f.download_count += 1
        db.session.commit()

        try:
            return send_file(f.filepath, as_attachment=True, download_name=f.filename)
        except Exception as e:
            return str(e), 500

    # Block everything else
    @app.route('/')
    def index():
        return render_template('download_landing.html')

    @app.errorhandler(404)
    def not_found(e):
        return render_template('download_404.html'), 404

    return app


app = create_public_app()

if __name__ == '__main__':
    port = int(os.environ.get('PUBLIC_SHARE_PORT', 5001))
    app.run(host='0.0.0.0', port=port)
