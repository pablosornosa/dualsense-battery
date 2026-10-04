# Genera dist\DualSenseBattery.exe (un unico exe: configurador + instalador + popup).
# Requisitos: Python 3.10+ en Windows.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name DualSenseBattery `
    --icon assets\icon.ico `
    --hidden-import hid `
    main.py

Write-Host "`nListo: dist\DualSenseBattery.exe"
