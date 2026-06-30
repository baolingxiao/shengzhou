# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from neuralpal.desktop.local_files import (
    looks_like_desktop_media_organize,
    organize_desktop_media,
)
from neuralpal.tools.agent.models import ActionProposal


def test_looks_like_desktop_media_organize():
    p = ActionProposal(
        task_id="t1",
        goal="整理桌面图片和视频，放入文件夹「媒体文件」",
        surface="local",
        steps=["扫描桌面", "移动文件"],
        risk_level="L2",
        reason="test",
    )
    assert looks_like_desktop_media_organize(p) is True


def test_organize_desktop_media(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        desktop = Path(tmp)
        (desktop / "a.jpg").write_bytes(b"x")
        (desktop / "b.mp4").write_bytes(b"y")
        (desktop / "note.txt").write_text("keep")
        monkeypatch.setattr(
            "neuralpal.desktop.local_files._desktop_dir",
            lambda: desktop,
        )
        msg = organize_desktop_media(folder_name="媒体文件")
        assert "2 个文件" in msg
        assert (desktop / "媒体文件" / "a.jpg").is_file()
        assert (desktop / "媒体文件" / "b.mp4").is_file()
        assert (desktop / "note.txt").is_file()


def test_resolve_computer_use_sonnet_46():
    from neuralpal.desktop.claude_executor import _resolve_computer_use

    pairs = _resolve_computer_use("claude-sonnet-4-6")
    assert pairs[0] == (["computer-use-2025-11-24"], "computer_20251124")
