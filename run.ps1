Write-Host ""
Write-Host "  Web:      http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

Start-Job -ScriptBlock { Start-Sleep 4; Start-Process "http://localhost:8000" } | Out-Null

.venv\Scripts\uvicorn backend.api:app --host 127.0.0.1 --port 8000
