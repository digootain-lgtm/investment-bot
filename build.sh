#!/bin/bash
# Build script for Render

echo "🔧 安裝 Python 依賴..."
pip install --upgrade pip
pip uninstall -y python-telegram-bot
pip install python-telegram-bot==20.7
pip install -r requirements.txt
echo "✅ 依賴安裝完成"
