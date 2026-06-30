#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量 alias 模式构建 贾维斯.app（依赖项目 .venv，打包快、TCC 显示 App 名）。"""
from __future__ import annotations

from pathlib import Path
from setuptools import setup

HERE = Path(__file__).resolve().parent
ICON = HERE / "jarvis.icns"

APP = [str(HERE / "jarvis_app_entry.py")]

PLIST = {
    "CFBundleName": "贾维斯",
    "CFBundleDisplayName": "贾维斯",
    "CFBundleIdentifier": "com.neuralpal.jarvis",
    "CFBundleShortVersionString": "0.1.0",
    "CFBundleVersion": "1",
    "LSMinimumSystemVersion": "13.0",
    "NSHighResolutionCapable": True,
    "NSAppleEventsUsageDescription": "贾维斯需要代你操作其他 App 以完成代办任务。",
}

setup(
    name="贾维斯",
    app=APP,
    options={
        "py2app": {
            "alias": True,
            "argv_emulation": False,
            "iconfile": str(ICON),
            "plist": PLIST,
        }
    },
    setup_requires=["py2app"],
)
