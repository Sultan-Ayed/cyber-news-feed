"""
يجلب أحدث أخبار الأمن السيبراني من عدة مصادر RSS، يبسّطها ويصيغها بأسلوب منشور
LinkedIn شخصي (إنجليزي أعلى / عربي أسفل)، يستخرج صورة مرتبطة بالخبر، ويحفظها في
data/posts.json — بدون الحاجة لأي مفتاح API (الترجمة عبر مكتبة deep-translator المجانية).
"""

import feedparser
import requests
import re
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import os
import hashlib
from datetime import datetime, timezone

# ------------------------------------------------------------------
# عدّل هذا القسم ليصير المنشور "خاص فيك" — يظهر كتوقيع بآخر كل منشور
# ------------------------------------------------------------------
AUTHOR_NAME_EN = "Sultan Ayed"
AUTHOR_TITLE_EN = "Cybersecurity Trainer"
AUTHOR_NAME_AR = "سلطان عايد"
AUTHOR_TITLE_AR = "مدرّب أمن سيبراني"

FEEDS = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "SecurityWeek": "https://www.securityweek.com/feed/",
}

DATA_FILE = "data/posts.json"
MAX_POSTS = 200          # أقصى عدد منشورات يحتفظ بها الملف
MAX_NEW_PER_RUN = 6       # حد أقصى للمنشورات الجديدة بكل تشغيل (يحمي من حظر الترجمة المجانية)
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80"

