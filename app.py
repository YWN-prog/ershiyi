from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
CONFIG_PATH = ROOT / "config.json"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"engine": {"mode": "command", "command": []}}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"config.json 格式错误：{exc}") from exc


_BOOT_CONFIG = load_config()
_BOOT_ENDPOINT = _BOOT_CONFIG.get("engine", {}).get("hf_endpoint")
if _BOOT_ENDPOINT:
    os.environ["HF_ENDPOINT"] = _BOOT_ENDPOINT
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import gradio as gr
_qwen_model = None
_qwen_device = None


def find_free_port(preferred: int, attempts: int = 50) -> int:
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"从 {preferred} 开始没有找到可用端口")


def find_ffmpeg_dll_dir() -> Path | None:
    candidates = [Path(item) for item in os.environ.get("PATH", "").split(os.pathsep) if item]
    candidates.append(ROOT / "ffmpeg" / "bin")
    winget_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_root.is_dir():
        candidates.extend(
            item.parent
            for item in winget_root.glob("**/avcodec-*.dll")
        )
    for directory in candidates:
        if (directory / "avutil-60.dll").exists() and list(directory.glob("avcodec-*.dll")):
            return directory
    return None


def find_ffmpeg_exe() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for directory in [ROOT / "ffmpeg" / "bin", find_ffmpeg_dll_dir()]:
        if directory:
            candidate = directory / "ffmpeg.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def normalize_reference_audio(reference_audio: str) -> str:
    source = Path(reference_audio)
    if source.suffix.lower() == ".wav":
        return str(source)
    ffmpeg = find_ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("参考音频不是 WAV，且未找到 FFmpeg。请先安装 FFmpeg。")
    converted = OUTPUT_DIR / f"reference_{uuid.uuid4().hex[:10]}.wav"
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "24000", "-sample_fmt", "s16", str(converted)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not converted.is_file() or converted.stat().st_size == 0:
        detail = (result.stderr or result.stdout or "未知错误").strip()[-800:]
        raise RuntimeError(f"参考音频转换失败：{detail}")
    return str(converted)


def detect_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def generate_qwen(reference_audio: str, text: str, language: str, config: dict) -> str:
    global _qwen_model, _qwen_device
    endpoint = config.get("hf_endpoint")
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        try:
            from huggingface_hub import constants

            constants.ENDPOINT = endpoint.rstrip("/")
            constants.HUGGINGFACE_CO_URL_TEMPLATE = constants.ENDPOINT + "/{repo_id}/resolve/{revision}/{filename}"
        except Exception:
            pass
    reference_audio = normalize_reference_audio(reference_audio)
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if _qwen_model is None or _qwen_device != device:
        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        _qwen_model = Qwen3TTSModel.from_pretrained(
            config.get("model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
            device_map=device,
            dtype=dtype,
        )
        _qwen_device = device
    qwen_language = {"中文": "Chinese", "English": "English"}.get(language, "Auto")
    wavs, sample_rate = _qwen_model.generate_voice_clone(
        text=text,
        language=qwen_language,
        ref_audio=reference_audio,
        ref_text=None,
        x_vector_only_mode=True,
        non_streaming_mode=True,
        max_new_tokens=int(config.get("max_new_tokens", 1024)),
    )
    output_path = OUTPUT_DIR / f"voice_{uuid.uuid4().hex[:10]}.wav"
    sf.write(output_path, wavs[0], sample_rate)
    return str(output_path)


def render_command(template: list[str], values: dict[str, str]) -> list[str]:
    return [item.format(**values) for item in template]


def generate_voice(
    reference_audio: str | None,
    reference_text: str,
    text: str,
    language: str,
):
    if not reference_audio or not Path(reference_audio).is_file():
        raise gr.Error("请先上传参考音频")
    text = (text or "").strip()
    reference_text = (reference_text or "").strip()
    if not text:
        raise gr.Error("请输入要生成的文本")
    if len(text) > 2000:
        raise gr.Error("单次文本不能超过 2000 个字符")

    config = load_config()
    engine = config.get("engine", {})
    if engine.get("mode") == "qwen3_tts":
        try:
            return generate_qwen(reference_audio, text, language, engine)
        except Exception as exc:
            raise gr.Error(f"Qwen3-TTS 生成失败：{exc}") from exc
    command = engine.get("command") or []
    if engine.get("mode", "command") != "command" or not command:
        raise gr.Error("尚未配置声音模型，请编辑 config.json 中的 engine.command")

    output_path = OUTPUT_DIR / f"voice_{uuid.uuid4().hex[:10]}.wav"
    leading_spaces = int(engine.get("leading_spaces", 1))
    engine_text = (" " * max(0, leading_spaces)) + text
    values = {
        "reference_audio": str(Path(reference_audio).resolve()),
        "reference_text": reference_text,
        "text": engine_text,
        "language": language,
        "output": str(output_path.resolve()),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "output_name": output_path.name,
        "device": detect_device(),
        "speed": str(engine.get("speed", 1.15)),
    }
    process_env = os.environ.copy()
    endpoint = engine.get("hf_endpoint")
    if endpoint:
        process_env["HF_ENDPOINT"] = endpoint
    process_env["PYTHONIOENCODING"] = "utf-8"
    process_env["PYTHONUTF8"] = "1"
    process_env["WANDB_DISABLED"] = "true"
    process_env["WANDB_MODE"] = "disabled"
    ffmpeg_dir = find_ffmpeg_dll_dir()
    if ffmpeg_dir:
        process_env["PATH"] = str(ffmpeg_dir) + os.pathsep + process_env.get("PATH", "")
    try:
        result = subprocess.run(
            render_command(command, values),
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=int(engine.get("timeout_seconds", 300)),
            env=process_env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise gr.Error("生成超时，请检查模型状态或缩短文本") from exc
    except OSError as exc:
        raise gr.Error(f"无法启动模型命令：{exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "未知错误").strip()[-1200:]
        raise gr.Error(f"模型生成失败：{detail}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise gr.Error("模型命令已结束，但没有生成 output 文件")
    return str(output_path)


with gr.Blocks(title="声音克隆工具") as demo:
    gr.Markdown("# 声音克隆工具\n上传参考音频，输入文本，生成并下载语音。")
    with gr.Row():
        with gr.Column():
            reference = gr.Audio(
                label="参考音频",
                sources=["microphone", "upload"],
                type="filepath",
            )
            reference_text = gr.Textbox(
                label="参考音频文字（可选）",
                placeholder="只填写当前这段参考音频里的内容；留空则自动识别。",
            )
            language = gr.Dropdown(
                ["中文", "English", "中英混合"], value="中文", label="语言"
            )
            text = gr.Textbox(
                label="生成文本", lines=8, placeholder="输入要生成的内容..."
            )
            generate = gr.Button("生成语音", variant="primary")
        with gr.Column():
            result_audio = gr.Audio(label="生成结果", type="filepath")
            gr.Markdown("生成后可在播放器中试听，并使用下载按钮保存 WAV 文件。")

    generate.click(
        generate_voice,
        inputs=[reference, reference_text, text, language],
        outputs=result_audio,
    )


if __name__ == "__main__":
    config = load_config()
    requested_port = int(os.getenv("VOICE_CLONE_PORT", config.get("port", 7860)))
    port = find_free_port(requested_port)
    if port != requested_port:
        print(f"Port {requested_port} is busy; using {port} instead.")
    demo.launch(
        server_name="localhost",
        server_port=port,
        inbrowser=True,
        theme=gr.themes.Soft(),
        show_error=True,
    )

