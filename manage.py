import sys
from app import app, db, User

def create_user(username, password):
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"Fehler: Benutzer '{username}' existiert bereits.")
            return

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"Benutzer '{username}' erfolgreich erstellt.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Verwendung: python manage.py <username> <password>")
    else:
        create_user(sys.argv[1], sys.argv[2])
