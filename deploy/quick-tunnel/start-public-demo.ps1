$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$composeFile = Join-Path $projectRoot "docker-compose.public-demo.yml"
$urlFile = Join-Path $projectRoot "PUBLIC-DEMO-URL.txt"
$projectName = "family-counseling-public-demo"
$composeArgs = @("compose", "-p", $projectName, "-f", $composeFile)

Set-Location -LiteralPath $projectRoot

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is not installed. Install and start Docker Desktop first."
    }

    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running. Start Docker Desktop and run this file again."
    }

    $env:PUBLIC_DEMO_AUTH_SECRET = [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")

    Write-Host ""
    Write-Host "Building and starting the public demo. The first run can take several minutes." -ForegroundColor Cyan
    & docker @composeArgs up --build -d --remove-orphans
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start the demo."
    }

    $publicUrl = $null
    for ($attempt = 1; $attempt -le 90; $attempt++) {
        $logs = (& docker @composeArgs logs --no-color tunnel 2>&1) | Out-String
        $match = [regex]::Match($logs, "https://[a-z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            $publicUrl = $match.Value
            break
        }
        Start-Sleep -Seconds 2
    }

    if (-not $publicUrl) {
        & docker @composeArgs logs --no-color --tail 100
        throw "Cloudflare did not return a public URL."
    }

    Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding UTF8
    Set-Clipboard -Value $publicUrl
    Write-Host ""
    Write-Host "PUBLIC DEMO URL" -ForegroundColor Green
    Write-Host $publicUrl -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Share this URL while this window stays open." -ForegroundColor Green
    Write-Host "Closing the demo changes the URL next time." -ForegroundColor DarkYellow
    Write-Host "The URL was copied to the clipboard and saved to PUBLIC-DEMO-URL.txt." -ForegroundColor Cyan
    Write-Host ""

    Start-Process $publicUrl
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Public demo URL (already copied):`n`n$publicUrl`n`nKeep Docker Desktop and this window open.",
        "Family Counseling Public Demo"
    ) | Out-Null
    Read-Host "Press ENTER to stop the public demo"
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    Write-Host "Stopping the public demo..." -ForegroundColor DarkGray
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        & docker @composeArgs down 2>$null
    }
    Remove-Item -LiteralPath $urlFile -Force -ErrorAction SilentlyContinue
}
