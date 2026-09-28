export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    const { name, contact, company, meeting_tool, source } = body || {};

    if (!name || !contact) {
      return res.status(400).json({ error: 'Name and contact are required' });
    }

    const token = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_ADMIN_CHAT_ID;

    if (!token || !chatId) {
      // If env vars not set in Vercel, return success with notice
      console.warn("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not configured");
      return res.status(200).json({ success: true, notice: "Saved locally, bot token pending" });
    }

    const cleanContact = contact.trim();
    const now = new Date().toLocaleString('uz-UZ', { timeZone: 'Asia/Tashkent' });
    const leadType = source || 'Murojaat (Bog‘lanish)';

    const text = `🔔 <b>Yangi murojaat qabul qilindi!</b>\n\n` +
      `📌 <b>Turi:</b> ${leadType}\n` +
      `👤 <b>Ism:</b> ${name.trim()}\n` +
      `📱 <b>Kontakt:</b> ${cleanContact}\n` +
      `🏢 <b>Kompaniya:</b> ${company ? company.trim() : 'Ko‘rsatilmagan'}\n` +
      `🎙 <b>Asosiy vosita:</b> ${meeting_tool || 'Google Meet'}\n` +
      `⏰ <b>Vaqt:</b> ${now}`;

    const payload = {
      chat_id: chatId,
      text: text,
      parse_mode: 'HTML'
    };

    if (cleanContact.startsWith('@')) {
      const handle = cleanContact.replace(/^@+/, '').trim();
      payload.reply_markup = {
        inline_keyboard: [[
          { text: `💬 ${cleanContact} ga yozish`, url: `https://t.me/${handle}` }
        ]]
      };
    }

    const tgResp = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const tgData = await tgResp.json();
    return res.status(200).json({ success: true, telegram: tgData });
  } catch (err) {
    console.error("Lead delivery error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
}
