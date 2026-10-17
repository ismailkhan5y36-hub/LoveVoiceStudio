import os
import sys
import json
import uuid
import time
import socket
import asyncio
import re
from datetime import datetime
from pathlib import Path
import aiohttp
from aiohttp import web
import edge_tts
import smart_director

# Keep Termux CPU and Network awake in background on Android
if os.environ.get("TERMUX_VERSION") or os.path.exists("/data/data/com.termux"):
    try:
        os.system("termux-wake-lock 2>/dev/null")
    except Exception:
        pass

# Force IPv4 to eliminate 90s IPv6 TCP connection timeout on mobile networks / Termux
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo


APP_DIR = Path(__file__).parent.resolve()
OUTPUTS_DIR = APP_DIR / "outputs"
STATIC_DIR = APP_DIR / "static"
HISTORY_FILE = APP_DIR / "history.json"
VOICES_CACHE_FILE = APP_DIR / "voices_cache.json"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

CACHED_VOICES = []

def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    history = history[:100]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving history:", e)

def load_voices():
    global CACHED_VOICES
    if VOICES_CACHE_FILE.exists():
        try:
            with open(VOICES_CACHE_FILE, "r", encoding="utf-8") as f:
                CACHED_VOICES = json.load(f)
                print(f"[Mobile Server] Loaded {len(CACHED_VOICES)} voices from cache.")
                return
        except Exception as e:
            print("Error loading voices cache:", e)

def split_text_into_chunks(text: str, max_chunk_size: int = 1500):
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

# Web Handlers
async def handle_index(request):
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return web.FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return web.Response(text="<h1>LoveVoice Studio Mobile Initializing...</h1>", content_type="text/html")

async def handle_engines(request):
    return web.json_response([
        {
            "id": "edge-tts",
            "name": "LoveVoice Global (322 Voices)",
            "ready": True,
            "badge": "⚡ Global HD (76+ Langs)",
            "desc": "Ultra-fast HD studio voices across Urdu, Hindi, Arabic, Spanish, English & 70+ languages."
        }
    ])

async def handle_languages(request):
    from collections import Counter
    counts = Counter(v["language"] for v in CACHED_VOICES)
    flag_map = {}
    for v in CACHED_VOICES:
        lang = v["language"]
        if lang not in flag_map and v.get("flag") and v["flag"] != "🌐":
            flag_map[lang] = v["flag"]
            
    priority = ["Urdu", "Hindi", "English", "Spanish", "Arabic", "French", "German", "Turkish", "Chinese", "Japanese", "Portuguese", "Italian", "Russian"]
    result = []
    for p in priority:
        if p in counts:
            result.append({
                "name": p,
                "count": counts[p],
                "flag": flag_map.get(p, "🌐"),
                "priority": True
            })
    for lang in sorted(counts.keys()):
        if lang not in priority:
            result.append({
                "name": lang,
                "count": counts[lang],
                "flag": flag_map.get(lang, "🌐"),
                "priority": False
            })
    return web.json_response(result)

async def handle_voices(request):
    lang = request.query.get("language")
    if not lang or lang.lower() == "all":
        return web.json_response(CACHED_VOICES)
    lang_lower = lang.lower()
    filtered = [v for v in CACHED_VOICES if (v.get("language") or "").lower() == lang_lower]
    return web.json_response(filtered)

