#!/bin/bash
# Update Script für L8teTools Docker

echo "🔄 Stoppe Container..."
docker-compose down

echo "🗑️  Lösche altes Image..."
docker rmi l8tetools:latest 2>/dev/null || echo "Kein altes Image gefunden"

echo "🔨 Baue neues Image (ohne Cache)..."
docker-compose build --no-cache

echo "🚀 Starte Container..."
docker-compose up -d

echo "✅ Update abgeschlossen!"
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "📝 Logs anzeigen mit: docker-compose logs -f"
