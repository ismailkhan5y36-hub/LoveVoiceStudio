#!/bin/bash
echo "=========================================================="
echo "   🌟 Setting up LoveVoice Studio AI on Android (Termux)"
echo "   🎙️ 322+ Neural Voices in 76+ Languages"
echo "=========================================================="

# Update packages
pkg update -y
pkg install -y python git

# Install required lightweight Python packages
pip install --upgrade pip
pip install fastapi uvicorn edge-tts pydantic

echo "=========================================================="
echo "   🚀 Starting LoveVoice Studio on Mobile..."
echo "   Open your phone browser at: http://localhost:7860"
echo "=========================================================="

python run.py
