# Update Script für L8teTools Docker (Windows PowerShell)

Write-Host "🔄 Stoppe Container..." -ForegroundColor Cyan
docker-compose down

Write-Host "🗑️  Lösche altes Image..." -ForegroundColor Yellow
docker rmi l8tetools:latest 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Kein altes Image gefunden" -ForegroundColor Gray }

Write-Host "🔨 Baue neues Image (ohne Cache)..." -ForegroundColor Magenta
docker-compose build --no-cache

Write-Host "🚀 Starte Container..." -ForegroundColor Green
docker-compose up -d

Write-Host "`n✅ Update abgeschlossen!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Container Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "📝 Logs anzeigen mit: docker-compose logs -f" -ForegroundColor Yellow
