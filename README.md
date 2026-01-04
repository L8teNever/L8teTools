# 🛠️ L8teTools

L8teTools ist eine moderne Web-Anwendung, die verschiedene hilfreiche Tools unter einer Oberfläche vereint. Das Design ist stark an **Android 16 / Material Design 3** angelehnt und bietet eine intuitive, dunkle Benutzeroberfläche.

## ✨ Features

- **Sicheres Login-System**: Zugriff nur für autorisierte Benutzer.
- **Modernes Design**: Clean, futuristisch und responsiv.
- **Passwort Generator**: Erstelle hochsichere Passwörter mit individuellen Kriterien.
- **Erweiterbar**: Einfaches Hinzufügen weiterer Tools.
- **Docker Ready**: Vollständig containerisiert für einfaches Deployment.

---

## 🚀 Deployment mit Docker / Dockge

Hier ist die passende `docker-compose.yml` für dein Setup (z.B. in Dockge):

```yaml
version: '3.8'

services:
  l8tetools:
    image: l8tenever/l8tetools:latest
    container_name: l8tetools
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=dein_geheimer_schlüssel_hier
    restart: unless-stopped
    volumes:
      - l8te_data:/app/instance

volumes:
  l8te_data:
```

---

## 🛠️ Installation & lokales Setup

Falls du das Projekt lokal ohne Docker weiterentwickeln möchtest:

1. **Repository klonen**
   ```powershell
   git clone https://github.com/l8tenever/L8teTools.git
   cd L8teTools
   ```

2. **Abhängigkeiten installieren**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Benutzer erstellen**
   Da es keine öffentliche Registrierung gibt, muss der erste Account per Befehl erstellt werden:
   ```powershell
   python manage.py <benutzername> <passwort>
   ```

4. **Server starten**
   ```powershell
   python app.py
   ```
   Die App ist dann unter `http://localhost:5000` erreichbar.

---

## 📦 CI/CD

Das Projekt nutzt **GitHub Actions**, um bei jedem Push in den `main` Branch automatisch ein neues Docker-Image auf Docker Hub zu bauen und zu pushen.

- **Username:** l8tenever
- **Repository:** l8tetools

---

## 📝 Lizenz

Dieses Projekt wurde von Simon erstellt. Alle Rechte vorbehalten.
