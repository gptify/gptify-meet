"""
GPTify Meet - Production Application Server
FastAPI backend with local SQLite persistence, audio processing, and Telegram delivery.
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx

import database
import ai_engine

app = FastAPI(title="GPTify Meet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
STATIC_DIR = BASE_DIR / "static"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Initialize database
database.init_db()

class ProcessTextRequest(BaseModel):
    title: Optional[str] = "Yangi uchrashuv"
    text: str
    duration: Optional[str] = None
    template: Optional[str] = "general"
    lang: Optional[str] = "uz"

def format_date_for_lang(dt: datetime, lang: str = "uz") -> str:
    months_uz = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    months_ru = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    
    if lang == "en":
        return f"{months_en[dt.month-1]} {dt.day}, {dt.year}"
    elif lang == "ru":
        return f"{dt.day} {months_ru[dt.month-1]} {dt.year} г."
    return f"{dt.day}-{months_uz[dt.month-1]}, {dt.year}"


class RenameSpeakerRequest(BaseModel):
    old_speaker: str
    new_speaker: str

class AddTaskRequest(BaseModel):
    text: str
    owner: Optional[str] = "Mas’ul belgilanmagan"
    due_date: Optional[str] = "Bugun"

class UpdateMeetingRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None

class TelegramShareRequest(BaseModel):
    meeting_id: int
    chat_id: Optional[str] = None
    direct: Optional[bool] = False

class SettingUpdate(BaseModel):
    key: str
    value: str

@app.get("/api/meetings")
def list_meetings(q: Optional[str] = None):
    return database.get_all_meetings(query=q)

@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: int):
    m = database.get_meeting_by_id(meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Uchrashuv topilmadi.")
    return m

@app.post("/api/meetings/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    duration: Optional[str] = Form(None),
    template: Optional[str] = Form("general"),
    lang: Optional[str] = Form("uz")
):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        if not suffix:
            suffix = ".wav"
        file_id = f"rec_{uuid.uuid4().hex[:10]}{suffix}"
        target_path = RECORDINGS_DIR / file_id
        
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        mime_type = file.content_type or "audio/wav"
        if "webm" in mime_type or suffix == ".webm":
            mime_type = "audio/webm"
        elif "mp3" in mime_type or suffix == ".mp3":
            mime_type = "audio/mp3"
        elif "m4a" in mime_type or suffix == ".m4a":
            mime_type = "audio/mp4"

        # Process with AI Engine with custom template and language
        selected_lang = lang or "uz"
        extracted = ai_engine.process_audio_file(target_path, mime_type=mime_type, template=template or "general", lang=selected_lang)
        
        default_titles = {"uz": "Audio uchrashuv", "en": "Audio Meeting", "ru": "Аудиовстреча"}
        meeting_title = title or extracted.get("title") or default_titles.get(selected_lang, "Audio uchrashuv")
        
        now = datetime.now()
        date_str = format_date_for_lang(now, selected_lang)
        
        default_dur = {"uz": "12 daqiqa", "en": "12 minutes", "ru": "12 минут"}
        dur_str = duration or default_dur.get(selected_lang, "12 daqiqa")
        
        meeting_id = database.save_meeting(
            title=meeting_title,
            date=date_str,
            duration=dur_str,
            summary=extracted.get("summary", ""),
            attendees=extracted.get("attendees", []),
            open_questions=extracted.get("open_questions", []),
            transcript_text=extracted.get("transcript_text", ""),
            transcript_segments=extracted.get("transcript_segments", []),
            decisions=extracted.get("decisions", []),
            tasks=extracted.get("tasks", []),
            audio_path=str(target_path)
        )
        
        return database.get_meeting_by_id(meeting_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio qayta ishlashda xatolik: {str(e)}")

@app.post("/api/meetings/process-text")
def process_text_meeting(req: ProcessTextRequest):
    selected_lang = req.lang or "uz"
    extracted = ai_engine.process_text_transcript(req.text, req.title or "Yangi uchrashuv", template=req.template or "general", lang=selected_lang)
    now = datetime.now()
    date_str = format_date_for_lang(now, selected_lang)
    
    default_dur = {"uz": "15 daqiqa", "en": "15 minutes", "ru": "15 минут"}
    meeting_id = database.save_meeting(
        title=extracted.get("title") or req.title,
        date=date_str,
        duration=req.duration or default_dur.get(selected_lang, "15 daqiqa"),
        summary=extracted.get("summary", ""),
        attendees=extracted.get("attendees", []),
        open_questions=extracted.get("open_questions", []),
        transcript_text=extracted.get("transcript_text", ""),
        transcript_segments=extracted.get("transcript_segments", []),
        decisions=extracted.get("decisions", []),
        tasks=extracted.get("tasks", [])
    )
    return database.get_meeting_by_id(meeting_id)

@app.patch("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int):
    updated = database.toggle_task(task_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi.")
    return updated

@app.post("/api/meetings/{meeting_id}/tasks")
def add_new_task(meeting_id: int, req: AddTaskRequest):
    t = database.add_task(meeting_id, text=req.text, owner=req.owner or "Mas’ul belgilanmagan", due_date=req.due_date or "Bugun")
    return t

@app.delete("/api/tasks/{task_id}")
def delete_task_endpoint(task_id: int):
    success = database.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi.")
    return {"success": True}

@app.post("/api/meetings/{meeting_id}/rename-speaker")
def rename_speaker_endpoint(meeting_id: int, req: RenameSpeakerRequest):
    success = database.update_speaker_name(meeting_id, req.old_speaker, req.new_speaker)
    if not success:
        raise HTTPException(status_code=404, detail="Uchrashuv topilmadi.")
    return database.get_meeting_by_id(meeting_id)

@app.put("/api/meetings/{meeting_id}")
def update_meeting_endpoint(meeting_id: int, req: UpdateMeetingRequest):
    success = database.update_meeting(meeting_id, title=req.title, summary=req.summary)
    if not success:
        raise HTTPException(status_code=404, detail="Uchrashuv topilmadi.")
    return database.get_meeting_by_id(meeting_id)

@app.delete("/api/meetings/{meeting_id}")
def delete_meeting_endpoint(meeting_id: int):
    success = database.delete_meeting(meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Uchrashuv topilmadi.")
    return {"success": True, "message": "Uchrashuv o'chirildi."}

@app.post("/api/telegram/share")
def share_telegram(req: TelegramShareRequest):
    meeting = database.get_meeting_by_id(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Uchrashuv topilmadi.")
    
    formatted_text = ai_engine.format_telegram_message(meeting)
    
    if req.direct:
        res = ai_engine.send_telegram_direct(formatted_text, chat_id=req.chat_id)
        return {
            "success": res.get("success"),
            "message": res.get("message") or res.get("error"),
            "formatted_text": formatted_text
        }
    else:
        import urllib.parse
        encoded_text = urllib.parse.quote(formatted_text)
        deep_link = f"https://t.me/share/url?url=&text={encoded_text}"
        return {
            "success": True,
            "deep_link": deep_link,
            "formatted_text": formatted_text
        }

@app.get("/api/settings")
def get_app_settings():
    return database.get_settings()

@app.get("/api/audio/{meeting_id}")
def get_meeting_audio(meeting_id: int):
    m = database.get_meeting_by_id(meeting_id)
    if not m or not m.get("audio_path"):
        raise HTTPException(status_code=404, detail="Audio fayl topilmadi.")
    p = Path(m["audio_path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="Audio fayl diskda mavjud emas.")
    
    media_type = "audio/wav"
    if p.suffix == ".webm": media_type = "audio/webm"
    elif p.suffix == ".mp3": media_type = "audio/mp3"
    elif p.suffix == ".m4a": media_type = "audio/mp4"
    return FileResponse(str(p), media_type=media_type)

@app.post("/api/settings")
def update_app_setting(req: SettingUpdate):
    database.save_setting(req.key, req.value)
    return {"success": True}

class CreateLeadRequest(BaseModel):
    name: str
    contact: str
    company: Optional[str] = None
    meeting_tool: Optional[str] = "Google Meet"

@app.post("/api/leads")
async def create_lead(req: CreateLeadRequest):
    if not req.name.strip() or not req.contact.strip():
        raise HTTPException(status_code=400, detail="Ism va kontakt kiritilishi shart.")
    lead_id = database.save_lead(
        name=req.name.strip(),
        contact=req.contact.strip(),
        company=req.company.strip() if req.company else "",
        meeting_tool=req.meeting_tool or "Google Meet"
    )
    # Send Telegram notification if credentials available
    try:
        if ai_engine.TELEGRAM_BOT_TOKEN and ai_engine.TELEGRAM_DEFAULT_CHAT:
            contact_clean = req.contact.strip()
            msg = (
                f"🔔 <b>Yangi mijoz demoga yozildi!</b>\n\n"
                f"👤 <b>Ism:</b> {req.name.strip()}\n"
                f"📱 <b>Kontakt:</b> {contact_clean}\n"
                f"🏢 <b>Kompaniya:</b> {req.company.strip() if req.company else 'Ko‘rsatilmagan'}\n"
                f"🎙 <b>Vosita:</b> {req.meeting_tool or 'Google Meet'}\n"
                f"⏰ <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"🤖 <i>Manzil: @GPTifyUzAdminbot orqali qabul qilindi</i>"
            )
            payload = {
                "chat_id": ai_engine.TELEGRAM_DEFAULT_CHAT,
                "text": msg,
                "parse_mode": "HTML"
            }
            if contact_clean.startswith("@"):
                tg_user = contact_clean.lstrip("@").strip()
                payload["reply_markup"] = {
                    "inline_keyboard": [[
                        {"text": f"💬 {contact_clean} ga yozish", "url": f"https://t.me/{tg_user}"}
                    ]]
                }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{ai_engine.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json=payload
                )
    except Exception as e:
        print(f"Telegram notification error: {e}")
    return {"success": True, "lead_id": lead_id}

@app.get("/api/leads")
def list_leads():
    return database.get_all_leads()

# Serve static frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "GPTify Meet Server Running", "version": "1.0.0"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
