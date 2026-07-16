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

## Cookies (necessario para Instagram)

O Instagram exige sessão autenticada para baixar a maioria dos reels/posts. O
yt-dlp suporta dois jeitos de fornecer isso — **nunca partilhes nem faças
commit do teu ficheiro de cookies**, ele equivale à tua password:

**Opção A — direto do browser (mais simples)**
Faz login no Instagram no Chrome ou Edge normalmente e usa `-Browser`:

```powershell
.\baixar.ps1 -InputFile urls.txt -Browser chrome
```

O yt-dlp lê a sessão ativa do browser a cada execução; não gera nenhum
ficheiro no disco.

**Opção B — exportar cookies.txt (recomendado no Windows, mais estável)**
1. Instala a extensão [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   no Chrome/Edge.
2. Faz login no `instagram.com`, abre a extensão e exporta os cookies desse
   site em formato Netscape.
3. Guarda o ficheiro exportado como `cookies.txt` na raiz do projeto.
4. Usa:

```powershell
.\baixar.ps1 -InputFile urls.txt -CookiesFile cookies.txt
```

O `cookies.txt` já está no `.gitignore` — nunca vai ser versionado. Se este
ficheiro alguma vez for exposto (commit acidental, partilha, etc.), a sessão
fica comprometida: faz logout de todas as sessões nas definições de
segurança do Instagram (Definições → Segurança → Onde entraste com a sessão
→ Terminar sessão em todos os dispositivos) e volta a fazer login para
gerar cookies novos.

Sem cookies, só funcionam conteúdos públicos e o TikTok/YouTube:

```powershell
.\baixar.ps1 -InputFile links.csv -SemCookies
```

## Execução

### Opção 1 — interface web (mais fácil)

```powershell
python app.py
```

ou dá duplo clique em `Iniciar App.bat`. Abre automaticamente em
`http://127.0.0.1:7860` — cola os links (ou sobe um TXT/CSV), escolhe o
modelo de transcrição e clica em "Baixar e transcrever". Há também um separador
para ler as transcrições já geradas.

### Opção 2 — linha de comando

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

Nenhum destes ficheiros gerados (`audios/`, `transcricoes/`, `cookies.txt`,
`links.csv`, `baixados.txt`) é versionado — veja `.gitignore`.
