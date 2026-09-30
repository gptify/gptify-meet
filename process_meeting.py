"""
Mirzo - CLI Meeting Audio Processor
Process in-person or recorded meeting audio files of any length (including 1-2 hour meetings).

Usage:
    python process_meeting.py "path/to/meeting_recording.m4a"
    python process_meeting.py "path/to/meeting_recording.m4a" --lang uz --template general
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import ai_engine
import database

def main():
    parser = argparse.ArgumentParser(description="Mirzo - Process Meeting Audio File")
    parser.add_argument("audio_path", help="Path to the audio recording file (.m4a, .mp3, .wav, etc.)")
    parser.add_argument("--title", default=None, help="Custom meeting title (optional)")
    parser.add_argument("--lang", default="uz", choices=["uz", "en", "ru"], help="Language (default: uz)")
    parser.add_argument("--template", default="general", choices=["general", "sales", "weekly", "strategy"], help="Meeting type template")
    parser.add_argument("--send-telegram", action="store_true", help="Send formatted summary to Telegram bot")

    args = parser.parse_args()

    audio_file = Path(args.audio_path)
    if not audio_file.exists():
        print(f"❌ Xatolik: Audio fayl topilmadi: {audio_file}")
        sys.exit(1)

    print(f"🎙️ Mirzo Meeting Processor ishga tushdi...")
    print(f"📁 Fayl: {audio_file.name} ({round(audio_file.stat().st_size / (1024*1024), 2)} MB)")
    print(f"🌐 Til: {args.lang.upper()} | Andaza: {args.template}")
    print("-" * 50)

    # Detect mime
    ext = audio_file.suffix.lower()
    mime_type = "audio/wav"
    if ext in [".m4a", ".mp4", ".aac"]:
        mime_type = "audio/mp4"
    elif ext == ".mp3":
        mime_type = "audio/mp3"
    elif ext == ".webm":
        mime_type = "audio/webm"

    print("⏳ 1/3: Audio tahlil qilinmoqda (siqish va transkripsiya)...")
    start_time = datetime.now()

    result = ai_engine.process_audio_file(
        audio_file,
        mime_type=mime_type,
        template=args.template,
        lang=args.lang
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Transkripsiya va tahlil yakunlandi! ({round(elapsed, 1)} soniya)")
    print("-" * 50)

    title = args.title or result.get("title") or "Yangi uchrashuv bayonnomasi"
    summary = result.get("summary", "")
    decisions = result.get("decisions", [])
    tasks = result.get("tasks", [])
    open_questions = result.get("open_questions", [])
    attendees = result.get("attendees", [])
    transcript = result.get("transcript_segments", [])

    # Save to local database
    database.init_db()
    meeting_id = database.save_meeting(
        title=title,
        date=datetime.now().strftime("%d-%m-%Y %H:%M"),
        duration=f"{round(elapsed // 60)} daqiqa",
        summary=summary,
        attendees=attendees,
        open_questions=open_questions,
        transcript_text=result.get("transcript_text", ""),
        transcript_segments=transcript,
        decisions=decisions,
        tasks=tasks,
        audio_path=str(audio_file.resolve())
    )

    # Output Terminal Summary
    print(f"\n📌 SARLAVHA: {title}")
    print(f"👥 QATNASHUVCHILAR: {', '.join(attendees) if attendees else 'Aniqlanmadi'}")
    print(f"\n📝 ASOSIY XULOSA:\n{summary}\n")

    if decisions:
        print("🎯 QABUL QILINGAN QARORLAR:")
        for d in decisions:
            t_str = f" [{d.get('source_time')}]" if d.get('source_time') else ""
            print(f"  • {d.get('text')}{t_str}")
        print()

    if tasks:
        print("✅ BELGILANGAN VAZIFALAR (ACTION ITEMS):")
        for t in tasks:
            owner = f" ({t.get('owner')})" if t.get('owner') else ""
            due = f" — muddat: {t.get('due_date')}" if t.get('due_date') else ""
            print(f"  [ ] {t.get('text')}{owner}{due}")
        print()

    if open_questions:
        print("❓ OCHIQ SAVOLLAR:")
        for q in open_questions:
            print(f"  • {q}")
        print()

    # Save Markdown file next to audio
    md_output = audio_file.with_name(f"{audio_file.stem}_bayonnoma.md")
    md_lines = [
        f"# {title}",
        f"**Sana:** {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        f"**Qatnashuvchilar:** {', '.join(attendees) if attendees else 'Aniqlanmadi'}",
        "",
        "## Asosiy xulosa",
        summary,
        "",
        "## Qabul qilingan qarorlar",
    ]
    for d in decisions:
        md_lines.append(f"- {d.get('text')} ({d.get('source_time', '')})")
    md_lines.append("")
    md_lines.append("## Vazifalar (Action Items)")
    for t in tasks:
        md_lines.append(f"- [ ] **{t.get('text')}** — Mas'ul: {t.get('owner', 'Belgilanmagan')} | Muddat: {t.get('due_date', '-')}")
    if open_questions:
        md_lines.append("")
        md_lines.append("## Ochiq savollar")
        for q in open_questions:
            md_lines.append(f"- {q}")

    md_lines.append("")
    md_lines.append("## To‘liq suhbat transkripsiyasi")
    for s in transcript:
        md_lines.append(f"**[{s.get('time', '00:00')}] {s.get('speaker', 'So‘zlovchi')}:** {s.get('text')}")

    md_output.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"📄 Tayyor bayonnoma fayli saqlandi: {md_output.resolve()}")

    if args.send_telegram:
        tg_text = ai_engine.format_telegram_summary(result)
        send_res = ai_engine.send_telegram_direct(tg_text)
        if send_res.get("success"):
            print("🚀 Telegram orqali xabar muvaffaqiyatli yuborildi!")
        else:
            print(f"⚠️ Telegram xatosi: {send_res.get('error')}")

    print(f"\n✨ Hammasi tayyor! Mahsulot ID: #{meeting_id}")

if __name__ == "__main__":
    main()
