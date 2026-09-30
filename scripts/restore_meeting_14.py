import os
import sys
import json
import sqlite3
import time
from pathlib import Path
from dotenv import dotenv_values

# Load env keys
env_keys = {}
for p in [Path(".env"), Path("c:/Users/Shuxrat/Documents/AI Newsletter/.env")]:
    if p.exists():
        env_keys.update(dotenv_values(str(p)))

GROQ_API_KEY = env_keys.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("GROQ_API_KEY not found!")
    sys.exit(1)

from groq import Groq
client = Groq(api_key=GROQ_API_KEY)

cache_file = Path("data/normalized_segments_14.json")
normalized_segments = []

if cache_file.exists():
    with open(cache_file, "r", encoding="utf-8") as f:
        normalized_segments = json.load(f)
    print(f"Loaded {len(normalized_segments)} normalized segments from cache!")

if not normalized_segments:
    # Load raw segments
    raw_file = Path("data/raw_meeting_14_segments.json")
    if not raw_file.exists():
        print(f"{raw_file} not found!")
        sys.exit(1)

    with open(raw_file, "r", encoding="utf-8") as f:
        raw_segments = json.load(f)

    print(f"Loaded {len(raw_segments)} raw segments.")

    filtered = []
    for s in raw_segments:
        t = s.get("text", "").strip()
        if any(w in t.lower() for w in ["mirzashuv", "barachafun", "ikrgatf", "nishafu", "aqish , aqish", "qaytta qaldin"]):
            continue
        if any(p in t for p in [
            "Sifatini tekshirish, ovoz yozish",
            "Mirzo, ilova, dizayn, sifatini tekshirish",
            "Mishko, uchrashuv, sifatini tekshirish"
        ]):
            continue
        if t in ["...", "A,", "qalim qalim, qalim, qalim, qalim...", "kala, kala, kala..."]:
            continue
        if len(t) < 3 and not t.isalpha():
            continue
        filtered.append(s)

    print(f"Filtered down to {len(filtered)} real conversation segments.")

    batch_size = 10
    batches = [filtered[i:i + batch_size] for i in range(0, len(filtered), batch_size)]

    system_prompt = """Siz professional audio tahrirchisi va o'zbek adabiy tili bo'yicha muharrirsiz.
Ushbu audio yozuv — Shuxrat va uning hamkori (Sherik) o'rtasidagi 17 daqiqalik jonli B2B uchrashuv.
Mavzu: "D-Med" tibbiy platformasi, xususiy klinikalar uchun tibbiyot CRM/OS tizimi, investor pitch deck, O'zbekistonda server suvereniteti va ma'lumotlar xavfsizligi, e-prescriptions (elektron retseptlar) va MVP topshiriqlari.

VAZIFANGIZ:
1. Xorazm shevasi ('kiliyatdirgan', 'bina', 'diba', 'gorub', 'ishlaydana', 'yok', 'gapiriyapman', 'keliyat', 'unang') va mikrofon xatoliklarini to'g'rilab, ravon, sof va tushunarli o'zbek adabiy tiliga o'giring.
2. Atamalarni to'g'ri yozing: "Dimaet"/"dimet" -> "D-Med", "aydent" -> "iDent", "CRM", "API", "pitch deck", "e-prescription", "roadmap", "telemedicine", "data security".
3. So'zlovchini aniqlang: matn mantig'iga qarab 'Shuxrat' yoki 'Sherik' deb belgilang.
4. Hech qachon 'yaratish' so'zini ishlatmang, uning o'rniga 'qurish', 'ishlab chiqish', 'tuzish', 'joriy qilish' so'zlarini ishlating.
5. Har bir segmentning 'time' maydonini aniq saqlang.

Natijani FAQAT quyidagi JSON formatida qaytaring:
{
  "segments": [
    {"time": "00:00", "speaker": "Shuxrat", "text": "Adabiy to'g'rilangan matn"}
  ]
}"""

    for idx, b in enumerate(batches):
        print(f"Normalizing batch {idx + 1}/{len(batches)} ({len(b)} segments)...", flush=True)
        prompt_user = f"Quyidagi segmentlarni adabiy o'zbek tiliga o'giring va so'zlovchini (Shuxrat / Sherik) belgilang:\n{json.dumps(b, ensure_ascii=False)}"
        
        success = False
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_user}
                    ],
                    temperature=0.1,
                    max_tokens=650,
                    response_format={"type": "json_object"}
                )
                raw_text = resp.choices[0].message.content.strip()
                data = json.loads(raw_text)
                b_res = data.get("segments", [])
                if isinstance(b_res, list) and len(b_res) > 0:
                    for i_s, s_item in enumerate(b):
                        if i_s < len(b_res):
                            b_res[i_s]["time"] = s_item["time"]
                            normalized_segments.append(b_res[i_s])
                        else:
                            normalized_segments.append(s_item)
                    success = True
                    break
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed for batch {idx + 1}: {e}", flush=True)
                time.sleep(3.0)

        if not success:
            normalized_segments.extend(b)

        time.sleep(1.5)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(normalized_segments, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(normalized_segments)} segments to cache!", flush=True)

# Rebuild full transcript text
full_text = "\n".join([f"[{s['time']}] {s['speaker']}: {s['text']}" for s in normalized_segments])