# ------------------------------------------------------------------
# بنك "الرأي الخبير" — يعطي كل خبر بُعد تبسيطي وشخصي حسب نوعه، بدون أي API
# ------------------------------------------------------------------
CATEGORIES = {
    "ransomware": {
        "keywords": ["ransomware", "ransom", "extortion", "encrypt"],
        "why_en": [
            "Ransomware doesn't just lock your files — it locks your entire operation, and recovery usually costs more than the ransom itself.",
            "What used to take attackers weeks now takes hours, because ransomware crews increasingly buy ready-made access instead of building it.",
        ],
        "why_ar": [
            "برامج الفدية ما تقفل بس ملفاتك، تقفل عملك بالكامل، والتعافي منها غالبًا يكلف أكثر من الفدية نفسها.",
            "اللي كان يحتاج أسابيع من المهاجمين صار يصير بساعات، لأن عصابات الفدية صارت تشتري صلاحيات دخول جاهزة بدل ما تبنيها.",
        ],
        "tip_en": [
            "Test your backups today, not the day you need them — an untested backup is a hope, not a plan.",
            "Segment your network. If ransomware can't move laterally, it can't hold the whole organization hostage.",
        ],
        "tip_ar": [
            "اختبر نسخك الاحتياطية اليوم، لا تنتظر يوم تحتاجها — النسخة غير المجرّبة أمنية، مو خطة حماية.",
            "قسّم شبكتك لأجزاء معزولة، إذا ما قدرت الفدية تتحرك بين الأنظمة ما تقدر تشل المنشأة كلها.",
        ],
    },
    "phishing": {
        "keywords": ["phishing", "phaas", "smishing", "spoof", "social engineering"],
        "why_en": [
            "Phishing keeps winning not because people are careless, but because attackers now rent professional kits that mimic real logins perfectly.",
            "The weakest link is rarely the technology — it's the split second someone trusts a message that looks routine.",
        ],
        "why_ar": [
            "التصيّد الاحتيالي ما زال ناجح، مو لأن الناس مهملين، بل لأن المهاجمين صاروا يستأجرون أدوات احترافية تقلّد صفحات الدخول الحقيقية بدقة.",
            "أضعف حلقة نادرًا ما تكون التقنية، هي لحظة يثق فيها شخص برسالة تبدو عادية.",
        ],
        "tip_en": [
            "Before clicking any login link, check the actual domain character by character — not just the logo or design.",
            "Enable phishing-resistant MFA (like passkeys) wherever you can; a stolen password alone shouldn't be enough.",
        ],
        "tip_ar": [
            "قبل ما تضغط أي رابط دخول، تأكد من النطاق (الدومين) حرف بحرف، مو بس الشعار أو التصميم.",
            "فعّل مصادقة ثنائية مقاومة للتصيد (زي مفاتيح المرور) كل ما قدرت، لأن كلمة المرور المسروقة لحالها ما لازم تكفي.",
        ],
    },
    "vulnerability": {
        "keywords": ["vulnerability", "cve-", "zero-day", "zero day", "patch", "exploit", "flaw"],
        "why_en": [
            "A vulnerability report isn't the scary part — the scary part is how fast attackers weaponize it after it becomes public.",
            "Patching isn't a one-time task; it's a race against whoever reads the same advisory you just did.",
        ],
        "why_ar": [
            "الإعلان عن ثغرة مو الجزء المخيف، المخيف هو سرعة استغلالها من المهاجمين بعد ما تصير معروفة للعموم.",
            "التحديث الأمني مو مهمة تسويها مرة وخلاص، هو سباق بينك وبين أي شخص ثاني قرأ نفس التنبيه.",
        ],
        "tip_en": [
            "Prioritize patching by exposure, not just severity score — an internet-facing system with a medium CVE can matter more than an internal high one.",
            "If you can't patch immediately, isolate the affected system from the network until you can.",
        ],
        "tip_ar": [
            "رتّب أولويات التحديث حسب مدى التعرض للإنترنت، مو بس درجة الخطورة — نظام مكشوف بثغرة متوسطة قد يكون أهم من نظام داخلي بثغرة عالية.",
            "إذا ما قدرت تحدّث فورًا، اعزل النظام المتأثر عن الشبكة لين يجهز التحديث.",
        ],
    },
    "breach": {
        "keywords": ["breach", "leaked", "exposed", "data leak", "stolen data", "hacked database"],
        "why_en": [
            "A data breach rarely stays contained to one company — leaked credentials get reused everywhere users reuse passwords.",
            "The real damage of a breach shows up months later, in accounts you forgot even existed.",
        ],
        "why_ar": [
            "تسريب البيانات نادرًا ما يبقى محصور بشركة وحدة — بيانات الدخول المسرّبة تنعاد استخدامها بأي مكان استخدم فيه الشخص نفس كلمة المرور.",
            "الضرر الحقيقي من التسريب يظهر بعد شهور، بحسابات نسيت أصلاً إنها موجودة.",
        ],
        "tip_en": [
            "Use a unique password for every account — a password manager makes this painless, not optional anymore.",
            "Check if your email appears in known breaches (e.g. haveibeenpwned.com) and rotate any reused passwords immediately.",
        ],
        "tip_ar": [
            "استخدم كلمة مرور مختلفة لكل حساب — برامج إدارة كلمات المرور تخلي هذا سهل، صار أمر ضروري مو رفاهية.",
            "تأكد إذا بريدك ظهر بتسريبات معروفة (مثل haveibeenpwned.com) وغيّر أي كلمة مرور مكررة فورًا.",
        ],
    },
    "malware": {
        "keywords": ["malware", "trojan", "backdoor", "spyware", "rootkit", "loader", "stealer", "infostealer", "keylogger", "worm"],
        "why_en": [
            "Modern malware doesn't announce itself — it blends into normal traffic until the moment it needs to strike.",
            "Most infections start with something boring: a fake update, a cracked tool, or an attachment that looked routine.",
        ],
        "why_ar": [
            "البرمجيات الخبيثة الحديثة ما تعلن عن نفسها، تندمج مع النشاط العادي للجهاز لين تجي لحظة الضربة.",
            "أغلب الإصابات تبدأ بشي عادي جدًا: تحديث مزيف، برنامج مقرصن، أو مرفق يبدو روتيني.",
        ],
        "tip_en": [
            "Only install software from official sources — 'free' cracked versions are one of the top malware delivery methods.",
            "Keep endpoint protection updated and don't ignore its alerts, even the ones that look minor.",
        ],
        "tip_ar": [
            "ثبّت البرامج من مصادرها الرسمية بس — النسخ 'المجانية' المقرصنة من أكثر طرق توزيع البرمجيات الخبيثة.",
            "خلّي برنامج الحماية محدث دايم، وما تتجاهل تنبيهاته حتى لو شكلها بسيطة.",
        ],
    },
    "ai_security": {
        "keywords": ["ai ", "artificial intelligence", "llm", "chatgpt", "claude", "genai", "machine learning model"],
        "why_en": [
            "AI tools are becoming part of the attack surface, not just the defense toolkit — every new capability is also a new thing to secure.",
            "The line between 'AI helping attackers' and 'AI helping defenders' is moving fast, and most policies haven't caught up yet.",
        ],
        "why_ar": [
            "أدوات الذكاء الاصطناعي صارت جزء من سطح الهجوم، مو بس أداة دفاع — كل قدرة جديدة تعني شي جديد لازم تأمّنه.",
            "الخط الفاصل بين 'الذكاء الاصطناعي يساعد المهاجمين' و'يساعد المدافعين' يتحرك بسرعة، وأغلب السياسات لسا ما لحقت عليه.",
        ],
        "tip_en": [
            "Treat AI tool access like any other privileged access — review what data it can see and what actions it can take.",
            "Before adopting a new AI tool at work, check its data-handling policy the same way you'd check a vendor's security posture.",
        ],
        "tip_ar": [
            "تعامل مع صلاحيات أدوات الذكاء الاصطناعي زي أي صلاحية حساسة ثانية — راجع وش تقدر تشوفه ووش تقدر تنفذه.",
            "قبل ما تعتمد أداة ذكاء اصطناعي جديدة بالعمل، راجع سياسة التعامل مع البيانات فيها زي ما تراجع أي مزوّد خدمة.",
        ],
    },
    "general": {
        "keywords": [],
        "why_en": [
            "Every headline like this is a reminder that security isn't a one-time project — it's a habit that has to keep up with attackers.",
            "The details change every week, but the pattern doesn't: attackers look for the easiest path, not the most dramatic one.",
        ],
        "why_ar": [
            "كل خبر زي هذا تذكير إن الأمن السيبراني مو مشروع تسويه مرة وخلاص، هو عادة لازم تواكب المهاجمين باستمرار.",
            "التفاصيل تتغيّر كل أسبوع، بس النمط ثابت: المهاجم يدور على أسهل طريق، مو أكثر طريق إثارة.",
        ],
        "tip_en": [
            "Take five minutes today to double-check one basic control (MFA, backups, or updates) — small habits prevent most incidents.",
            "Share this with one colleague — awareness spreads slower than threats do, so it needs a push.",
        ],
        "tip_ar": [
            "خذ خمس دقايق اليوم وراجع ضابط أساسي وحد (مصادقة ثنائية، نسخ احتياطي، أو تحديثات) — العادات الصغيرة توقف أغلب الحوادث.",
            "شارك هذا الخبر مع زميل — الوعي ينتشر أبطأ من التهديدات، فيحتاج دفعة منك.",
        ],
    },
}

