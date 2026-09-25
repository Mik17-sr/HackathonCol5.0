Set-Location "C:\Mis documentos\ME\Universidad Distrital\Hackathon\HackathonCol5.0\backend"
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v --tb=short 2>&1 | ForEach-Object { "$_" }
