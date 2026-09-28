"""
GPTify Meet - High-Accuracy Audio & Meeting Intelligence Engine
Primary: Gemini 3.8 Flash (native Uzbek dialect understanding)
Secondary: Groq Whisper-large-v3 with Uzbek language biasing and context prompt.
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from dotenv import dotenv_values

ENV_KEYS = {}
for env_candidate in [
    Path(__file__).parent / ".env",
    Path("c:/Users/Shuxrat/Documents/AI Newsletter/.env")
]:
    if env_candidate.exists():
        ENV_KEYS.update(dotenv_values(str(env_candidate)))

GROQ_API_KEY = ENV_KEYS.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = ENV_KEYS.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = ENV_KEYS.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_DEFAULT_CHAT = ENV_KEYS.get("TELEGRAM_GROUP_ID") or ENV_KEYS.get("TELEGRAM_ADMIN_CHAT_ID")

SYSTEM_INSTRUCTIONS = {
    "uz": """Siz GPTify Meet tizimining professional AI bayonnoma ekspertisiz.
Vazifangiz: uchrashuv yoki audio transkripsiyasini tahlil qilib, o'zbek tilida aniq, qisqa va qat'iy tuzilmali (structured JSON) bayonnoma shakllantirish.

TALABLAR:
1. Til: Mutlaqo sof va tushunarli o'zbek tili. Murojaat va bayonnomalarda hurmat ohangida ("Siz") bo'lsin.
2. "yaratish" so'zini aslo ishlatmang, uning o'rniga "qurish", "ishlab chiqish", "tuzish", "shakllantirish" yoki "tekshirish" so'zlarini ishlating.
3. To'qib chiqarmang (no hallucination). Audio matnida nima aytilgan bo'lsa, faqat shunga asoslaning.
4. Natijani FAQAT quyidagi JSON formatida qaytaring, boshqa hech qanday izoh qo'shmang:
{
  "title": "Uchrashuvning qisqa mazmunli nomi",
  "summary": "1-3 jumlada asosiy natija va xulosa",
  "attendees": ["Ism yoki unvon"],
  "open_questions": ["Hali ochiq qolgan savol yoki masala"],
  "decisions": [
    {"text": "Qabul qilingan aniq qaror yoki kelishuv", "source_time": "00:05"}
  ],
  "tasks": [
    {"text": "Bajarilishi kerak bo'lgan vazifa yoki keyingi qadam", "owner": "Mas'ul ism", "due_date": "Belgilangan muddat", "completed": 0}
  ]
}
""",
    "en": """You are a senior AI meeting intelligence expert for GPTify Meet.
Your task: Analyze the meeting transcript or audio notes and generate a concise, highly structured meeting summary, key decisions, and actionable next steps in English.

REQUIREMENTS:
1. Language: Clear, professional, concise English.
2. Grounded facts: Do not hallucinate or extrapolate beyond what was actually discussed.
3. Output STRICTLY as JSON with no extra commentary:
{
  "title": "Concise and descriptive meeting title",
  "summary": "1-3 sentences capturing the executive summary and key outcome",
  "attendees": ["Name or role"],
  "open_questions": ["Unresolved question or open issue"],
  "decisions": [
    {"text": "Specific decision or agreement made", "source_time": "00:05"}
  ],
  "tasks": [
    {"text": "Action item or task to complete", "owner": "Assignee name", "due_date": "Deadline or date", "completed": 0}
  ]
}
""",
    "ru": """Вы профессиональный эксперт по анализу встреч системы GPTify Meet.
Ваша задача: проанализировать транскрипцию или аудиозапись встречи и составить четкий, структурированный протокол на русском языке.