BOLD_MAP = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    BOLD_MAP[ch] = chr(0x1D400 + i)
for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    BOLD_MAP[ch] = chr(0x1D41A + i)
for i, ch in enumerate("0123456789"):
    BOLD_MAP[ch] = chr(0x1D7CE + i)


def to_bold(text):
    """يحوّل النص لأحرف يونيكود 'عريضة' حقيقية تظهر Bold حتى بنص عادي بلا تنسيق (تصلح لعنوان لينكدإن)."""
    return "".join(BOLD_MAP.get(ch, ch) for ch in text)


def ar_hashtag(tag):
    """يمنع تشابك اتجاه الكتابة (RTL/LTR) بين رمز # واللاحقة العربية عند اللصق في لينكدإن."""
    return f"#\u200f{tag}"


def load_posts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_posts(posts):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def make_id(link):
    return hashlib.sha256(link.encode()).hexdigest()[:16]


def clean_html(raw):
    text = BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)
    # يشيل ذيول شائعة بخلاصات RSS (WordPress) ما تفيد بالمنشور
    text = re.sub(r"\[\s*…\s*\]|\[\s*\.\.\.\s*\]", "", text)
    text = re.sub(r"The post .* appeared first on .*\.$", "", text)
    text = re.sub(r"Read More.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def smart_truncate(text, limit=260):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for punct in [". ", "! ", "? "]:
        idx = cut.rfind(punct)
        if idx > limit * 0.4:
            return cut[: idx + 1].strip()
    idx = cut.rfind(" ")
    return (cut[:idx] if idx > 0 else cut).strip() + "…"


def categorize(title, summary):
    text = f"{title} {summary}".lower()
    for key, data in CATEGORIES.items():
        if key == "general":
            continue
        if any(kw in text for kw in data["keywords"]):
            return key
    return "general"


def extract_image(entry):
    try:
        if getattr(entry, "media_content", None):
            url = entry.media_content[0].get("url")
            if url:
                return url
        if getattr(entry, "media_thumbnail", None):
            url = entry.media_thumbnail[0].get("url")
            if url:
                return url
        for l in entry.get("links", []):
            if str(l.get("type", "")).startswith("image"):
                return l.get("href")
        r = requests.get(entry.link, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        pass
    return DEFAULT_IMAGE


def linkedin_english(title, gist, category, variant, source, link):
    data = CATEGORIES[category]
    headline = to_bold(title)
    why = data["why_en"][variant % len(data["why_en"])]
    tip = data["tip_en"][variant % len(data["tip_en"])]
    hashtags = "#CyberSecurity #InfoSec #ThreatIntel #DataProtection #TechNews"
    return (
        f"🛡️ {headline}\n\n"
        f"📌 What happened: {gist}\n\n"
        f"💡 Why it matters: {why}\n\n"
        f"✅ Quick tip: {tip}\n\n"
        f"🔗 Source: {source} — {link}\n\n"
        f"{hashtags}\n\n"
        f"— {AUTHOR_NAME_EN}, {AUTHOR_TITLE_EN}"
    )


def linkedin_arabic(title_ar, gist_ar, category, variant, source, link):
    data = CATEGORIES[category]
    why = data["why_ar"][variant % len(data["why_ar"])]
    tip = data["tip_ar"][variant % len(data["tip_ar"])]
    tags = ["الأمن_السيبراني", "حماية_البيانات", "تهديدات_سيبرانية", "تقنية"]
    hashtags = " ".join(ar_hashtag(t) for t in tags)
    return (
        f"🛡️ {title_ar}\n\n"
        f"📌 وش اللي صار: {gist_ar}\n\n"
        f"💡 ليش هذا مهم: {why}\n\n"
        f"✅ نصيحة سريعة: {tip}\n\n"
        f"🔗 المصدر: {source} — {link}\n\n"
        f"{hashtags}\n\n"
        f"— {AUTHOR_NAME_AR}، {AUTHOR_TITLE_AR}"
    )


def safe_translate(text, target="ar"):
    if not text:
        return ""
    try:
        chunks = [text[i:i + 4500] for i in range(0, len(text), 4500)]
        translated = [GoogleTranslator(source="auto", target=target).translate(c) for c in chunks]
        return " ".join(translated)
    except Exception as e:
        print(f"تحذير: فشلت الترجمة ({e}) - سيتم إبقاء النص الأصلي.")
        return text


def main():
    posts = load_posts()
    existing_ids = {p["id"] for p in posts}
    new_posts = []

    for source, url in FEEDS.items():
        if len(new_posts) >= MAX_NEW_PER_RUN:
            break
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            if len(new_posts) >= MAX_NEW_PER_RUN:
                break
            pid = make_id(entry.link)
            if pid in existing_ids:
                continue

            title = clean_html(entry.get("title", ""))
            raw_summary = clean_html(entry.get("summary", entry.get("description", "")))
            if not title:
                continue

            gist = smart_truncate(raw_summary, 260)
            category = categorize(title, raw_summary)
            variant = int(pid, 16) % 2

            image = extract_image(entry)
            title_ar = safe_translate(title)
            gist_ar = safe_translate(gist)

            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                dt = datetime(*published[:6], tzinfo=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            post = {
                "id": pid,
                "source": source,
                "link": entry.link,
                "image": image,
                "published_at": dt.isoformat(),
                "en_text": linkedin_english(title, gist, category, variant, source, entry.link),
                "ar_text": linkedin_arabic(title_ar, gist_ar, category, variant, source, entry.link),
            }
            new_posts.append(post)
            existing_ids.add(pid)

    if new_posts:
        posts = new_posts + posts
        posts.sort(key=lambda p: p["published_at"], reverse=True)
        posts = posts[:MAX_POSTS]
        save_posts(posts)
        print(f"تمت إضافة {len(new_posts)} خبر جديد.")
    else:
        print("لا توجد أخبار جديدة في هذا التشغيل.")


if __name__ == "__main__":
    main()
