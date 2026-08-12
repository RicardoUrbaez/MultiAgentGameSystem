$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

function Test-CanBindPort {
    param([int]$Port)

    $listener = $null
    try {
        $address = [System.Net.IPAddress]::Parse("127.0.0.1")
        $listener = [System.Net.Sockets.TcpListener]::new($address, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

$port = 8010
foreach ($candidate in 8010..8020) {
    if (Test-CanBindPort -Port $candidate) {
        $port = $candidate
        break
    }
}

$url = "http://127.0.0.1:$port/"
Write-Host "Opening Agentic Game Lab at $url"
Start-Process $url
& $python -m uvicorn lab_app.main:app --host 127.0.0.1 --port $port
