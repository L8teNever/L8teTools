#!/bin/bash
# Update Script für L8teTools Docker

echo "🔄 Stoppe Container..."
docker-compose down

echo "📥  Lade neuestes Image herunter..."
docker-compose pull

echo "🚀 Starte Container..."
docker-compose up -d

echo "✅ Update abgeschlossen!"
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "📝 Logs anzeigen mit: docker-compose logs -f"
