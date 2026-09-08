"""Model adapter entry point.

This file is retained as an adapter example. The default config uses the
F5-TTS CLI directly; custom engines can use this entry point instead.
"""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(
        "请在 engine_adapter.py 中接入 GPT-SoVITS/CosyVoice 推理，并写入: "
        + str(Path(args.output).resolve())
    )


if __name__ == "__main__":
    main()
