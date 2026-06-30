#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 贾维斯.app（py2app）

用法（在项目根目录）:
  ./scripts/macos/make_jarvis_app.sh
"""
from __future__ import annotations

from pathlib import Path
from setuptools import find_packages, setup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

APP = [str(HERE / "jarvis_app_entry.py")]

PACKAGES = [
    p
    for p in find_packages(where=str(ROOT))
    if p == "server" or p.startswith("neuralpal")
]

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

OPTIONS = {
    "argv_emulation": False,
    "emulate_shell_environment": True,
    "semi_standalone": True,
    "site_packages": True,
    "packages": ["neuralpal", "server"],
    "includes": [
        "uvicorn",
        "fastapi",
        "pydantic",
        "pydantic_settings",
        "langchain",
        "langchain_core",
        "langchain_anthropic",
        "langchain_openai",
        "anthropic",
        "openai",
        "pyautogui",
        "ApplicationServices",
        "dotenv",
        "httpx",
        "anyio",
        "starlette",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy.distutils",
        "pytest",
        "IPython",
        "chromadb",
        "sentence_transformers",
        "transformers",
        "torch",
        "tensorflow",
        "sklearn",
        "scipy",
        "pandas",
        "onnxruntime",
        "opencv",
        "cv2",
        "PIL",
        "notebook",
        "jupyter",
        "sympy",
        "setuptools",
        "distutils",
    ],
    "plist": PLIST,
    "resources": [
        str(ROOT / "dist"),
        str(ROOT / "data"),
        str(ROOT / ".env.example"),
    ],
}

setup(
    name="贾维斯",
    app=APP,
    packages=PACKAGES,
    package_dir={"": str(ROOT)},
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
