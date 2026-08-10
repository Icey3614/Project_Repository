# -*- coding: utf-8 -*-
"""设置持久化：主题与语言，保存到程序目录下的 settings.json。"""
import json
import os
import sys

DEFAULTS = {"theme": "light", "lang": "zh_cn"}


def get_settings_path():
    """settings.json 放在主程序（或 exe）所在目录。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "settings.json")


def load_settings():
    """读取设置；文件不存在或损坏时返回默认值。"""
    result = dict(DEFAULTS)
    try:
        with open(get_settings_path(), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("theme") in ("light", "dark"):
            result["theme"] = data["theme"]
        if data.get("lang") in ("zh_cn", "zh_tw", "en", "ru"):
            result["lang"] = data["lang"]
    except Exception:
        pass
    return result


def save_settings(theme="light", lang="zh_cn"):
    """保存设置到 settings.json。"""
    try:
        with open(get_settings_path(), "w", encoding="utf-8") as f:
            json.dump(
                {"theme": theme, "lang": lang},
                f, ensure_ascii=False, indent=2,
            )
    except OSError:
        pass
