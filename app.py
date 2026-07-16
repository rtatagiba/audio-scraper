"""
app.py — interface web local para baixar e transcrever audios de
Instagram / TikTok / YouTube Shorts.

Uso:  duplo clique em "Iniciar App.bat"  (ou: python app.py)
Abre automaticamente no browser em http://127.0.0.1:7860
"""

import re
import subprocess
import sys
from pathlib import Path

import gradio as gr

BASE = Path(__file__).parent
PASTA_AUDIOS = BASE / "audios"
PASTA_TRANSCRICOES = BASE / "transcricoes"
COOKIES_DEFAULT = BASE / "cookies.txt"
COOKIES_DOC_URL = "https://github.com/rtatagiba/audio-scraper#cookies-necessario-para-instagram"

PADRAO_URL = re.compile(r'https?://[^\s,;"\'<>|]+')
PADROES_POST = re.compile(
    r'instagram\.com/(reel|reels|p|tv)/'
    r'|tiktok\.com/@[^/]+/video/'
    r'|tiktok\.com/(t|v)/'
    r'|vm\.tiktok\.com/'
    r'|youtube\.com/(shorts/|watch\?)'
    r'|youtu\.be/'
)

# --- Traducoes da interface (labels estaticos) ---
TEXTOS = {
    "pt": dict(
        titulo="# 🎙️ Audio Scraper\nBaixa o audio de Instagram / TikTok / Shorts e transcreve para texto.",
        aviso_cookies=(
            "⚠️ **Para baixar do Instagram é preciso estar autenticado.** Veja como "
            "configurar os cookies com segurança — e por que nunca deves partilhar "
            f"esse ficheiro — no [README do projeto]({COOKIES_DOC_URL})."
        ),
        idioma_label="Idioma",
        tab_baixar="Baixar e transcrever",
        links_label="Cola aqui os links (um por linha, ou texto com links pelo meio)",
        links_placeholder="https://www.instagram.com/reel/...\nhttps://www.tiktok.com/@user/video/...\nhttps://www.youtube.com/shorts/...",
        ficheiro_label="...ou sobe um TXT / CSV com os links",
        modelo_label="Modelo de transcricao",
        modelo_info="small = bom equilibrio; medium = mais preciso e mais lento",
        usar_cookies_label="Usar cookies.txt (necessario para Instagram)",
        so_transcrever_label="So transcrever (nao baixar nada novo)",
        botao_label="▶ Baixar e transcrever",
        saida_label="Progresso",
        tab_ver="Ver transcricoes",
        escolha_label="Transcricao",
        atualizar_label="🔄 Atualizar lista",
        texto_t_label="Texto",
    ),
    "en": dict(
        titulo="# 🎙️ Audio Scraper\nDownloads audio from Instagram / TikTok / Shorts and transcribes it to text.",
        aviso_cookies=(
            "⚠️ **Downloading from Instagram requires an authenticated session.** "
            "See how to set up cookies safely — and why you should never share "
            f"that file — in the [project README]({COOKIES_DOC_URL})."
        ),
        idioma_label="Language",
        tab_baixar="Download & transcribe",
        links_label="Paste the links here (one per line, or text with links mixed in)",
        links_placeholder="https://www.instagram.com/reel/...\nhttps://www.tiktok.com/@user/video/...\nhttps://www.youtube.com/shorts/...",
        ficheiro_label="...or upload a TXT / CSV with the links",
        modelo_label="Transcription model",
        modelo_info="small = good balance; medium = more accurate and slower",
        usar_cookies_label="Use cookies.txt (required for Instagram)",
        so_transcrever_label="Transcribe only (don't download anything new)",
        botao_label="▶ Download & transcribe",
        saida_label="Progress",
        tab_ver="View transcripts",
        escolha_label="Transcript",
        atualizar_label="🔄 Refresh list",
        texto_t_label="Text",
    ),
    "es": dict(
        titulo="# 🎙️ Audio Scraper\nDescarga el audio de Instagram / TikTok / Shorts y lo transcribe a texto.",
        aviso_cookies=(
            "⚠️ **Para descargar de Instagram es necesario estar autenticado.** Mira "
            "cómo configurar las cookies de forma segura — y por qué nunca debes "
            f"compartir ese archivo — en el [README del proyecto]({COOKIES_DOC_URL})."
        ),
        idioma_label="Idioma",
        tab_baixar="Descargar y transcribir",
        links_label="Pega aquí los enlaces (uno por línea, o texto con enlaces mezclados)",
        links_placeholder="https://www.instagram.com/reel/...\nhttps://www.tiktok.com/@user/video/...\nhttps://www.youtube.com/shorts/...",
        ficheiro_label="...o sube un TXT / CSV con los enlaces",
        modelo_label="Modelo de transcripción",
        modelo_info="small = buen equilibrio; medium = más preciso y más lento",
        usar_cookies_label="Usar cookies.txt (necesario para Instagram)",
        so_transcrever_label="Solo transcribir (no descargar nada nuevo)",
        botao_label="▶ Descargar y transcribir",
        saida_label="Progreso",
        tab_ver="Ver transcripciones",
        escolha_label="Transcripción",
        atualizar_label="🔄 Actualizar lista",
        texto_t_label="Texto",
    ),
}

