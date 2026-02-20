# =============================================================================
# HRI Poker Experiment - Script di avvio (Windows PowerShell)
# =============================================================================
#
# UTILIZZO:
#   .\start.ps1                    -> Modalita' SIMULAZIONE (default)
#   .\start.ps1 -Mode simulate     -> Modalita' SIMULAZIONE
#   .\start.ps1 -Mode robot        -> Modalita' ROBOT (Choregraphe)
#   .\start.ps1 -Mode robot -NaoIp 192.168.1.100   -> Robot fisico su IP specifico
#
# =============================================================================

param(
    [ValidateSet("simulate", "robot")]
    [string]$Mode = "simulate",

    [string]$NaoIp = "127.0.0.1",
    [int]$NaoPort = 50683,

    # Path di Python 2.7 (necessario per il controller robot con qi SDK)
    [string]$Python27 = "C:\Python27\python.exe",

    # Path dell'SDK Choregraphe
    [string]$SdkPath = "C:\Program Files (x86)\Aldebaran Robotics\Choregraphe Suite 2.1\lib"
)

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   HRI POKER EXPERIMENT - Avvio Sistema"       -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# --- Directory del progetto ---
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

# --- Modalita' ---
if ($Mode -eq "simulate") {
    $env:SIMULATION_MODE = "true"
    Write-Host "  Modalita':  SIMULAZIONE (senza robot)" -ForegroundColor Yellow
} else {
    $env:SIMULATION_MODE = "false"
    Write-Host "  Modalita':  ROBOT (collegamento Choregraphe/NAO)" -ForegroundColor Green
}

$env:NAO_IP = $NaoIp
$env:NAO_PORT = $NaoPort.ToString()
$env:PYTHON_PATH = $Python27
$env:NAOQI_SDK_PATH = $SdkPath

Write-Host "  NAO IP:     ${NaoIp}:${NaoPort}"
Write-Host "  Python 2.7: $Python27"
Write-Host "  SDK Path:   $SdkPath"
Write-Host "  Directory:  $ProjectDir"
Write-Host ""

# --- Virtual environment ---
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$VenvActivate = Join-Path $ProjectDir ".venv\Scripts\Activate.ps1"

if (Test-Path $VenvPython) {
    & $VenvActivate
    Write-Host "[OK] Virtual environment attivato" -ForegroundColor Green
} else {
    Write-Host "[!] Virtual environment non trovato in .venv\" -ForegroundColor Yellow
    Write-Host "    Creo il venv e installo le dipendenze..."
    python -m venv "$ProjectDir\.venv"
    & $VenvActivate
}

# --- Verifica Python 2.7 (solo in modalita' robot) ---
if ($Mode -eq "robot") {
    if (Test-Path $Python27) {
        Write-Host "[OK] Python 2.7 trovato: $Python27" -ForegroundColor Green
        # Verifica modulo qi
        $qiCheck = & $Python27 -c "import sys; sys.path.insert(0, r'$SdkPath'); import qi; print('OK')" 2>&1
        if ($qiCheck -match "OK") {
            Write-Host "[OK] Modulo qi (NAOqi SDK) disponibile" -ForegroundColor Green
        } else {
            Write-Host "[!] ATTENZIONE: modulo qi non trovato in $SdkPath" -ForegroundColor Red
            Write-Host "    Assicurati che Choregraphe sia installato e il path sia corretto." -ForegroundColor Red
            Write-Host "    Il server partira' ma i comandi robot falliranno." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[!] ATTENZIONE: Python 2.7 non trovato in $Python27" -ForegroundColor Red
        Write-Host "    Il server partira' ma i comandi robot falliranno." -ForegroundColor Yellow
    }
}

# --- Verifica Flask ---
$flaskCheck = & $VenvPython -c "import flask; print(flask.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Flask non trovato. Installazione in corso..." -ForegroundColor Yellow
    & $VenvPython -m pip install flask
} else {
    Write-Host "[OK] Flask $flaskCheck" -ForegroundColor Green
}

# --- Crea cartella dati ---
$DataDir = Join-Path $ProjectDir "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

# --- Avvio ---
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   Avvio server Flask..."                       -ForegroundColor Cyan
Write-Host ""
Write-Host "   Interfacce:"
Write-Host "     Player:  http://localhost:5000/player"     -ForegroundColor White
Write-Host "     Robot:   http://localhost:5000/robot"      -ForegroundColor White
Write-Host "     Admin:   http://localhost:5000/admin"      -ForegroundColor White
Write-Host ""
if ($Mode -eq "robot") {
    Write-Host "   Assicurati che Choregraphe sia aperto"   -ForegroundColor Yellow
    Write-Host "   con un robot virtuale su ${NaoIp}:${NaoPort}" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "   Premi Ctrl+C per fermare il server"         -ForegroundColor DarkGray
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

& $VenvPython (Join-Path $ProjectDir "server.py")
