# =============================================================================
# HRI Poker Experiment - Script di avvio (Windows PowerShell)
# =============================================================================
#
# La configurazione e' nel file .env (modifica quello per cambiare impostazioni)
#
# UTILIZZO:
#   .\start.ps1                -> Avvia il server (configurazione da .env)
#   .\start.ps1 -Verify        -> Esegue verify_system.py prima di avviare
#
# =============================================================================

param(
    [switch]$Verify
)

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   HRI POKER EXPERIMENT - Avvio Sistema"       -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# --- Directory del progetto ---
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

# --- Installazione dipendenze ---
# Workaround: pip di Python 2.7 non gestisce caratteri Unicode nel path
# Copiamo requirements.txt in %TEMP% per evitare il problema
$RequirementsPath = Join-Path $ProjectDir "requirements.txt"
if (Test-Path $RequirementsPath) {
    Write-Host "[*] Installazione dipendenze..." -ForegroundColor Yellow
    $TempReq = Join-Path $env:TEMP "hri_requirements.txt"
    Copy-Item $RequirementsPath $TempReq -Force
    & python -m pip install -r $TempReq --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Installazione dipendenze fallita, verifico se sono gia' presenti..." -ForegroundColor Yellow
        $flaskOk = & python -c "import flask" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Dipendenze gia' installate" -ForegroundColor Green
        } else {
            Write-Host "[!] ERRORE: Flask non trovato. Installa manualmente: pip install Flask" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[OK] Dipendenze installate" -ForegroundColor Green
    }
    Remove-Item $TempReq -ErrorAction SilentlyContinue -Force
}

# --- Crea cartella dati ---
$DataDir = Join-Path $ProjectDir "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

# --- Verifica .env ---
$envFile = Join-Path $ProjectDir ".env"
$envExample = Join-Path $ProjectDir ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Write-Host "[*] File .env non trovato, copio da .env.example..." -ForegroundColor Yellow
        Copy-Item $envExample $envFile
        Write-Host "[OK] File .env creato (modifica i valori secondo il tuo setup)" -ForegroundColor Green
    } else {
        Write-Host "[!] File .env e .env.example non trovati" -ForegroundColor Red
        Write-Host "    Verra' usata la configurazione di default." -ForegroundColor Yellow
    }
}

# --- Verifica (opzionale) ---
if ($Verify) {
    Write-Host ""
    Write-Host "[*] Verifica del sistema..." -ForegroundColor Yellow
    & python (Join-Path $ProjectDir "verify_system.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Verifica fallita" -ForegroundColor Red
        exit 1
    }
}

# --- Leggi modalita' dal .env ---
if (Test-Path $envFile) {
    $simMode = "SIMULAZIONE"
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^SIMULATION_MODE=(.+)$") {
            if ($Matches[1].Trim().ToLower() -eq "false") {
                $simMode = "ROBOT"
            }
        }
    }
    Write-Host "  Modalita':  $simMode" -ForegroundColor Yellow
    Write-Host "  Config:     .env" -ForegroundColor DarkGray
} else {
    Write-Host "  Modalita':  SIMULAZIONE (default)" -ForegroundColor Yellow
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
Write-Host "   Premi Ctrl+C per fermare il server"         -ForegroundColor DarkGray
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

& python (Join-Path $ProjectDir "server.py")
