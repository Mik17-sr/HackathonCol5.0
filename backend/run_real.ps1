Set-Location "C:\Mis documentos\ME\Universidad Distrital\Hackathon\HackathonCol5.0\backend"
& ".\.venv\Scripts\python.exe" test_real.py 2>&1 | ForEach-Object { "$_" }
