from pathlib import Path

import pytest

from app import render_command


def test_render_command_replaces_placeholders():
    command = render_command(
        ["python", "adapter.py", "--text", "{text}", "--output", "{output}"],
        {"text": "你好", "output": "out.wav"},
    )
    assert command == ["python", "adapter.py", "--text", "你好", "--output", "out.wav"]


def test_render_command_does_not_require_shell():
    assert isinstance(render_command(["echo", "{text}"], {"text": "a;b"}), list)
