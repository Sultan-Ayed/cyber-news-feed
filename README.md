# SIGNAL /CYBER — تغذية أخبار الأمن السيبراني

صفحة GitHub Pages تعرض آخر أخبار الأمن السيبراني، تُحدَّث تلقائيًا كل ساعة عبر GitHub Actions،
وتُصاغ كل خبر كمنشور LinkedIn ثنائي اللغة (إنجليزي أعلى / عربي أسفل) مع صورة مرتبطة بالمحتوى،
**بدون الحاجة لأي مفتاح API** (الترجمة تتم عبر مكتبة `deep-translator` المجانية).

---

## 1) إنشاء المستودع ورفع الملفات

1. افتح [github.com/new](https://github.com/new) وأنشئ مستودعًا جديدًا، مثلاً باسم `cyber-news-feed`.
   - اجعله **Public** (مطلوب لتفعيل GitHub Pages المجاني).
   - لا تُفعّل "Add README" لأن الملف موجود هنا مسبقًا.
2. ارفع جميع الملفات والمجلدات الموجودة في هذا المشروع كما هي (حافظ على نفس الهيكلة):
   ```
   index.html
   assets/style.css
   assets/app.js
   data/posts.json
   scripts/fetch_news.py
   requirements.txt
   .github/workflows/update-news.yml
   README.md
   ```
   أسهل طريقة: من صفحة المستودع الفارغة اضغط "uploading an existing file" واسحب كل الملفات
   (تأكد أن مجلد `.github` رُفع أيضًا — بعض المتصفحات تُخفي المجلدات التي تبدأ بنقطة، فإذا لم يظهر
   استخدم الرفع عبر Git من جهازك أو GitHub Desktop).

## 2) تفعيل GitHub Pages

1. من المستودع: **Settings → Pages**.
2. تحت "Build and deployment" اختر **Deploy from a branch**.
3. اختر الفرع `main` والمجلد `/ (root)`، ثم احفظ.
4. بعد دقيقة أو دقيقتين ستظهر رابط الصفحة أعلى الإعداد (مثل
   `https://<username>.github.io/cyber-news-feed/`).

## 3) تفعيل التحديث التلقائي (GitHub Actions)

الأتمتة مفعّلة تلقائيًا فور رفع مجلد `.github/workflows` — ستعمل كل ساعة تلقائيًا.
لتشغيلها فورًا أول مرة بدل انتظار الساعة القادمة:

1. من المستودع اذهب لتبويب **Actions**.
2. إذا ظهرت رسالة تفعيل الـ Workflows اضغط "I understand my workflows, go ahead and enable them".
3. اختر **Update Cybersecurity News** من القائمة اليسرى.
4. اضغط **Run workflow → Run workflow**.
5. بعد اكتمال التشغيل (دقيقة أو دقيقتين) سيتحدّث ملف `data/posts.json` تلقائيًا،
   وستظهر الأخبار في صفحتك خلال دقائق.

## 4) ملاحظات مهمة

- **بدون مفتاح API:** الترجمة تعتمد على خدمة Google Translate غير الرسمية (عبر مكتبة
  `deep-translator`)، وهي مجانية لكن قد تتعطل أو تتأخر أحيانًا بسبب حدود الاستخدام —
  في هذه الحالة يبقى النص الأصلي دون ترجمة مؤقتًا وسيُحاول السكربت مرة أخرى في التشغيل التالي.
- **مصادر الأخبار:** The Hacker News, BleepingComputer, Krebs on Security, Dark Reading,
  SecurityWeek. يمكنك إضافة أو حذف مصادر من القاموس `FEEDS` في `scripts/fetch_news.py`.
- **وتيرة التحديث:** كل ساعة افتراضيًا (`cron: '0 * * * *'` في ملف الـ workflow). لتغييرها
  عدّل قيمة الـ cron في `.github/workflows/update-news.yml`.
- **الصياغة:** النصوص تُبنى بقالب ثابت (عنوان تنبيهي + ملخص + رابط + هاشتاقات) وليست
  بصياغة توليدية بالذكاء الاصطناعي، لأنه لا يوجد مفتاح API متاح. إذا رغبت لاحقًا بصياغة أكثر
  احترافية وذكاءً، يمكن ربط مفتاح Anthropic API كـ Secret في المستودع وتحديث السكربت
  لاستدعاء نموذج Claude بدل القالب الثابت.

## 5) هيكل المشروع

```
├── index.html                     # الصفحة الرئيسية
├── assets/
│   ├── style.css                  # التصميم
│   └── app.js                     # عرض المنشورات من data/posts.json
├── data/
│   └── posts.json                 # قاعدة بيانات الأخبار (تُحدَّث تلقائيًا)
├── scripts/
│   └── fetch_news.py              # سكربت الجلب + الترجمة + الصياغة
├── requirements.txt                # مكتبات بايثون
└── .github/workflows/
    └── update-news.yml            # أتمتة GitHub Actions (كل ساعة)
```
