"""
Smart AI Emotion & Script Director for LoveVoice Studio.
Zero-dependency, high-speed, multilingual sentiment and prosody analyzer.
Analyzes scripts across Urdu, Hindi, English, Spanish, Arabic, etc., and recommends
optimal voice emotion, speaking rate, pitch, volume, and breathing rhythm.
"""

import re
from typing import Dict, Any

# Multilingual Emotion Lexicons
EMOTION_LEXICONS = {
    "happy": {
        "words": [
            # Urdu
            "خوش", "خوشی", "مبارک", "کامیاب", "کامیابی", "شاندار", "عید", "بہترین", "پیار", "محبت", 
            "جیت", "خوشخبری", "جشن", "زندہ باد", "سلامت", "خوبصورت", "شکر", "الحمدللہ", "مسکراہٹ",
            # Hindi
            "खुशी", "खुश", "बधाई", "शानदार", "जीत", "प्रेम", "सुंदर", "उत्सव", "मुबारक", "आनंद", 
            "प्रसन्न", "सफलता", "मुस्कान", "प्यार",
            # English
            "happy", "joy", "cheerful", "congratulations", "celebrate", "celebrating", "great", 
            "wonderful", "amazing", "love", "smile", "laugh", "excited", "fantastic", "awesome", 
            "delighted", "blessed", "victory", "proud", "beautiful", "yay", "hurray", "cheers",
            # Arabic
            "سعيد", "سعادة", "مبروك", "فرح", "جميل", "رائع", "حب", "تهانينا", "الحمدلله", "نجاح",
            # Spanish
            "feliz", "felicidad", "alegre", "felicidades", "maravilloso", "amor", "genial", 
            "excelente", "fiesta", "sonrisa", "victoria", "hermoso"
        ],
        "rate": "+10%",
        "pitch": "+15Hz",
        "volume": "+5%",
        "label": "😃 Cheerful & Happy",
        "reason": "Joyful words, celebration or positive emotion detected."
    },
    "sad": {
        "words": [
            # Urdu
            "اداس", "اداسی", "افسوس", "غم", "غمگین", "موت", "رونا", "درد", "تکلیف", "مایوس", 
            "مایوسی", "جدائی", "بے بس", "اشک", "جنازہ", "صدمہ", "تنہائی", "تباہ", "آنسو", "ہار",
            # Hindi
            "उदास", "उदासी", "दुःख", "दुख", "दर्द", "रोना", "शोक", "मायूस", "कष्ट", "पीड़ा", 
            "अकेला", "गम", "आंसू", "बेबस",
            # English
            "sad", "sadness", "unhappy", "sorrow", "grief", "mourn", "mourning", "tragic", 
            "tragedy", "pain", "crying", "tears", "depressed", "depression", "heartbroken", 
            "loss", "regret", "hopeless", "condolences", "lonely", "miss you", "rip", "devastated",
            # Arabic
            "حزين", "حزن", "مؤسف", "ألم", "بكاء", "موت", "وجع", "فقدان", "صدمة", "دموع",
            # Spanish
            "triste", "tristeza", "pena", "dolor", "llorar", "luto", "tragedia", "soledad", 
            "depresión", "lágrimas", "pérdida"
        ],
        "rate": "-15%",
        "pitch": "-10Hz",
        "volume": "-5%",
        "label": "😢 Emotional & Sad",
        "reason": "Somber, grieving or melancholy sentiment detected."
    },
    "whisper": {
        "words": [
            # Urdu
            "راز", "خاموش", "خاموشی", "آہستہ", "سرگوشی", "چھپ", "چپکے", "کان میں", "کوئی نہ سنے", "آہستہ بولو",
            # Hindi
            "राज", "चुप", "धीरे", "फुसफुसा", "रहस्य", "चुपचाप", "शांति", "धीमे",
            # English
            "whisper", "whispering", "secret", "quiet", "softly", "shh", "silent", "silence", 
            "hush", "confidential", "listen closely", "private", "stealth", "asmr", "don't tell",
            # Arabic
            "همس", "سر", "هدوء", "صمت", "سري", "لا تخبر أحدا",
            # Spanish
            "susurro", "susurrar", "secreto", "silencio", "callado", "despacio", "confidencial", "en voz baja"
        ],
        "rate": "-10%",
        "pitch": "-20Hz",
        "volume": "-30%",
        "label": "🤫 Whisper / ASMR",
        "reason": "Secretive, whispering, or intimate quiet tone detected."
    },
    "excited": {
        "words": [
            # Urdu
            "جلدی", "خطرہ", "ہنگامی", "بھاگو", "فوراً", "تیز", "دیکھو", "خبردار", "ہلچل", "دھماکہ", 
            "حیران", "ناقابل یقین", "تیزی سے", "ہوشیار",
            # Hindi
            "जल्दी", "खतरा", "आपातकाल", "भागो", "तुरंत", "तेज़", "सावधान", "धमाका", "अविश्वसनीय",
            # English
            "breaking", "urgent", "emergency", "hurry", "quick", "fast", "danger", "alert", 
            "run", "explosive", "insane", "unbelievable", "omg", "rush", "action", "warning", 
            "look out", "breaking news", "shocking", "critical",
            # Arabic
            "عاجل", "خطر", "بسرعة", "تحذير", "طوارئ", "انفجار", "لا يصدق", "انتبه",
            # Spanish
            "urgente", "alerta", "peligro", "rápido", "corre", "emergencia", "increíble", "impactante", "cuidado"
        ],
        "rate": "+18%",
        "pitch": "+20Hz",
        "volume": "+10%",
        "label": "⚡ Excited & Energetic",
        "reason": "High urgency, excitement or intense action detected."
    },
    "dramatic": {
        "words": [
            # Urdu
            "ایک دفعہ کا ذکر ہے", "داستان", "کہانی", "اندھیرا", "پراسرار", "جنگل", "خوفناک", 
            "صدیوں پہلے", "تاریکی", "بادشاہ", "خواب", "سفر", "قسمت", "سایہ",
            # Hindi
            "एक समय की बात है", "कहानी", "अंधेरा", "रहस्यमय", "जंगल", "डरावना", "इतिहास", "किस्सा", "छाया",
            # English
            "once upon a time", "story", "chapter", "shadow", "mystery", "mysterious", "journey", 
            "destiny", "ancient", "darkness", "legend", "tale", "chronicle", "deep within", 
            "the end", "suddenly", "fateful", "myth",
            # Arabic
            "كان يا ما كان", "قصة", "حكاية", "غموض", "ظلام", "أسطورة", "مصير", "رحلة",
            # Spanish
            "había una vez", "historia", "misterio", "sombra", "leyenda", "cuento", "antiguo", "destino", "de repente"
        ],
        "rate": "-8%",
        "pitch": "-6Hz",
        "volume": "+10%",
        "label": "🎙️ Dramatic Storyteller",
        "reason": "Storytelling, suspense or cinematic narrative detected."
    },
    "news": {
        "words": [
            # Urdu
            "حکومت", "وزیر", "رپورٹ", "معیشت", "پالیسی", "سپریم کورٹ", "بیان", "ترجمان", 
            "بین الاقوامی", "سائنس", "کانفرنس", "وزیر اعظم", "اداروں", "معاہدہ",
            # Hindi
            "सरकार", "मंत्रालय", "रिपोर्ट", "अर्थव्यवस्था", "नीति", "अदालत", "बयान", "अंतर्राष्ट्रीय", "प्रधानमंत्री",
            # English
            "report", "announcement", "government", "official", "president", "minister", "prime minister",
            "economy", "policy", "court", "statement", "broadcast", "according to", "press release", 
            "spokesperson", "conference", "treaty", "statistics",
            # Arabic
            "حكومة", "تقرير", "بيان", "رسمي", "اقتصاد", "وزير", "مؤتمر", "رئيس", "محكمة",
            # Spanish
            "gobierno", "informe", "oficial", "economía", "política", "declaración", "noticia", "presidente", "ministro"
        ],
        "rate": "+6%",
        "pitch": "-2Hz",
        "volume": "+5%",
        "label": "📰 Authoritative News",
        "reason": "Formal, official report or journalistic structure detected."
    }
}

