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

PADRAO_URL = re.compile(r'https?://[^\s,;"\'<>|]+')
PADROES_POST = re.compile(
    r'instagram\.com/(reel|reels|p|tv)/'
    r'|tiktok\.com/@[^/]+/video/'
    r'|tiktok\.com/(t|v)/'
    r'|vm\.tiktok\.com/'
    r'|youtube\.com/(shorts/|watch\?)'
    r'|youtu\.be/'
)


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


def processar(links_texto, ficheiro, modelo, usar_cookies, so_transcrever):
    log: list[str] = []

    def emitir(linha=""):
        log.append(linha)
        return "\n".join(log[-400:])  # limita o tamanho mostrado

    if not so_transcrever:
        # --- 1. Juntar texto colado + ficheiro subido ---
        texto = links_texto or ""
        if ficheiro:
            try:
                texto += "\n" + Path(ficheiro).read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                yield emitir(f"ERRO ao ler o ficheiro subido: {e}")
                return

        urls = extrair_urls(texto)
        if not urls:
            yield emitir(
                "Nenhum link de post/video encontrado.\n"
                "Aceites: instagram.com/reel|p/..., tiktok.com/@user/video/..., "
                "youtube.com/shorts/..., youtu.be/..."
            )
            return

        yield emitir(f">> {len(urls)} links encontrados:")
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
            yield emitir("AVISO: cookies.txt nao encontrado na pasta do projeto — a continuar sem cookies.")

        yield emitir()
        yield emitir(">> A baixar audios...")
        for linha in _correr(comando):
            if "No video formats found" in linha:
                yield emitir("   (post sem video — provavelmente so fotos, ignorado)")
            else:
                yield emitir(f"   {linha}")

    # --- 3. Transcrever ---
    yield emitir()
    yield emitir(f">> A transcrever com o modelo '{modelo}' (a 1a vez descarrega o modelo, e demora)...")
    comando_t = [sys.executable, "-u", str(BASE / "transcrever.py"), "--model", modelo]
    for linha in _correr(comando_t):
        yield emitir(f"   {linha}")

    # --- 4. Resumo final ---
    yield emitir()
    txts = sorted(PASTA_TRANSCRICOES.glob("*.txt")) if PASTA_TRANSCRICOES.is_dir() else []
    yield emitir(f">> Concluido! {len(txts)} transcricoes em {PASTA_TRANSCRICOES}")
    for t in txts:
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


with gr.Blocks(title="Audio Scraper") as demo:
    gr.Markdown("# 🎙️ Audio Scraper\nBaixa o audio de Instagram / TikTok / Shorts e transcreve para texto.")

    with gr.Tab("Baixar e transcrever"):
        with gr.Row():
            with gr.Column():
                links = gr.Textbox(
                    label="Cola aqui os links (um por linha, ou texto com links pelo meio)",
                    lines=8,
                    placeholder="https://www.instagram.com/reel/...\nhttps://www.tiktok.com/@user/video/...\nhttps://www.youtube.com/shorts/...",
                )
                ficheiro = gr.File(
                    label="...ou sobe um TXT / CSV com os links",
                    file_types=[".txt", ".csv"],
                    type="filepath",
                )
                with gr.Row():
                    modelo = gr.Dropdown(
                        ["tiny", "base", "small", "medium", "large-v3"],
                        value="small",
                        label="Modelo de transcricao",
                        info="small = bom equilibrio; medium = mais preciso e mais lento",
                    )
                with gr.Row():
                    usar_cookies = gr.Checkbox(
                        value=COOKIES_DEFAULT.exists(),
                        label="Usar cookies.txt (necessario para Instagram)",
                    )
                    so_transcrever = gr.Checkbox(
                        value=False,
                        label="So transcrever (nao baixar nada novo)",
                    )
                botao = gr.Button("▶ Baixar e transcrever", variant="primary", size="lg")
            with gr.Column():
                saida = gr.Textbox(label="Progresso", lines=28, max_lines=28, autoscroll=True)

        botao.click(processar, inputs=[links, ficheiro, modelo, usar_cookies, so_transcrever], outputs=saida)

    with gr.Tab("Ver transcricoes") as tab_ver:
        with gr.Row():
            escolha = gr.Dropdown(label="Transcricao", choices=[], interactive=True, scale=3)
            atualizar = gr.Button("🔄 Atualizar lista", scale=1)
        texto_t = gr.Textbox(label="Texto", lines=24)

        tab_ver.select(listar_transcricoes, outputs=escolha)
        atualizar.click(listar_transcricoes, outputs=escolha)
        escolha.change(ler_transcricao, inputs=escolha, outputs=texto_t)

if __name__ == "__main__":
    demo.launch(inbrowser=True)
