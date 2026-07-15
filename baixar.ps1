# baixar.ps1 — extrai URLs (Instagram, TikTok, YouTube/Shorts) de um TXT ou CSV
# e baixa apenas o audio em MP3 via yt-dlp.
#
# Uso:
#   .\baixar.ps1 -InputFile urls.txt
#   .\baixar.ps1 -InputFile links.csv -Browser edge
#   .\baixar.ps1 -InputFile urls.txt -SemCookies          # sem cookies (TikTok/YouTube publicos)
#   .\baixar.ps1 -InputFile links.csv -CookiesFile cookies.txt   # cookies exportados (recomendado no Windows)

param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [string]$Browser = "chrome",

    [string]$CookiesFile,

    [switch]$SemCookies
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputFile)) {
    Write-Host "ERRO: ficheiro nao encontrado: $InputFile" -ForegroundColor Red
    exit 1
}

# --- 1. Extrair URLs por regex (funciona para TXT, CSV ou qualquer texto) ---
$conteudo = Get-Content $InputFile -Raw -Encoding UTF8

$padrao = 'https?://[^\s,;"''<>|]+'
$todas = [regex]::Matches($conteudo, $padrao) | ForEach-Object { $_.Value.TrimEnd('.', ')', ']') }

# Filtrar apenas URLs de posts/videos (exclui perfis, avatares, etc.)
$padroesPost = @(
    'instagram\.com/(reel|reels|p|tv)/'      # posts do Instagram
    'tiktok\.com/@[^/]+/video/'              # video do TikTok
    'tiktok\.com/(t|v)/'                     # links curtos TikTok
    'vm\.tiktok\.com/'                       # links partilhados TikTok
    'youtube\.com/(shorts/|watch\?)'         # Shorts e videos YouTube
    'youtu\.be/'                             # links curtos YouTube
) -join '|'

$suportadas = $todas | Where-Object { $_ -match $padroesPost } | Select-Object -Unique

if (-not $suportadas) {
    Write-Host "ERRO: nenhuma URL de Instagram/TikTok/YouTube encontrada em $InputFile" -ForegroundColor Red
    exit 1
}

Write-Host "Encontradas $($suportadas.Count) URLs unicas:" -ForegroundColor Cyan
$suportadas | ForEach-Object { Write-Host "  $_" }

# Lista limpa temporaria (UTF-8 sem BOM, senao o yt-dlp le a 1a URL com lixo)
$listaTemp = Join-Path $env:TEMP "ytdlp_urls_limpa.txt"
[System.IO.File]::WriteAllLines($listaTemp, $suportadas)

# --- 2. Baixar audio com yt-dlp ---
# Usa o yt-dlp do .venv do projeto se existir; senao tenta o do PATH
$ytdlp = Join-Path $PSScriptRoot ".venv\Scripts\yt-dlp.exe"
if (-not (Test-Path $ytdlp)) {
    $ytdlp = "yt-dlp"
    if (-not (Get-Command yt-dlp -ErrorAction SilentlyContinue)) {
        Write-Host "ERRO: yt-dlp nao encontrado. Corre: .\.venv\Scripts\pip install yt-dlp" -ForegroundColor Red
        exit 1
    }
}

New-Item -ItemType Directory -Force -Path "audios" | Out-Null

$ytArgs = @(
    "-a", $listaTemp,
    "-x", "--audio-format", "mp3",
    "--download-archive", "baixados.txt",
    "--restrict-filenames",
    "--ignore-errors",
    "--sleep-interval", "5",
    "--max-sleep-interval", "30",
    "-o", "audios/%(id)s.%(ext)s",
    "--write-info-json"
)

if ($CookiesFile) {
    if (-not (Test-Path $CookiesFile)) {
        Write-Host "ERRO: ficheiro de cookies nao encontrado: $CookiesFile" -ForegroundColor Red
        exit 1
    }
    $ytArgs += @("--cookies", $CookiesFile)
} elseif (-not $SemCookies) {
    $ytArgs += @("--cookies-from-browser", $Browser)
}

Write-Host "`nA iniciar downloads..." -ForegroundColor Cyan
& $ytdlp @ytArgs

Write-Host "`nConcluido. Audios em .\audios\ | historico em baixados.txt" -ForegroundColor Green
