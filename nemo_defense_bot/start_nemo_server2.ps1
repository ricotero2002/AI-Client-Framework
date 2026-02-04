# Script to start NeMo Guardrails server
# Usage: .\start_nemo_server.ps1

# 1. Función para cargar variables de entorno (.env)
function Load-Env {
    param ([string]$Path)
    if (Test-Path $Path) {
        Write-Host "Loading .env from $Path" -ForegroundColor Green
        Get-Content $Path | ForEach-Object {
            if ($_ -match "^\s*(?:export\s+)?([^#=]+)\s*=\s*(.*)") {
                [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
            }
        }
        return $true
    }
    return $false
}

# 2. Cargar variables
$envLoaded = Load-Env -Path ".env"
if (-not $envLoaded) { $envLoaded = Load-Env -Path "..\.env" }

if (-not $env:NVIDIA_API_KEY) {
    Write-Warning "NVIDIA_API_KEY is not set. Required for NVIDIA NIM models."
}

if (-not $env:NVIDIA_API_KEY) {
    Write-Host "❌ NVIDIA_API_KEY no está en el entorno. Configurala primero:"
    Write-Host '   setx NVIDIA_API_KEY "tu_api_key_aqui"'
    exit 1
}

Write-Host "✅ NVIDIA_API_KEY encontrada en el entorno."

# ================================
# 2) Levantar servidor GLiNER
# ================================

Write-Host "🚀 Iniciando servidor GLiNER..."

Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "cd examples/deployment/gliner_server; gliner-server --host 0.0.0.0 --port 1235"

# Esperar unos segundos a que levante
Start-Sleep -Seconds 5

# ================================
# 3) Iniciar NeMo Guardrails
# ================================

Write-Host "🤖 Iniciando NeMo Guardrails (Puerto 8000)..."
Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "nemoguardrails server --config config --default-config-id config --port 8000"
