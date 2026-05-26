"""
utils.py — 通用辅助函数
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent


def _debug_log(msg):
    """写调试日志到 gunicorn error log 文件（相对于项目BASE_DIR）"""
    try:
        with open(BASE_DIR / 'gunicorn-error.log', 'a') as f:
            from datetime import datetime
            f.write(f'[{datetime.now().isoformat()}] {msg}\n')
    except Exception:
        pass


def _safe_number(val):
    """安全转换为 float，失败返回 0。"""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return 0