# --- Traducoes das mensagens de progresso emitidas durante o processamento ---
# (o output bruto do yt-dlp / faster-whisper nao e traduzido, so as mensagens proprias)
MSGS = {
    "pt": dict(
        erro_ficheiro="ERRO ao ler o ficheiro subido: {e}",
        nenhum_link=(
            "Nenhum link de post/video encontrado.\n"
            "Aceites: instagram.com/reel|p/..., tiktok.com/@user/video/..., "
            "youtube.com/shorts/..., youtu.be/..."
        ),
        links_encontrados=">> {n} links encontrados:",
        aviso_sem_cookies="AVISO: cookies.txt nao encontrado na pasta do projeto — a continuar sem cookies.",
        a_baixar=">> A baixar audios...",
        sem_video="   (post sem video — provavelmente so fotos, ignorado)",
        a_transcrever=">> A transcrever com o modelo '{modelo}' (a 1a vez descarrega o modelo, e demora)...",
        concluido=">> Concluido! {n} transcricoes novas nesta sessao (de {total} no total em {pasta})",
    ),
    "en": dict(
        erro_ficheiro="ERROR reading uploaded file: {e}",
        nenhum_link=(
            "No post/video link found.\n"
            "Accepted: instagram.com/reel|p/..., tiktok.com/@user/video/..., "
            "youtube.com/shorts/..., youtu.be/..."
        ),
        links_encontrados=">> {n} links found:",
        aviso_sem_cookies="WARNING: cookies.txt not found in the project folder — continuing without cookies.",
        a_baixar=">> Downloading audio...",
        sem_video="   (post has no video — likely photos only, skipped)",
        a_transcrever=">> Transcribing with model '{modelo}' (first run downloads the model, it takes a while)...",
        concluido=">> Done! {n} new transcripts this session (of {total} total in {pasta})",
    ),
    "es": dict(
        erro_ficheiro="ERROR al leer el archivo subido: {e}",
        nenhum_link=(
            "No se encontró ningún enlace de post/video.\n"
            "Aceptados: instagram.com/reel|p/..., tiktok.com/@user/video/..., "
            "youtube.com/shorts/..., youtu.be/..."
        ),
        links_encontrados=">> {n} enlaces encontrados:",
        aviso_sem_cookies="AVISO: no se encontró cookies.txt en la carpeta del proyecto — continuando sin cookies.",
        a_baixar=">> Descargando audio...",
        sem_video="   (post sin video — probablemente solo fotos, omitido)",
        a_transcrever=">> Transcribiendo con el modelo '{modelo}' (la primera vez descarga el modelo, tarda un poco)...",
        concluido=">> ¡Listo! {n} transcripciones nuevas en esta sesión (de {total} en total en {pasta})",
    ),
}