# Re-run meeting analysis with Qwen
print("Generating structured executive meeting intelligence...", flush=True)
analysis_system = """Siz Mirzo (mirzo.gptify.uz) tizimining bosh uchrashuv tahlilchisisiz.
Berilgan uchrashuv transkripsiyasini tahlil qiling va O'ZBEK tilida to'liq, mukammal va aniq JSON bayonnoma tuzing.

TALABLAR:
1. "yaratish" so'zini aslo ishlatmang, uning o'rniga "qurish", "ishlab chiqish", "tuzish", "shakllantirish" so'zlaridan foydalaning.
2. Hurmat bilan "Siz" uslubida yozing.
3. Ishtirokchilar: Shuxrat, Hamkor (Sherik).
4. Asosiy mazmun: D-Med platformasini o'rganish, davlat poliklinikalari vs xususiy klinikalar segmentatsiyasi, elektron retseptlar (e-prescriptions) integratsiyasi va qonuniy me'yorlar, O'zbekistonda server suvereniteti va tibbiy ma'lumotlar xavfsizligi, investorlar uchun pitch deckni to'ldirish, MVP navbatdagi qadamlari.
5. Har bir qaror (decisions) va vazifa (tasks) aniq vaqtdagi manbaga (source_time), mas'ulga va muddatga ega bo'lsin.

Javobni FAQAT quyidagi JSON formatida bering:
{
  "title": "D-Med va Xususiy Klinikalar Tizimi: Strategiya va Pitch Deck Muhokamasi",
  "summary": "1-3 jumlada qisqa mazmun",
  "attendees": ["Shuxrat", "Hamkor"],
  "open_questions": [
    "Ochiq savol 1",
    "Ochiq savol 2"
  ],
  "decisions": [
    {"text": "Qaror matni", "source_time": "02:33"}
  ],
  "tasks": [
    {"text": "Topshiriq matni", "owner": "Shuxrat yoki Hamkor", "due_date": "Belgilangan muddat", "completed": 0}
  ]
}"""

for attempt in range(3):
    try:
        resp_analysis = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": analysis_system},
                {"role": "user", "content": f"Quyidagi to'liq suhbat transkripsiyasini tahlil qiling:\n\n{full_text}"}
            ],
            temperature=0.1,
            max_tokens=850,
            response_format={"type": "json_object"}
        )
        meeting_data = json.loads(resp_analysis.choices[0].message.content.strip())
        break
    except Exception as e:
        print(f"Analysis attempt {attempt + 1} failed: {e}", flush=True)
        time.sleep(4.0)

title = meeting_data.get("title", "D-Med va Xususiy Klinikalar Tizimi Strategiyasi")
summary = meeting_data.get("summary", "")
attendees = json.dumps(meeting_data.get("attendees", ["Shuxrat", "Hamkor"]), ensure_ascii=False)
open_questions = json.dumps(meeting_data.get("open_questions", []), ensure_ascii=False)
decisions = json.dumps(meeting_data.get("decisions", []), ensure_ascii=False)
tasks_list = meeting_data.get("tasks", [])
segments_json = json.dumps(normalized_segments, ensure_ascii=False)

# Update Meeting #14 in DB
db_path = Path("data/gptify_meet.db")
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# 1. Update meetings row
cur.execute("""
    UPDATE meetings
    SET title = ?,
        summary = ?,
        transcript_text = ?,
        transcript_segments = ?,
        attendees = ?,
        decisions = ?,
        open_questions = ?
    WHERE id = 14
""", (title, summary, full_text, segments_json, attendees, decisions, open_questions))

# 2. Clear old tasks for meeting 14 and insert new ones
cur.execute("DELETE FROM tasks WHERE meeting_id = 14")
for t in tasks_list:
    cur.execute("""
        INSERT INTO tasks (meeting_id, text, owner, due_date, completed)
        VALUES (14, ?, ?, ?, ?)
    """, (t.get("text", ""), t.get("owner", "Belgilanmagan"), t.get("due_date", "Tez orada"), 0))

conn.commit()
conn.close()
print("Updated Meeting #14 and tasks in gptify_meet.db successfully!", flush=True)

# Also generate a markdown report
md_lines = [
    f"# 📋 {title}",
    f"**Sana:** 2026-09-30 | **Davomiyligi:** 17 daqiqa | **Ishtirokchilar:** Shuxrat, Hamkor",
    "",
    "## 💡 Qisqacha Mazmuni va Xulosa",
    summary,
    "",
    "## ✅ Qabul Qilingan Asosiy Qarorlar",
]
for d in meeting_data.get("decisions", []):
    st = f" `[{d.get('source_time', '')}]`" if d.get('source_time') else ""
    md_lines.append(f"- **{d.get('text', '')}**{st}")

md_lines.extend([
    "",
    "## 📌 Topshiriqlar va Keyingi Qadamlar",
])
for t in tasks_list:
    md_lines.append(f"- [ ] **{t.get('text', '')}** — *Mas'ul:* {t.get('owner', 'Belgilanmagan')} | *Muddat:* {t.get('due_date', 'Tez orada')}")

md_lines.extend([
    "",
    "## ❓ Ochiq Qolgan Savollar",
])
for q in meeting_data.get("open_questions", []):
    md_lines.append(f"- {q}")

md_lines.extend([
    "",
    "## 📝 To'liq va Tozalangan Transkripsiya (Adabiy O'zbek Tilida)",
    ""
])
for s in normalized_segments:
    md_lines.append(f"> **[{s['time']}] {s['speaker']}:** {s['text']}")

md_content = "\n".join(md_lines)
report_path = Path("data/meeting_14_bayonnoma.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"Saved executive meeting minutes to {report_path}!", flush=True)
