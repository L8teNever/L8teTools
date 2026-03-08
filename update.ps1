# Update Script für L8teTools Docker (Windows PowerShell)

Write-Host "🔄 Stoppe Container..." -ForegroundColor Cyan
docker-compose down

Write-Host "📥  Lade neuestes Image herunter..." -ForegroundColor Cyan
docker-compose pull

Write-Host "🚀 Starte Container..." -ForegroundColor Green
docker-compose up -d

Write-Host "`n✅ Update abgeschlossen!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Container Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "📝 Logs anzeigen mit: docker-compose logs -f" -ForegroundColor Yellow
