# Audio Scraper — extrator de texto de audios de videos

Baixa o audio de links de **Instagram, TikTok e YouTube/Shorts** (input em TXT ou CSV)
e transcreve tudo para texto com **faster-whisper**.

## Instalação (PowerShell)

```powershell
# 1. ffmpeg (obrigatorio para o yt-dlp converter para mp3)
winget install Gyan.FFmpeg
# fecha e reabre o PowerShell depois de instalar

# 2. ambiente Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

```powershell
# 1. poe os links num urls.txt (um por linha) ou num CSV qualquer
.\baixar.ps1 -InputFile urls.txt          # usa cookies do Chrome (preciso p/ Instagram)
.\baixar.ps1 -InputFile links.csv -SemCookies   # TikTok/YouTube publicos

# 2. transcrever
python transcrever.py                     # modelo small, pt
python transcrever.py --model medium      # mais preciso, mais lento
```

Resultados:

- `audios/<id>.mp3` + `audios/<id>.info.json` — audio e metadados
- `transcricoes/<id>.txt` — texto limpo
- `transcricoes/<id>.json` — segments (start/end/text) + metadados do video
- `baixados.txt` — historico do yt-dlp (nao re-baixa o que ja tem)

Audios ja transcritos (com `.txt` em `transcricoes/`) são ignorados; um ficheiro
corrompido não pára o lote.