ТРЕБОВАНИЯ:
1. Язык: Грамотный, деловой и ясный русский язык.
2. Без домыслов: опирайтесь строго на фактически сказанные в аудио слова.
3. Ответ СТРОГО в формате JSON без каких-либо вводных слов или пояснений:
{
  "title": "Краткое емкое название встречи",
  "summary": "1-3 предложения с ключевыми итогами и выводами",
  "attendees": ["Имя или роль"],
  "open_questions": ["Нерешенный вопрос или тема для обсуждения"],
  "decisions": [
    {"text": "Принятое решение или договоренность", "source_time": "00:05"}
  ],
  "tasks": [
    {"text": "Задача или следующий шаг", "owner": "Ответственный", "due_date": "Срок", "completed": 0}
  ]
}
"""
}
SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTIONS["uz"]


def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def transcribe_with_gemini(audio_path: Path, mime_type: str) -> Optional[Dict[str, Any]]:
    """Native Gemini 3.8 Flash audio transcription with deep Uzbek understanding."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=GEMINI_API_KEY)
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = """Ushbu audioda inson o'zbek tilida (GPTify Meet, uchrashuv, biznes yoki texnik sinov mavzusida) gapirmoqda.
Iltimos, audio yozuvni to'liq tinglab, aniq so'zma-so'z o'zbekcha transkripsiyasini yozing.
So'zlovchi aynan nima degan bo'lsa, so'zma-so'z to'g'ri o'zbek adabiy tilida yozing. Hech qanday boshqa izohsiz, faqat transkripsiyani qaytaring."""

        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[audio_part, prompt]
        )
        text = resp.text.strip()
        if text.startswith("Audio yozuvning matni:"):
            text = text.replace("Audio yozuvning matni:", "").strip()
        if text:
            # Build clean segments
            segments = []
            sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]
            for i, sent in enumerate(sentences):
                segments.append({
                    "time": f"00:{i*5:02d}",
                    "speaker": "So‘zlovchi",
                    "text": sent
                })
            return {"text": text, "segments": segments}
    except Exception as e:
        print(f"Gemini transcription error: {e}")
    return None

def transcribe_with_groq_whisper(audio_path: Path, lang: str = "uz") -> Optional[Dict[str, Any]]:
    """Groq Whisper-large-v3 transcription with explicit language bias and domain prompt."""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt_map = {
            "uz": "O‘zbek tilida so‘zlashuv: uchrashuv, sinov, mikrofon, ovoz yozish, GPTify Meet, ilova, dizayn, sifatini tekshirish...",
            "en": "Business meeting and discussion: project updates, decisions, deliverables, action items, GPTify Meet...",
            "ru": "Деловая встреча и обсуждение: проект, задачи, сроки, ответственные, решения, GPTify Meet..."
        }
        whisper_lang = lang if lang in ["uz", "en", "ru"] else "uz"
        whisper_prompt = prompt_map.get(whisper_lang, prompt_map["uz"])

        with open(audio_path, "rb") as f:
            tr = client.audio.transcriptions.create(
                file=(audio_path.name, f.read()),
                model="whisper-large-v3",
                language=whisper_lang,
                prompt=whisper_prompt,
                response_format="verbose_json"
            )
        
        segments = []
        raw_segments = getattr(tr, "segments", []) or []
        for s in raw_segments:
            start_sec = s.get("start", 0) if isinstance(s, dict) else getattr(s, "start", 0)
            txt = s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")
            if txt.strip():
                speaker_label = "Speaker" if lang == "en" else ("Спикер" if lang == "ru" else "So‘zlovchi")
                segments.append({
                    "time": format_timestamp(start_sec),
                    "speaker": speaker_label,
                    "text": txt.strip()
                })
        
        full_text = getattr(tr, "text", "").strip()
        if not segments and full_text:
            speaker_label = "Speaker" if lang == "en" else ("Спикер" if lang == "ru" else "So‘zlovchi")
            segments.append({"time": "00:00", "speaker": speaker_label, "text": full_text})

        return {"text": full_text, "segments": segments}
    except Exception as e:
        print(f"Groq Whisper transcription error: {e}")
    return None

TEMPLATE_INSTRUCTIONS = {
    "general": {
        "uz": "Umumiy uchrashuv tahlili: asosiy natijalar, qat'iy qarorlar va topshiriqlarni ajrating.",
        "en": "General meeting summary: extract core outcomes, decisive agreements, and next action items.",
        "ru": "Общий анализ встречи: выделите ключевые итоги, четкие решения и задачи."
    },
    "sales": {
        "uz": "Savdo va mijoz bilan muzokara tahlili: mijozning asosiy muammo/ehtiyoji, narx/budjet va keyingi qadamlar.",
        "en": "Sales call analysis: customer needs, budget, objections, and next touchpoint.",
        "ru": "Анализ переговоров о продажах: потребности клиента, бюджет, возражения и следующий контакт."
    },
    "weekly": {
        "uz": "Ichki jamoaviy haftalik sync: erishilgan natijalar, blokerlar va keyingi hafta rejalari.",
        "en": "Internal team weekly sync: accomplishments, blockers, and goals for next week.",
        "ru": "Еженедельный синк команды: результаты, блокеры и цели на следующую неделю."
    },
    "strategy": {
        "uz": "Boshqaruv va strategik yig'ilish: kompaniya maqsadlari, strategik qarorlar va xatarlar.",
        "en": "Executive strategy meeting: corporate goals, strategic decisions, and risk factors.",
        "ru": "Стратегическая встреча: цели компании, стратегические решения и риски."
    }
}