async def handle_smart_direct(request):
    try:
        data = await request.json()
        text = data.get("text", "")
        return web.json_response(smart_director.analyze_text(text))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_smart_enhance(request):
    try:
        data = await request.json()
        text = data.get("text", "")
        enhanced = smart_director.enhance_word_level_emotions(text)
        return web.json_response({"original": text, "enhanced": enhanced})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_generate(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"detail": "Invalid JSON body"}, status=400)

    text = data.get("text", "").strip()
    if not text:
        return web.json_response({"detail": "Text cannot be empty."}, status=400)

    voice = data.get("voice", "ur-PK-UzmaNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")
    volume = data.get("volume", "+0%")

    item_id = str(uuid.uuid4())[:12]
    filename = f"audio_{item_id}.mp3"
    filepath = OUTPUTS_DIR / filename
    start_time = time.time()

    chunks = split_text_into_chunks(text, max_chunk_size=1500)

    try:
        if len(chunks) == 1:
            conn = aiohttp.TCPConnector(family=socket.AF_INET)
            communicate = edge_tts.Communicate(
                text=chunks[0],
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
                connector=conn
            )
            # High-speed streaming synthesis
            with open(filepath, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
        else:
            temp_paths = [OUTPUTS_DIR / f"temp_{item_id}_{idx}.mp3" for idx in range(len(chunks))]

            async def run_single_chunk(idx: int, chunk_text: str, dest_path: Path):
                c_conn = aiohttp.TCPConnector(family=socket.AF_INET)
                comm = edge_tts.Communicate(
                    text=chunk_text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume,
                    connector=c_conn
                )
                with open(dest_path, "wb") as f:
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])

            tasks = [run_single_chunk(i, chunks[i], temp_paths[i]) for i in range(len(chunks))]
            await asyncio.gather(*tasks)

            with open(filepath, "wb") as outfile:
                for tp in temp_paths:
                    if tp.exists():
                        with open(tp, "rb") as infile:
                            outfile.write(infile.read())
                        try:
                            tp.unlink()
                        except Exception:
                            pass

    except Exception as e:
        return web.json_response({"detail": f"Edge-TTS failed: {str(e)}"}, status=500)

    elapsed = round(time.time() - start_time, 2)
    file_size_kb = round(os.path.getsize(filepath) / 1024, 1) if filepath.exists() else 0

    voice_meta = next((v for v in CACHED_VOICES if v["id"] == voice), {
        "name": voice, "flag": "🌐", "country": "Unknown", "gender": "Unknown"
    })

    history_entry = {
        "id": item_id,
        "filename": filename,
        "url": f"/outputs/{filename}",
        "text": text,
        "engine": "edge-tts",
        "voice_id": voice,
        "voice_name": voice_meta.get("name", voice),
        "voice_flag": voice_meta.get("flag", "🌐"),
        "voice_country": voice_meta.get("country", ""),
        "voice_gender": voice_meta.get("gender", ""),
        "rate": rate,
        "pitch": pitch,
        "size_kb": file_size_kb,
        "generation_time": elapsed,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_history(history_entry)
    return web.json_response(history_entry)

async def handle_get_history(request):
    return web.json_response(load_history())

async def handle_delete_history(request):
    item_id = request.match_info.get("item_id")
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
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return web.json_response({"success": True})

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

def create_app():
    load_voices()
    app = web.Application(middlewares=[cors_middleware], client_max_size=50*1024*1024)
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/engines', handle_engines)
    app.router.add_get('/api/languages', handle_languages)
    app.router.add_get('/api/voices', handle_voices)
    app.router.add_post('/api/smart-direct', handle_smart_direct)
    app.router.add_post('/api/smart-enhance', handle_smart_enhance)
    app.router.add_post('/api/generate', handle_generate)
    app.router.add_get('/api/history', handle_get_history)
    app.router.add_delete('/api/history/{item_id}', handle_delete_history)
    app.router.add_static('/outputs', path=str(OUTPUTS_DIR), name='outputs')
    app.router.add_static('/static', path=str(STATIC_DIR), name='static')
    return app

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    port = int(os.environ.get("PORT", 7860))
    print("=" * 65)
    print("   🌟 LoveVoice Studio AI Mobile Server (Fast IPv4 Streaming)")
    print("   🎙️ 322+ Neural Voices in 76+ Languages")
    print(f"   📱 Running on: http://localhost:{port}")
    print("=" * 65)
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
