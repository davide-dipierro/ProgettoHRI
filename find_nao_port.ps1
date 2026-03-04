<#
.SYNOPSIS
Trova la porta TCP su cui NAO/NAOqi (avviato da Choregraphe) è in ascolto.

.DESCRIPTION
Choregraphe può avviare NAOqi su una porta random. Questo script:
1) cerca processi rilevanti (naoqi, qilaunch, choregraphe)
2) mappa i PID alle connessioni TCP in stato LISTEN
3) mostra le porte candidate (e la più probabile)
4) opzionalmente aggiorna NAO_PORT nel file .env

.USAGE
  .\find_nao_port.ps1
  .\find_nao_port.ps1 -Ip 127.0.0.1
  .\find_nao_port.ps1 -UpdateEnv
  .\find_nao_port.ps1 -UpdateEnv -EnvPath ".\.env"
#>

[CmdletBinding()]
param(
    [string]$Ip = "127.0.0.1",
    [switch]$UpdateEnv,
    [string]$EnvPath = (Join-Path $PSScriptRoot ".env"),
    [int]$Top = 12,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-NaoProcesses {
    $nameRegex = '(?i)(naoqi|qilaunch|choregraphe)'
    $cmdRegex  = '(?i)(naoqi|qilaunch|choregraphe|aldebaran|softbank robotics)'

    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match $nameRegex -or ($_.CommandLine -and $_.CommandLine -match $cmdRegex)
        } |
        Select-Object ProcessId, Name, CommandLine
}

function Get-ListeningTcpConnections {
    try {
        return Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
    }
    catch {
        # Fallback (ambienti dove Get-NetTCPConnection non è disponibile/consentito)
        $rows = @()
        $lines = netstat -ano -p tcp | Select-String "LISTENING"
        foreach ($line in $lines) {
            if ($line.Line -match '^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$') {
                $rows += [PSCustomObject]@{
                    LocalAddress  = $Matches[1]
                    LocalPort     = [int]$Matches[2]
                    OwningProcess = [int]$Matches[3]
                }
            }
        }
        return $rows
    }
}

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if (-not (Test-Path $Path)) {
        "${Key}=${Value}" | Set-Content -Path $Path -Encoding UTF8
        return
    }

    $content = Get-Content -Path $Path
    $pattern = "^\s*${Key}\s*=.*$"

    if ($content -match $pattern) {
        $updated = $content | ForEach-Object {
            if ($_ -match $pattern) { "${Key}=${Value}" } else { $_ }
        }
        $updated | Set-Content -Path $Path -Encoding UTF8
    }
    else {
        $content + "${Key}=${Value}" | Set-Content -Path $Path -Encoding UTF8
    }
}

$naoProcesses = Get-NaoProcesses
if (-not $naoProcesses -or $naoProcesses.Count -eq 0) {
    Write-Warning "Nessun processo NAO/Choregraphe trovato. Avvia Choregraphe (o NAOqi) e riprova."
    exit 1
}

$pidSet = $naoProcesses.ProcessId
$allListening = Get-ListeningTcpConnections

# Filtra connessioni appartenenti ai PID NAO/Choregraphe
$candidates = $allListening | Where-Object { $_.OwningProcess -in $pidSet }

if ($Ip) {
    $ipRegex = [Regex]::Escape($Ip)
    $candidates = $candidates | Where-Object {
        $_.LocalAddress -match "^$ipRegex$|^0\.0\.0\.0$|^::$|^\[::\]$|^::$"
    }
}

if (-not $candidates -or $candidates.Count -eq 0) {
    Write-Warning "Trovati processi NAO/Choregraphe ma nessuna porta TCP in LISTEN associata."
    exit 2
}

# Unisci info processo + connessione
$result = foreach ($conn in $candidates) {
    $proc = $naoProcesses | Where-Object { $_.ProcessId -eq $conn.OwningProcess } | Select-Object -First 1

    # euristica punteggio: preferisci NAOqi vero (naoqi-bin / naoqi-service)
    $score = 0
    $role = "other"
    if ($proc.Name -match '(?i)naoqi-bin\.exe|naoqi-service\.exe|naoqi\.exe') {
        $score += 220
        $role = "naoqi"
    }
    elseif ($proc.Name -match '(?i)qi-secure-gateway\.exe') {
        $score += 80
        $role = "gateway"
    }
    elseif ($proc.Name -match '(?i)choregraphe-bin\.exe') {
        $score += 40
        $role = "choregraphe"
    }

    if ($conn.LocalPort -eq 9559) { $score += 20 }
    if ($conn.LocalPort -ge 1024) { $score += 10 }
    if ($proc.CommandLine -and $proc.CommandLine -match '(?i)--port\s+\d+') { $score += 20 }

    [PSCustomObject]@{
        Score       = $score
        Role        = $role
        LocalIp     = $conn.LocalAddress
        Port        = [int]$conn.LocalPort
        PID         = [int]$conn.OwningProcess
        ProcessName = $proc.Name
        CommandLine = $proc.CommandLine
    }
}

$ordered = $result | Sort-Object -Property Score, Port -Descending

# Se esiste almeno una porta di ruolo NAOqi, scegli tra quelle
$naoqiOnly = $ordered | Where-Object { $_.Role -eq "naoqi" }
if ($naoqiOnly -and $naoqiOnly.Count -gt 0) {
    $best = $naoqiOnly | Select-Object -First 1
}
else {
    $best = $ordered | Select-Object -First 1
}

if ($Json) {
    $ordered | Select-Object -First $Top | ConvertTo-Json -Depth 4
}
else {
    Write-Host ""
    Write-Host "Porte candidate NAO/Choregraphe:" -ForegroundColor Cyan
    $ordered |
        Select-Object -First $Top Port, LocalIp, PID, ProcessName, Role, Score |
        Format-Table -AutoSize

    Write-Host "Porta più probabile: $($best.Port)" -ForegroundColor Green
}

if ($UpdateEnv) {
    Set-DotEnvValue -Path $EnvPath -Key "NAO_PORT" -Value ([string]$best.Port)
    Write-Host "Aggiornato NAO_PORT=$($best.Port) in '$EnvPath'" -ForegroundColor Yellow
}

exit 0
