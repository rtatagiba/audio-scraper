"""
transcrever.py — transcreve todos os audios de audios/ com faster-whisper.

Para cada audio gera em transcricoes/:
  <id>.txt   -> texto limpo
  <id>.json  -> segments (start, end, text) + metadados do <id>.info.json

Audios que ja tem .txt em transcricoes/ sao ignorados.
Erros num ficheiro nao param o lote.

Uso:
  python transcrever.py                # modelo default: small
  python transcrever.py --model medium
  python transcrever.py --language pt --audios audios --saida transcricoes
"""

import argparse
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

EXTENSOES_AUDIO = {".mp3", ".m4a", ".wav", ".opus", ".webm", ".ogg", ".flac"}

# Campos do info.json do yt-dlp que interessam guardar
CAMPOS_METADADOS = [
    "id", "title", "description", "uploader", "uploader_id", "channel",
    "webpage_url", "extractor", "duration", "upload_date",
    "view_count", "like_count", "comment_count",
]


def carregar_metadados(caminho_audio: Path) -> dict:
    info_json = caminho_audio.with_suffix("").with_suffix(".info.json")
    # yt-dlp grava como <id>.info.json ao lado do audio
    if not info_json.exists():
        info_json = caminho_audio.parent / f"{caminho_audio.stem}.info.json"
    if not info_json.exists():
        return {}
    try:
        with open(info_json, encoding="utf-8") as f:
            info = json.load(f)
        return {k: info.get(k) for k in CAMPOS_METADADOS if info.get(k) is not None}
    except (json.JSONDecodeError, OSError) as e:
        print(f"  aviso: nao consegui ler metadados {info_json.name}: {e}")
        return {}


def limpar_texto(segmentos: list[dict]) -> str:
    partes = [s["text"].strip() for s in segmentos if s["text"].strip()]
    return " ".join(partes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcreve audios com faster-whisper.")
    parser.add_argument("--model", default="small",
                        help="Modelo whisper: tiny, base, small, medium, large-v3 (default: small)")
    parser.add_argument("--language", default="pt", help="Idioma (default: pt)")
    parser.add_argument("--audios", default="audios", help="Pasta com os audios (default: audios)")
    parser.add_argument("--saida", default="transcricoes", help="Pasta de saida (default: transcricoes)")
    args = parser.parse_args()

    pasta_audios = Path(args.audios)
    pasta_saida = Path(args.saida)

    if not pasta_audios.is_dir():
        print(f"ERRO: pasta '{pasta_audios}' nao existe. Corre primeiro o baixar.ps1.")
        return 1

    pasta_saida.mkdir(parents=True, exist_ok=True)

    ficheiros = sorted(
        f for f in pasta_audios.iterdir()
        if f.suffix.lower() in EXTENSOES_AUDIO
    )
    if not ficheiros:
        print(f"Nenhum audio encontrado em '{pasta_audios}'.")
        return 0

    pendentes = [f for f in ficheiros if not (pasta_saida / f"{f.stem}.txt").exists()]
    print(f"{len(ficheiros)} audios encontrados, {len(pendentes)} por transcrever.")
    if not pendentes:
        return 0

    print(f"A carregar modelo '{args.model}' (compute_type=int8)...")
    model = WhisperModel(args.model, compute_type="int8")

    ok, falhas = 0, 0
    for i, audio in enumerate(pendentes, 1):
        print(f"[{i}/{len(pendentes)}] {audio.name}")
        try:
            segments, info = model.transcribe(
                str(audio),
                language=args.language,
                vad_filter=True,
            )
            segmentos = [
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                for s in segments
            ]

            texto = limpar_texto(segmentos)
            (pasta_saida / f"{audio.stem}.txt").write_text(texto, encoding="utf-8")

            resultado = {
                "ficheiro": audio.name,
                "idioma_detetado": info.language,
                "duracao": round(info.duration, 2),
                "metadados": carregar_metadados(audio),
                "segments": segmentos,
            }
            with open(pasta_saida / f"{audio.stem}.json", "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            print(f"  ok ({len(segmentos)} segmentos, {len(texto)} chars)")
            ok += 1
        except Exception as e:
            print(f"  ERRO em {audio.name}: {e}")
            falhas += 1

    print(f"\nConcluido: {ok} transcritos, {falhas} falhas. Resultados em '{pasta_saida}/'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
