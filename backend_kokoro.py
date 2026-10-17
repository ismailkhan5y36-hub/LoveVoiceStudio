import os
import re
import time
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Dict, Any, Optional

APP_DIR = Path(__file__).parent.resolve()
MODELS_DIR = APP_DIR / "models" / "kokoro"
MODEL_PATH = MODELS_DIR / "kokoro-v0_19.onnx"
VOICES_PATH = MODELS_DIR / "voices-v1.0.bin" if (MODELS_DIR / "voices-v1.0.bin").exists() else MODELS_DIR / "voices.bin"

KOKORO_VOICES = [
    # American English - Female
    {"id": "af_heart", "name": "Heart (ElevenLabs Grade)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Flagship: Warm, breathtaking, deeply emotional"},
    {"id": "af_bella", "name": "Bella (Warm Narration)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Gentle, natural rhythm, expressive"},
    {"id": "af_nicole", "name": "Nicole (Whispering Calm)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Smooth, relaxed, intimate"},
    {"id": "af_sarah", "name": "Sarah (Broadcast / Pro)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Crisp, confident, news & commercial"},
    {"id": "af_sky", "name": "Sky (Bright & Friendly)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Upbeat, lively, conversational"},
    {"id": "af_alloy", "name": "Alloy (Modern & Direct)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Clean, balanced corporate & explainer"},
    {"id": "af_jessica", "name": "Jessica (Engaging Storyteller)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Dynamic, captivating storytelling tone"},
    {"id": "af_nova", "name": "Nova (Clear & Energetic)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Bright, modern tech narrative"},
    {"id": "af_river", "name": "River (Calm & Reflective)", "gender": "Female", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Soothing, meditative pace"},
    # American English - Male
    {"id": "am_adam", "name": "Adam (Deep & Confident)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Flagship Male: Deep vocal fry, natural cadence"},
    {"id": "am_michael", "name": "Michael (Conversational)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Authentic, relatable podcast tone"},
    {"id": "am_eric", "name": "Eric (Warm & Friendly)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Casual, reassuring storyteller"},
    {"id": "am_liam", "name": "Liam (Youthful Energy)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Engaging, modern YouTuber tone"},
    {"id": "am_echo", "name": "Echo (Resonant & Articulate)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Deep presentation & educational tone"},
    {"id": "am_onyx", "name": "Onyx (Authoritative Deep)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Commanding, cinematic narration"},
    {"id": "am_fenrir", "name": "Fenrir (Intense Dramatic)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Bold, dramatic trailer voice"},
    {"id": "am_puck", "name": "Puck (Playful & Character)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Animated, expressive character"},
    {"id": "am_santa", "name": "Santa (Jovial & Deep)", "gender": "Male", "lang_code": "en-us", "country": "United States", "flag": "🇺🇸", "desc": "Rich, heartwarming baritone"},
    # British English - Female
    {"id": "bf_emma", "name": "Emma (Royal British)", "gender": "Female", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Sophisticated, elegant RP accent"},
    {"id": "bf_isabella", "name": "Isabella (Gentle British)", "gender": "Female", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Soft, poetic UK tone"},
    {"id": "bf_alice", "name": "Alice (Classic British)", "gender": "Female", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Polished, classical UK English"},
    {"id": "bf_lily", "name": "Lily (Bright British)", "gender": "Female", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Cheerful, modern UK conversational"},
    # British English - Male
    {"id": "bm_george", "name": "George (Classic British)", "gender": "Male", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Documentary & BBC style narration"},
    {"id": "bm_lewis", "name": "Lewis (Modern British)", "gender": "Male", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Warm, articulate UK conversational"},
    {"id": "bm_daniel", "name": "Daniel (Deep UK Narration)", "gender": "Male", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Rich, resonant British storyteller"},
    {"id": "bm_fable", "name": "Fable (British Drama)", "gender": "Male", "lang_code": "en-gb", "country": "United Kingdom", "flag": "🇬🇧", "desc": "Artistic, expressive audiobook UK voice"},
    # Spanish - Female & Male
    {"id": "ef_dora", "name": "Dora (Spanish Natural)", "gender": "Female", "lang_code": "es", "country": "Spain / LatAm", "flag": "🇪🇸", "desc": "Warm, clear Spanish narration"},
    {"id": "em_alex", "name": "Alex (Spanish Storyteller)", "gender": "Male", "lang_code": "es", "country": "Spain / LatAm", "flag": "🇪🇸", "desc": "Engaging, natural masculine Spanish voice"},
    {"id": "em_santa", "name": "Santa (Spanish Deep)", "gender": "Male", "lang_code": "es", "country": "Spain / LatAm", "flag": "🇪🇸", "desc": "Deep, resonant Spanish male voice"},
]

_kokoro_instance = None

def is_kokoro_ready() -> bool:
    return MODEL_PATH.exists() and VOICES_PATH.exists() and MODEL_PATH.stat().st_size > 100_000_000

def get_kokoro_engine():
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance
    if not is_kokoro_ready():
        raise RuntimeError("Kokoro model files are not yet fully downloaded.")
    from kokoro_onnx import Kokoro
    import onnxruntime as rt
    print(f"Loading Kokoro ONNX model with 4 CPU threads from {MODEL_PATH}...")
    opts = rt.SessionOptions()
    opts.intra_op_num_threads = 4  # Utilize all 4 physical cores of Intel Core i5
    opts.inter_op_num_threads = 1
    opts.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
    session = rt.InferenceSession(str(MODEL_PATH), sess_options=opts, providers=["CPUExecutionProvider"])
    _kokoro_instance = Kokoro.from_session(session, str(VOICES_PATH))
    print("Kokoro ONNX engine successfully initialized with optimized 4 CPU threads!")
    return _kokoro_instance

def get_kokoro_voice_metadata() -> List[Dict[str, Any]]:
    for v in KOKORO_VOICES:
        if v.get("lang_code", "").startswith("en-us"):
            v["language"] = "American English"
            v["accent"] = "American"
        elif v.get("lang_code", "").startswith("en-gb"):
            v["language"] = "British English"
            v["accent"] = "British"
        elif v.get("lang_code", "").startswith("es"):
            v["language"] = "Spanish"
            v["accent"] = "Spanish"
        else:
            v["language"] = "English"
            v["accent"] = "English"
    return KOKORO_VOICES

def synthesize_kokoro_to_file(
    text: str,
    output_path: Path,
    voice_id: str = "af_heart",
    speed: float = 1.0,
    sentence_pause: float = 0.28,
) -> float:
    """
    Synthesizes speech using Kokoro ONNX and writes directly to an MP3 file.
    Returns the generation elapsed time in seconds.
    """
    engine = get_kokoro_engine()
    
    # Identify language code from voice prefix
    # af/am -> en-us, bf/bm -> en-gb, ef/em -> es
    lang = "en-us"
    if voice_id.startswith(("bf_", "bm_")):
        lang = "en-gb"
    elif voice_id.startswith(("ef_", "em_", "es_", "pf_", "pm_")):
        lang = "es"
        
    t0 = time.time()
    
    text = text.strip()
    sample_rate = 24000

    # If text is medium length, let Kokoro handle internal chunking in one fast pass
    if len(text) <= 600:
        samples, sr = engine.create(
            text=text,
            voice=voice_id,
            speed=speed,
            lang=lang,
            sentence_pause=sentence_pause,
            trim=True
        )
        final_waveform = samples
        sample_rate = sr
    else:
        # Group text into reasonable paragraphs (~500 chars) to prevent memory spikes
        sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', text) if s.strip()]
        chunks = []
        curr = []
        curr_len = 0
        for s in sentences:
            if curr_len + len(s) > 500 and curr:
                chunks.append(" ".join(curr))
                curr = [s]
                curr_len = len(s)
            else:
                curr.append(s)
                curr_len += len(s) + 1
        if curr:
            chunks.append(" ".join(curr))

        all_audio_segments = []
        for chunk in chunks:
            samples, sr = engine.create(
                text=chunk,
                voice=voice_id,
                speed=speed,
                lang=lang,
                sentence_pause=sentence_pause,
                trim=True
            )
            sample_rate = sr
            all_audio_segments.append(samples)
            pause_samples = int(sample_rate * sentence_pause)
            all_audio_segments.append(np.zeros(pause_samples, dtype=np.float32))
            
        final_waveform = np.concatenate(all_audio_segments)
    
    # Write directly as high quality MP3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), final_waveform, sample_rate, format="MP3")
    
    elapsed = round(time.time() - t0, 2)
    return elapsed