def extrair_urls(texto: str) -> list[str]:
    """Extrai URLs de posts/videos suportados, sem duplicados, mantendo a ordem."""
    urls = []
    for m in PADRAO_URL.finditer(texto or ""):
        url = m.group(0).rstrip('.)]')
        if PADROES_POST.search(url) and url not in urls:
            urls.append(url)
    return urls


def _correr(comando: list[str]):
    """Corre um comando e vai devolvendo as linhas de output."""
    proc = subprocess.Popen(
        comando,
        cwd=BASE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    for linha in proc.stdout:
        yield linha.rstrip()
    proc.wait()
    yield f"(processo terminou com codigo {proc.returncode})"


def processar(links_texto, ficheiro, modelo, usar_cookies, so_transcrever, idioma):
    m = MSGS.get(idioma, MSGS["pt"])
    log: list[str] = []

    def emitir(linha=""):
        log.append(linha)
        return "\n".join(log[-400:])  # limita o tamanho mostrado

    # snapshot de antes, para so reportar no fim o que foi feito NESTA sessao
    antes = set(PASTA_TRANSCRICOES.glob("*.txt")) if PASTA_TRANSCRICOES.is_dir() else set()

    if not so_transcrever:
        # --- 1. Juntar texto colado + ficheiro subido ---
        texto = links_texto or ""
        if ficheiro:
            try:
                texto += "\n" + Path(ficheiro).read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                yield emitir(m["erro_ficheiro"].format(e=e))
                return

        urls = extrair_urls(texto)
        if not urls:
            yield emitir(m["nenhum_link"])
            return

        yield emitir(m["links_encontrados"].format(n=len(urls)))
        for u in urls:
            yield emitir(f"   {u}")

        lista = BASE / "_urls_temp.txt"
        lista.write_text("\n".join(urls), encoding="utf-8")

        # --- 2. Baixar com yt-dlp ---
        comando = [
            sys.executable, "-m", "yt_dlp",
            "-a", str(lista),
            "-x", "--audio-format", "mp3",
            "--download-archive", "baixados.txt",
            "--restrict-filenames",
            "--ignore-errors",
            "--sleep-interval", "5",
            "-o", "audios/%(id)s.%(ext)s",
            "--write-info-json",
        ]
        if usar_cookies and COOKIES_DEFAULT.exists():
            comando += ["--cookies", str(COOKIES_DEFAULT)]
        elif usar_cookies:
            yield emitir(m["aviso_sem_cookies"])

        yield emitir()
        yield emitir(m["a_baixar"])
        for linha in _correr(comando):
            if "No video formats found" in linha:
                yield emitir(m["sem_video"])
            else:
                yield emitir(f"   {linha}")

    # --- 3. Transcrever ---
    yield emitir()
    yield emitir(m["a_transcrever"].format(modelo=modelo))
    comando_t = [sys.executable, "-u", str(BASE / "transcrever.py"), "--model", modelo]
    for linha in _correr(comando_t):
        yield emitir(f"   {linha}")

    # --- 4. Resumo final: so as transcricoes novas nesta sessao ---
    yield emitir()
    depois = set(PASTA_TRANSCRICOES.glob("*.txt")) if PASTA_TRANSCRICOES.is_dir() else set()
    novos = sorted(depois - antes, key=lambda p: p.name)
    yield emitir(m["concluido"].format(n=len(novos), total=len(depois), pasta=PASTA_TRANSCRICOES))
    for t in novos:
        yield emitir(f"   {t.name}")


def listar_transcricoes():
    if not PASTA_TRANSCRICOES.is_dir():
        return gr.update(choices=[], value=None)
    nomes = [t.name for t in sorted(PASTA_TRANSCRICOES.glob("*.txt"))]
    return gr.update(choices=nomes, value=nomes[0] if nomes else None)


def ler_transcricao(nome):
    if not nome:
        return ""
    caminho = PASTA_TRANSCRICOES / nome
    if not caminho.exists():
        return "(ficheiro nao encontrado)"
    return caminho.read_text(encoding="utf-8", errors="replace")


def mudar_idioma(idioma):
    t = TEXTOS.get(idioma, TEXTOS["pt"])
    return (
        gr.update(value=t["titulo"]),
        gr.update(value=t["aviso_cookies"]),
        gr.update(label=t["tab_baixar"]),
        gr.update(label=t["links_label"], placeholder=t["links_placeholder"]),
        gr.update(label=t["ficheiro_label"]),
        gr.update(label=t["modelo_label"], info=t["modelo_info"]),
        gr.update(label=t["usar_cookies_label"]),
        gr.update(label=t["so_transcrever_label"]),
        gr.update(value=t["botao_label"]),
        gr.update(label=t["saida_label"]),
        gr.update(label=t["tab_ver"]),
        gr.update(label=t["escolha_label"]),
        gr.update(value=t["atualizar_label"]),
        gr.update(label=t["texto_t_label"]),
    )


with gr.Blocks(title="Audio Scraper") as demo:
    t0 = TEXTOS["pt"]

    with gr.Row():
        with gr.Column(scale=4):
            titulo_md = gr.Markdown(t0["titulo"])
        with gr.Column(scale=1, min_width=160):
            idioma = gr.Radio(
                choices=["pt", "en", "es"],
                value="pt",
                label=t0["idioma_label"],
            )

    aviso_md = gr.Markdown(t0["aviso_cookies"])

    with gr.Tab(t0["tab_baixar"]) as tab_baixar:
        with gr.Row():
            with gr.Column():
                links = gr.Textbox(
                    label=t0["links_label"],
                    lines=8,
                    placeholder=t0["links_placeholder"],
                )
                ficheiro = gr.File(
                    label=t0["ficheiro_label"],
                    file_types=[".txt", ".csv"],
                    type="filepath",
                )
                with gr.Row():
                    modelo = gr.Dropdown(
                        ["tiny", "base", "small", "medium", "large-v3"],
                        value="small",
                        label=t0["modelo_label"],
                        info=t0["modelo_info"],
                    )
                with gr.Row():
                    usar_cookies = gr.Checkbox(
                        value=COOKIES_DEFAULT.exists(),
                        label=t0["usar_cookies_label"],
                    )
                    so_transcrever = gr.Checkbox(
                        value=False,
                        label=t0["so_transcrever_label"],
                    )
                botao = gr.Button(t0["botao_label"], variant="primary", size="lg")
            with gr.Column():
                saida = gr.Textbox(label=t0["saida_label"], lines=28, max_lines=28, autoscroll=True)

        botao.click(
            processar,
            inputs=[links, ficheiro, modelo, usar_cookies, so_transcrever, idioma],
            outputs=saida,
        )

    with gr.Tab(t0["tab_ver"]) as tab_ver:
        with gr.Row():
            escolha = gr.Dropdown(label=t0["escolha_label"], choices=[], interactive=True, scale=3)
            atualizar = gr.Button(t0["atualizar_label"], scale=1)
        texto_t = gr.Textbox(label=t0["texto_t_label"], lines=24)

        tab_ver.select(listar_transcricoes, outputs=escolha)
        atualizar.click(listar_transcricoes, outputs=escolha)
        escolha.change(ler_transcricao, inputs=escolha, outputs=texto_t)

    idioma.change(
        mudar_idioma,
        inputs=idioma,
        outputs=[
            titulo_md, aviso_md, tab_baixar, links, ficheiro, modelo,
            usar_cookies, so_transcrever, botao, saida, tab_ver, escolha,
            atualizar, texto_t,
        ],
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
