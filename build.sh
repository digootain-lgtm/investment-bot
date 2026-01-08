#!/bin/bash
# Build script for Render

echo "🔧 升級 pip..."
pip install --upgrade pip

echo "🗑️ 移除所有舊版本..."
pip uninstall -y python-telegram-bot python-telegram-bot-raw

echo "📦 安裝 python-telegram-bot 20.7..."
pip install --no-cache-dir python-telegram-bot[all]==20.7

echo "📦 安裝其他依賴..."
pip install --no-cache-dir requests==2.31.0
pip install --no-cache-dir flask==3.0.0

echo "✅ 檢查安裝版本..."
pip show python-telegram-bot

echo "✅ 依賴安裝完成"
