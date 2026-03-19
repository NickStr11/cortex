#!/usr/bin/env python3
"""PreCompact hook: trigger diary entry before context compression."""
import sys

print("Контекст сжимается. Выполни /diary прямо сейчас, чтобы сохранить контекст сессии.")
sys.exit(0)
