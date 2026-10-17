#!/bin/bash
echo "=========================================================="
echo "   🌟 Setting up LoveVoice Studio AI on Android (Termux)"
echo "   🎙️ 322+ Neural Voices in 76+ Languages"
echo "   ⚡ Zero-Rust Ultra Fast Mobile Setup"
echo "=========================================================="

# Update packages
pkg update -y
pkg install -y python git

# Install edge-tts (pure async Python with aiohttp - zero Rust/C compiler needed)
pip install --upgrade pip
pip install edge-tts

echo "=========================================================="
echo "   🚀 Starting LoveVoice Studio on Mobile..."
echo "   Open your phone browser at: http://localhost:7860"
echo "=========================================================="

python run.py
