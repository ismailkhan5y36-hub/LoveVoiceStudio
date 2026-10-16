import os
import json
import uuid
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import edge_tts

APP_DIR = Path(__file__).parent.resolve()
OUTPUTS_DIR = APP_DIR / "outputs"
STATIC_DIR = APP_DIR / "static"
HISTORY_FILE = APP_DIR / "history.json"
VOICES_CACHE_FILE = APP_DIR / "voices_cache.json"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="LoveVoice Studio AI", description="Global Multilingual Neural Text-to-Speech Studio")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

CACHED_VOICES: List[Dict[str, Any]] = []

def load_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(entry: Dict[str, Any]):
    history = load_history()
    history.insert(0, entry)
    history = history[:100]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

import backend_kokoro

class TTSRequest(BaseModel):
    text: str
    voice: str
    engine: str = "edge-tts"  # "edge-tts" or "kokoro"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"

@app.get("/api/engines")
async def get_engines():
    return [
        {
            "id": "edge-tts",
            "name": "LoveVoice Global (322 Voices)",
            "ready": True,
            "badge": "⚡ Global HD (76+ Langs)",
            "desc": "Ultra-fast HD studio voices across Urdu, Hindi, Arabic, Spanish, English & 70+ languages."
        },
        {
            "id": "kokoro",
            "name": "Kokoro Ultra (ElevenLabs Grade)",
            "ready": backend_kokoro.is_kokoro_ready(),
            "badge": "🌟 ElevenLabs Grade",
            "desc": "Deep human emotions, realistic breathing, and micro-inflection on CPU (29 Voices)."
        }
    ]

@app.on_event("startup")
async def startup_event():
    global CACHED_VOICES
    if VOICES_CACHE_FILE.exists():
        try:
            with open(VOICES_CACHE_FILE, "r", encoding="utf-8") as f:
                CACHED_VOICES = json.load(f)
                print(f"Loaded {len(CACHED_VOICES)} global voices from cache.")
                return
        except Exception as e:
            print("Error loading voices_cache.json:", e)

    # Fallback to generating voices cache
    try:
        raw = await edge_tts.list_voices()
        formatted = []
        for v in raw:
            loc = v.get("Locale", "")
            loc_name = v.get("LocaleName", "")
            lang = loc_name.split("(")[0].strip() if "(" in loc_name else loc_name
            country = loc_name.split("(")[1].replace(")", "").strip() if "(" in loc_name else loc
            short_name = v.get("ShortName", "")
            parts = short_name.split("-")
            voice_name = parts[-1].replace("Neural", "") if len(parts) >= 3 else short_name
            
            # Country flag
            flag = "🌐"
            if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isalpha():
                cc = parts[-1].upper()
                flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397)
            elif "-" in loc:
                cc = loc.split("-")[-1].upper()
                if len(cc) == 2 and cc.isalpha():
                    flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397)
            
            is_featured = voice_name in [
                "Uzma", "Asad", "Swara", "Madhur", "Zariyah", "Hamed",
                "Jenny", "Guy", "Aria", "Alvaro", "Elvira", "Jorge", "Dalia",
                "Henri", "Denise", "Katja", "Conrad", "Nanami", "Keita", "Xiaoxiao", "Yunxi"
            ]
            
            formatted.append({
                "id": short_name,
                "name": voice_name,
                "gender": v.get("Gender", "Unknown"),
                "locale": loc,
                "country": country,
                "flag": flag,
                "language": lang,
                "featured": is_featured
            })
            
        formatted.sort(key=lambda x: (not x["featured"], x["language"], x["country"], x["name"]))
        CACHED_VOICES = formatted
        with open(VOICES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)
        print(f"Generated cache with {len(CACHED_VOICES)} global voices.")
    except Exception as e:
        print("Failed to initialize voices:", e)

@app.get("/api/languages")
async def get_languages():
    """Returns sorted list of all available languages with counts and flags."""
    from collections import Counter
    counts = Counter(v["language"] for v in CACHED_VOICES)
    flag_map = {}
    for v in CACHED_VOICES:
        lang = v["language"]
        if lang not in flag_map and v.get("flag") and v["flag"] != "🌐":
            flag_map[lang] = v["flag"]
            
    # Priority popular languages first
    priority = ["Urdu", "Hindi", "English", "Spanish", "Arabic", "French", "German", "Turkish", "Chinese", "Japanese", "Portuguese", "Italian", "Russian"]
    
    result = []
    # Add priority ones that exist
    for p in priority:
        if p in counts:
            result.append({
                "name": p,
                "count": counts[p],
                "flag": flag_map.get(p, "🌐"),
                "priority": True
            })
            
    # Add remaining alphabetically
    for lang in sorted(counts.keys()):
        if lang not in priority:
            result.append({
                "name": lang,
                "count": counts[lang],
                "flag": flag_map.get(lang, "🌐"),
                "priority": False
            })
            
    return result

@app.get("/api/voices")
async def get_voices(engine: str = "edge-tts", language: Optional[str] = None):
    if engine == "kokoro":
        kv = backend_kokoro.get_kokoro_voice_metadata()
        if language and language.lower() != "all":
            lang_lower = language.lower()
            if lang_lower.startswith("en"):
                return [v for v in kv if v["lang_code"].startswith("en")]
            elif lang_lower.startswith("es"):
                return [v for v in kv if v["lang_code"].startswith("es")]
        return kv

    if not language or language.lower() == "all":
        return CACHED_VOICES
    lang_lower = language.lower()
    return [v for v in CACHED_VOICES if v["language"].lower() == lang_lower]

import re

