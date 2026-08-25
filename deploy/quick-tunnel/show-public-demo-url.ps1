param(
    [switch]$NoOpen,
    [switch]$NoPopup
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$composeFile = Join-Path $projectRoot "docker-compose.public-demo.yml"
$urlFile = Join-Path $projectRoot "PUBLIC-DEMO-URL.txt"
$projectName = "family-counseling-public-demo"
$composeArgs = @("compose", "-p", $projectName, "-f", $composeFile)

Set-Location -LiteralPath $projectRoot

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is not installed."
    }

    $logs = (& docker @composeArgs logs --no-color tunnel 2>&1) | Out-String
    $match = [regex]::Match($logs, "https://[a-z0-9-]+\.trycloudflare\.com")
    if (-not $match.Success) {
        throw "No running public demo URL was found. Run start-public-demo.cmd first."
    }

    $publicUrl = $match.Value
    Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding UTF8
    Set-Clipboard -Value $publicUrl
    if (-not $NoOpen) {
        Start-Process $publicUrl
    }

    if (-not $NoPopup) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "Public demo URL (already copied):`n`n$publicUrl",
            "Family Counseling Public Demo"
        ) | Out-Null
    }

    Write-Output $publicUrl
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
