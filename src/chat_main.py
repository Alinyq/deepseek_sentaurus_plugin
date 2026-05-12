#!/usr/bin/env python3
"""
TCAD AI Chat - Standalone launcher
可以独立运行或在SWB中调用
"""
import sys
import os

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from core.chat.chat_widget import ChatWidget


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont("WenQuanYi Micro Hei", 11)
    if not font.exactMatch():
        font = QFont("Noto Sans CJK SC", 11)
    app.setFont(font)

    window = ChatWidget()
    window.setWindowTitle("TCAD AI Chat - Multi-turn Conversation")
    window.resize(1000, 700)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