def split_text_into_chunks(text: str, max_chunk_size: int = 2500) -> List[str]:
    text = text.strip()
    if len(text) <= max_chunk_size:
        return [text]
    
    sentences = re.split(r'(?<=[.!?\n۔।])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chunk_size:
            words = sentence.split(' ')
            sub_chunk = []
            sub_len = 0
            for w in words:
                if sub_len + len(w) + 1 > max_chunk_size and sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                    sub_chunk = [w]
                    sub_len = len(w)
                else:
                    sub_chunk.append(w)
                    sub_len += len(w) + 1
            if sub_chunk:
                chunks.append(" ".join(sub_chunk))
            continue
            
        if current_length + len(sentence) + 1 > max_chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length += len(sentence) + 1
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks if chunks else [text]

@app.post("/api/generate")
async def generate_speech(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    MAX_ALLOWED = 35000
    if len(text) > MAX_ALLOWED:
        raise HTTPException(status_code=400, detail=f"Text exceeds maximum limit of {MAX_ALLOWED:,} characters.")
    
    item_id = str(uuid.uuid4())[:12]
    filename = f"audio_{item_id}.mp3"
    filepath = OUTPUTS_DIR / filename
    start_time = time.time()
    
    # 1. KOKORO ULTRA ROUTE
    if req.engine == "kokoro":
        if not backend_kokoro.is_kokoro_ready():
            raise HTTPException(
                status_code=503, 
                detail="Kokoro-82M model is downloading. Please wait a moment or switch to LoveVoice Global."
            )
        kokoro_voices = backend_kokoro.get_kokoro_voice_metadata()
        v_match = next((v for v in kokoro_voices if v["id"] == req.voice), None)
        if not v_match:
            v_match = kokoro_voices[0]
            req.voice = v_match["id"]
            
        speed = 1.0
        try:
            if req.rate and req.rate.endswith("%"):
                val = int(req.rate.replace("%", "").replace("+", ""))
                speed = max(0.5, min(2.0, 1.0 + (val / 100.0)))
        except Exception:
            speed = 1.0
            
        try:
            elapsed = backend_kokoro.synthesize_kokoro_to_file(
                text=text,
                output_path=filepath,
                voice_id=req.voice,
                speed=speed
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Kokoro generation failed: {str(e)}")
            
        file_size_kb = round(os.path.getsize(filepath) / 1024, 1) if filepath.exists() else 0
        history_entry = {
            "id": item_id,
            "filename": filename,
            "url": f"/outputs/{filename}",
            "text": text,
            "engine": "kokoro",
            "voice_id": req.voice,
            "voice_name": v_match["name"],
            "voice_flag": v_match.get("flag", "🌟"),
            "voice_country": v_match.get("country", "Ultra Quality"),
            "voice_gender": v_match.get("gender", "Female"),
            "rate": req.rate,
            "pitch": req.pitch,
            "size_kb": file_size_kb,
            "generation_time": elapsed,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_history(history_entry)
        return history_entry

    # 2. LOVEVOICE GLOBAL ROUTE (322 VOICES)
    voice_ids = [v["id"] for v in CACHED_VOICES]
    if req.voice not in voice_ids and CACHED_VOICES:
        raise HTTPException(status_code=400, detail="Invalid voice selected.")
    
    chunks = split_text_into_chunks(text, max_chunk_size=2500)
    
    try:
        if len(chunks) == 1:
            communicate = edge_tts.Communicate(
                text=chunks[0],
                voice=req.voice,
                rate=req.rate,
                pitch=req.pitch,
                volume=req.volume
            )
            await communicate.save(str(filepath))
        else:
            with open(filepath, "wb") as outfile:
                for idx, chunk in enumerate(chunks):
                    temp_chunk_path = OUTPUTS_DIR / f"temp_{item_id}_{idx}.mp3"
                    communicate = edge_tts.Communicate(
                        text=chunk,
                        voice=req.voice,
                        rate=req.rate,
                        pitch=req.pitch,
                        volume=req.volume
                    )
                    await communicate.save(str(temp_chunk_path))
                    with open(temp_chunk_path, "rb") as infile:
                        outfile.write(infile.read())
                    try:
                        temp_chunk_path.unlink()
                    except Exception:
                        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    
    if not filepath.exists() or os.path.getsize(filepath) == 0:
        raise HTTPException(status_code=500, detail="Generated audio file is empty. Please try again.")
        
    elapsed = round(time.time() - start_time, 2)
    file_size_kb = round(os.path.getsize(filepath) / 1024, 1)
    
    voice_meta = next((v for v in CACHED_VOICES if v["id"] == req.voice), {
        "name": req.voice, "flag": "🌐", "country": "Unknown", "gender": "Unknown"
    })
    
    history_entry = {
        "id": item_id,
        "filename": filename,
        "url": f"/outputs/{filename}",
        "text": text,
        "engine": "edge-tts",
        "voice_id": req.voice,
        "voice_name": voice_meta["name"],
        "voice_flag": voice_meta.get("flag", "🌐"),
        "voice_country": voice_meta.get("country", ""),
        "voice_gender": voice_meta.get("gender", ""),
        "rate": req.rate,
        "pitch": req.pitch,
        "size_kb": file_size_kb,
        "generation_time": elapsed,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_history(history_entry)
    
    return history_entry

@app.get("/api/history")
async def get_history():
    return load_history()

@app.delete("/api/history/{item_id}")
async def delete_history(item_id: str):
    history = load_history()
    entry = next((h for h in history if h["id"] == item_id), None)
    if entry:
        filepath = OUTPUTS_DIR / entry["filename"]
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass
        history = [h for h in history if h["id"] != item_id]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    return {"success": True}

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>LoveVoice Studio UI is initializing...</h1>")