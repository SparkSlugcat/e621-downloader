#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置持久化：记住用户名 / API Key / 上次输出目录（明文 JSON）。
保存在 %APPDATA%/E621Downloader/config.json。
"""

import json
import os
from pathlib import Path


def config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "E621Downloader"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d / "config.json"


def load() -> dict:
    """读取配置；文件不存在或损坏时返回空字典。"""
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save(data: dict) -> None:
    """写入配置；失败时静默忽略（不阻塞下载）。"""
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