def analyze_transcript(text: str, segments: List[Dict[str, str]], template: str = "general", lang: str = "uz") -> Dict[str, Any]:
    """Analyzes transcribed text and produces structured meeting intelligence in specified language."""
    tpl = TEMPLATE_INSTRUCTIONS.get(template, TEMPLATE_INSTRUCTIONS["general"])
    context_hint = tpl.get(lang, tpl.get("uz", ""))
    base_sys = SYSTEM_INSTRUCTIONS.get(lang, SYSTEM_INSTRUCTIONS["uz"])
    active_sys_instruction = f"{base_sys}\n\nSPECIAL TEMPLATE GUIDANCE:\n{context_hint}"


    # 1. Try Groq Qwen (ultra-fast and reliable)
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": active_sys_instruction},
                    {"role": "user", "content": f"Quyidagi audio transkripsiyasini tahlil qiling:\n\n{text}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw = resp.choices[0].message.content.strip()
            data = json.loads(raw)
            return build_final_structure(data, text, segments)
        except Exception as e:
            print(f"Groq Qwen analysis error: {e}")

    # 2. Try Gemini 3.8 Flash
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GEMINI_API_KEY)
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=f"Quyidagi audio transkripsiyasini tahlil qiling va qat'iy talab qilingan JSON formatida qaytaring:\n\n{text}",
                config=types.GenerateContentConfig(
                    system_instruction=active_sys_instruction,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            clean = clean_json_string(resp.text)
            data = json.loads(clean)
            return build_final_structure(data, text, segments)
        except Exception as e:
            print(f"Gemini text analysis error: {e}")

    return build_final_structure({}, text, segments)

def normalize_segments(segments: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Cleans up colloquial phonetics, dialect quirks, speech-to-text slips,
    multilingual phrases, and punctuates raw speech segments into polished,
    grammatically correct literary text.
    """
    if not segments:
        return segments

    prompt = """Siz professional transkripsiya va til muharririsiz.
Foydalanuvchi jonli audio yozuvda gapirgan va xom fonetik transkripsiya olingan.
Vazifangiz: har bir segmentdagi nutqni grammatik jihatdan to'g'ri, adabiy va aniq shaklga keltirish:
1. Shevaviy, fonetik va orfoepik buzilishlarni to'g'rilang (masalan: 'bygen' -> 'bugun', 'kemiyapti/kemi yapti' -> 'kelmayapti', 'nama xisami' -> 'nima qilsam', 'uju' -> 'uje', 'boldi' -> 'bo‘ldi').
2. Boshqa tildagi (nemischa, inglizcha, ruscha) so'z yoki iboralarni to'g'ri orfografiyada yozing (masalan: 'Ich mis shlafen' -> 'Ich muss schlafen', 'Uzbek tili, ingilisli, nemisli, ruschi' -> 'O‘zbek tili, ingliz tili, nemis tili, rus tili').
3. Tinish belgilarini va bosh harflarni to'g'ri qo'ying.
4. Har bir segmentning 'time' va 'speaker' maydonlarini saqlang.

Natijani FAQAT quyidagi JSON formatida qaytaring:
{
  "segments": [
    {"time": "00:00", "speaker": "So‘zlovchi", "text": "To'g'rilangan matn"}
  ]
}"""

    # 1. Try Groq Qwen (super fast)
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(segments, ensure_ascii=False)}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content.strip())
            if data.get("segments") and len(data["segments"]) == len(segments):
                return data["segments"]
        except Exception as e:
            print(f"Normalization with Groq error: {e}")

    # 2. Try Gemini
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GEMINI_API_KEY)
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=f"{prompt}\n\nSegmentlar:\n{json.dumps(segments, ensure_ascii=False)}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            data = json.loads(clean_json_string(resp.text))
            if data.get("segments") and len(data["segments"]) == len(segments):
                return data["segments"]
        except Exception as e:
            print(f"Normalization with Gemini error: {e}")

    return segments

def process_audio_file(audio_path: Path, mime_type: str = "audio/wav", template: str = "general", lang: str = "uz") -> Dict[str, Any]:
    """
    Complete audio pipeline:
    1. Audio-to-text via Gemini / Groq Whisper (with language biasing).
    2. Grammar & dialect normalization pass into literary text.
    3. Structured meeting analysis into summary, decisions, tasks in requested language.
    """
    transcription = None
    if lang == "uz":
        transcription = transcribe_with_gemini(audio_path, mime_type)
    if not transcription or not transcription.get("text"):
        transcription = transcribe_with_groq_whisper(audio_path, lang=lang)

    if not transcription or not transcription.get("text"):
        fallback_titles = {"uz": "Ovozli yozuv", "en": "Voice Recording", "ru": "Голосовая запись"}
        fallback_summaries = {
            "uz": "Audio yozuvdan so'zlar aniqlanmadi.",
            "en": "No clear speech detected in the audio recording.",
            "ru": "В аудиозаписи не обнаружена четкая речь."
        }
        return {
            "title": fallback_titles.get(lang, fallback_titles["uz"]),
            "summary": fallback_summaries.get(lang, fallback_summaries["uz"]),
            "attendees": ["User"] if lang == "en" else (["Пользователь"] if lang == "ru" else ["Foydalanuvchi"]),
            "open_questions": [],
            "decisions": [],
            "tasks": [],
            "transcript_segments": [{"time": "00:00", "speaker": "Audio", "text": fallback_summaries.get(lang, fallback_summaries["uz"])}],
            "transcript_text": fallback_summaries.get(lang, fallback_summaries["uz"])
        }

    raw_segments = transcription.get("segments") or []
    clean_segments = normalize_segments(raw_segments)
    clean_full_text = " ".join([s["text"] for s in clean_segments]) if clean_segments else transcription["text"]

    return analyze_transcript(clean_full_text, clean_segments, template=template, lang=lang)

def process_text_transcript(raw_text: str, title_hint: str = "Yangi uchrashuv", template: str = "general", lang: str = "uz") -> Dict[str, Any]:
    speaker_name = "Speaker" if lang == "en" else ("Спикер" if lang == "ru" else "So‘zlovchi")
    segments = [{"time": "00:00", "speaker": speaker_name, "text": raw_text}]
    return analyze_transcript(raw_text, segments, template=template, lang=lang)

def build_final_structure(data: Dict[str, Any], full_text: str, segments: List[Dict[str, str]]) -> Dict[str, Any]:
    title = data.get("title")
    if not title or title.strip() == "":
        title = "Ovozli suhbat tahlili"
    
    summary = data.get("summary")
    if not summary or summary.strip() == "":
        summary = full_text[:200] + "..." if len(full_text) > 200 else full_text

    return {
        "title": title,
        "summary": summary,
        "attendees": data.get("attendees") or ["Uchrashuv ishtirokchilari"],
        "open_questions": data.get("open_questions") or [],
        "decisions": data.get("decisions") or [],
        "tasks": data.get("tasks") or [],
        "transcript_segments": segments if segments else [{"time": "00:00", "speaker": "So‘zlovchi", "text": full_text}],
        "transcript_text": full_text
    }

def clean_json_string(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```json"):
        s = s[7:]
    if s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()

def format_telegram_message(meeting: Dict[str, Any]) -> str:
    title = meeting.get("title", "Uchrashuv bayonnomasi")
    date = meeting.get("date", "")
    summary = meeting.get("summary", "")
    decisions = meeting.get("decisions", [])
    tasks = meeting.get("tasks", [])
    open_questions = meeting.get("open_questions", [])

    lines = [
        f"📋 *{title}* ({date})",
        "",
        f"💡 *Qisqacha xulosa:*\n{summary}",
        ""
    ]

    if decisions:
        lines.append("✅ *Asosiy qarorlar:*")
        for d in decisions:
            lines.append(f"• {d.get('text', '')}")
        lines.append("")

    if tasks:
        lines.append("📌 *Vazifalar va mas’ullar:*")
        for t in tasks:
            status = "✓" if t.get("completed") else "▫️"
            owner = t.get("owner", "Belgilanmagan")
            due = t.get("due_date", "")
            due_str = f" ({due})" if due else ""
            lines.append(f"{status} {t.get('text', '')} — *{owner}*{due_str}")
        lines.append("")

    if open_questions:
        lines.append("❓ *Ochiq savollar:*")
        for q in open_questions:
            lines.append(f"• {q}")
        lines.append("")

    lines.append("🔒 _GPTify Meet orqali lokal qayta ishlangan._")
    return "\n".join(lines)

def send_telegram_direct(text: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    token = TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_DEFAULT_CHAT
    if not token or not target_chat:
        return {"success": False, "error": "Telegram bot token yoki Chat ID sozlanmagan."}
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = httpx.post(url, json={
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10.0)
        res_data = resp.json()
        if res_data.get("ok"):
            return {"success": True, "message": "Xabar Telegramga yuborildi."}
        else:
            return {"success": False, "error": res_data.get("description", "Xatolik yuz berdi")}
    except Exception as e:
        return {"success": False, "error": str(e)}
