"""
يجلب أحدث أخبار الأمن السيبراني من عدة مصادر RSS، يصيغها بأسلوب منشور LinkedIn
(إنجليزي أعلى / عربي أسفل)، يستخرج صورة مرتبطة بالخبر، ويحفظها في data/posts.json
بدون الحاجة لأي مفتاح API (يستخدم مكتبة deep-translator المجانية للترجمة).
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import os
import hashlib
from datetime import datetime, timezone

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
    return BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)


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
        # آخر محاولة: جلب og:image من صفحة المقال نفسها
        r = requests.get(entry.link, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        pass
    return DEFAULT_IMAGE


def linkedin_english(title, summary, source, link):
    hook = f"🚨 Cybersecurity Alert: {title}"
    body = summary[:420].rstrip()
    if len(summary) > 420:
        body += "..."
    hashtags = "#CyberSecurity #InfoSec #ThreatIntel #DataProtection #TechNews"
    return (
        f"{hook}\n\n{body}\n\n"
        f"🔗 Source: {source}\n"
        f"Read the full story: {link}\n\n"
        f"{hashtags}"
    )


def linkedin_arabic(title_ar, summary_ar, source, link):
    hook = f"🚨 تنبيه أمن سيبراني: {title_ar}"
    body = (summary_ar or "").strip()
    if len(body) > 420:
        body = body[:420].rstrip() + "..."
    hashtags = "#الأمن_السيبراني #حماية_البيانات #تهديدات_سيبرانية #تقنية"
    return (
        f"{hook}\n\n{body}\n\n"
        f"🔗 المصدر: {source}\n"
        f"رابط الخبر الكامل: {link}\n\n"
        f"{hashtags}"
    )


def safe_translate(text, target="ar"):
    if not text:
        return ""
    try:
        # الترجمة المجانية محدودة بعدد أحرف لكل طلب، لذلك نقسم النص عند الحاجة
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
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            if not title:
                continue

            image = extract_image(entry)
            title_ar = safe_translate(title)
            summary_ar = safe_translate(summary)

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
                "en_text": linkedin_english(title, summary, source, entry.link),
                "ar_text": linkedin_arabic(title_ar, summary_ar, source, entry.link),
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