def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyzes input text and determines the optimal emotion, speed, pitch,
    volume, and breath pacing.
    """
    text_clean = text.strip()
    if not text_clean:
        return {
            "emotion": "natural",
            "label": "🌟 Natural / Story",
            "confidence": 100,
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "reason": "Empty or standard text."
        }

    text_lower = text_clean.lower()
    
    # Score tracking
    scores = {
        "happy": 0.0,
        "sad": 0.0,
        "whisper": 0.0,
        "excited": 0.0,
        "dramatic": 0.0,
        "news": 0.0
    }

    # 1. Word Matching across multilingual vocabulary
    for emotion, data in EMOTION_LEXICONS.items():
        for keyword in data["words"]:
            if keyword in text_lower:
                # Multi-word matches carry higher weight
                weight = 3.0 if " " in keyword else 1.5
                scores[emotion] += weight

    # 2. Punctuation & Style heuristics
    exclamation_count = text_clean.count("!") + text_clean.count("！")
    ellipsis_count = len(re.findall(r'\.{2,}', text_clean)) + text_clean.count("…")
    question_count = text_clean.count("?") + text_clean.count("؟")

    if exclamation_count >= 2:
        scores["excited"] += 2.0 * exclamation_count
        scores["happy"] += 1.0 * exclamation_count

    if ellipsis_count >= 1:
        scores["sad"] += 2.0 * ellipsis_count
        scores["dramatic"] += 2.0 * ellipsis_count
        scores["whisper"] += 1.5 * ellipsis_count

    # Check for ALL CAPS in Latin characters
    latin_words = [w for w in re.findall(r'[A-Za-z]+', text_clean) if len(w) > 2]
    if latin_words:
        caps_words = [w for w in latin_words if w.isupper()]
        if len(caps_words) >= 2:
            scores["excited"] += 3.0

    # Determine highest scoring emotion
    best_emotion, highest_score = max(scores.items(), key=lambda x: x[1])

    # If score is too low or neutral
    if highest_score < 1.5:
        return {
            "emotion": "natural",
            "label": "🌟 Natural / Story",
            "confidence": 85,
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "reason": "Balanced conversational tone detected."
        }

    # Calculate confidence percentage (capped 70% to 98%)
    confidence = min(98, int(70 + (highest_score * 4.5)))

    matched_config = EMOTION_LEXICONS[best_emotion]

    return {
        "emotion": best_emotion,
        "label": matched_config["label"],
        "confidence": confidence,
        "rate": matched_config["rate"],
        "pitch": matched_config["pitch"],
        "volume": matched_config["volume"],
        "reason": matched_config["reason"]
    }
