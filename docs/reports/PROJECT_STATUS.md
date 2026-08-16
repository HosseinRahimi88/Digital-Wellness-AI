# وضعیت پروژه Digital Wellness AI — گزارش کامل

**آخرین به‌روزرسانی:** بعد از فاز تست بار (Load Testing) روی SHAP
**تعداد تست‌ها:** ۱۲۳ از ۱۲۳ پاس ✅
**وضعیت مدل‌های ML:** دست‌نخورده، MD5-verified در هر مرحله

---

## ۱. این پروژه چیه؟

مرج دو پروژه:
- **Project A**: مدل‌های ML قوی‌تر (classifier + regressor)، feature engineering دقیق، SHAP، pipeline پیش‌بینی
- **Project B (Parisa)**: معماری محصول بهتر (onboarding، dashboard، weekly plan، توصیه‌ها، مستندات)

**تصمیم معماری:** بک‌اند FastAPI پروژه B رد شد (به مدل خودش قفل شده بود، جایگزینی‌اش یعنی بازنویسی کامل). Streamlit پروژه A به‌عنوان پایه نگه داشته شد؛ ایده‌های محصولی B روی سرویس‌های واقعی A پیاده‌سازی شدن.

---

## ۲. چیکارا تموم شده (فاز به فاز)

### فاز ۰ — تصمیم معماری
- مقایسه کامل دو پروژه، رد کردن FastAPI پروژه B (اما کد امنیتی/auth اون audit و بعداً پورت شد)

### فاز ۱ — زیرساخت Auth
| فایل | چیکار می‌کنه |
|---|---|
| `services/account_service.py` | ثبت‌نام/لاگین چند‌کاربره، بدون دیتابیس جدید (از storage خود A استفاده می‌کنه) |
| `utils/security.py` | هش پسورد با Argon2 |
| `legacy/streamlit_app/pages/Login.py` | صفحه لاگین/ثبت‌نام |

### فاز ۲ — Onboarding
| فایل | چیکار می‌کنه |
|---|---|
| `legacy/streamlit_app/pages/Onboarding.py` | ۶ سوال (هدف، دلیل استفاده، برنامه هفتگی، خواب، سطح تلاش، رضایت‌نامه) |
| `config/onboarding_options.py` | گزینه‌های مشترک بین Onboarding و Profile |

### فاز ۳ — Prediction (بهبود)
| فایل | چیکار می‌کنه |
|---|---|
| `config/demo_profiles.py` | ۴ پروفایل دمو (Healthy/At Risk/Borderline/Baseline) برای تست سریع |
| `legacy/streamlit_app/pages/Prediction.py` | تب "Quick Demo" اضافه شد کنار فرم اصلی |

### فاز ۴ — Dashboard (صفحه جدید)
| فایل | چیکار می‌کنه |
|---|---|
| `legacy/streamlit_app/pages/Dashboard.py` | امتیاز آخرین چک-این، مقایسه با قبلی، heatmap هفتگی، نقاط قوت/ضعف از SHAP، توصیه‌ها |

### فاز ۵ — Weekly Plan (پایدارسازی)
| فایل | چیکار می‌کنه |
|---|---|
| `services/plan_progress_service.py` | تیک‌زدن تسک‌های پلن هفتگی، **ذخیره واقعی** (نه فقط session) |
| `legacy/streamlit_app/pages/Weekly_Insights.py` | بخش "Weekly Plan" پایدار اضافه شد |

### فاز ۶ — Recommendations (محتوای Guardrail)
| فایل | چیکار می‌کنه |
|---|---|
| `config/recommendation_registry.py` | هر توصیه یه `success_metric` و `safety_note` گرفت |
| `legacy/streamlit_app/components/recommendation_card.py` | نمایش این محتوا در UI |

### فاز ۷ — Analytics (روند تاریخی)
| فایل | چیکار می‌کنه |
|---|---|
| `legacy/streamlit_app/pages/Analytics.py` | نمودار روند امتیاز در طول زمان + الگوی روز هفته، از داده واقعی |

### فاز ۸ — Profile Management (صفحه جدید)
| فایل | چیکار می‌کنه |
|---|---|
| `legacy/streamlit_app/pages/Profile.py` | مدیریت اکانت، ویرایش ترجیحات، لینک به Model Performance واقعی |

### فاز ۹ — باگ‌فیکس + آماده‌سازی بک‌اند برای FastAPI (بدون ساخت خودش)
- باگ واقعی پیدا و رفع شد: `Account(**record)` با کلید ناشناس crash می‌کرد
- `utils/tokens.py` اضافه شد: صدور/اعتبارسنجی JWT — **هنوز به هیچ صفحه‌ای وصل نیست**، فقط آماده‌ست

### فاز ۱۰ — تست‌های سخت‌گیرانه (Concurrency + Adversarial)
- باگ واقعی پیدا و رفع شد: مقدار boolean بی‌صدا به‌جای عدد قبول می‌شد (`float(True) == 1.0`)
- تست race condition واقعی با ۳۰-۵۰ thread همزمان — بدون مشکل
- تست حمله‌های JWT (جعل توکن، دستکاری امضا) — همه رد شدن
- تست فارسی/ایموجی/پسورد طولانی — بدون مشکل

### فاز ۱۱ — تست بار SHAP (این آخرین فاز)
- تأیید شد: هیچ crash، هیچ نشت حافظه، هیچ قاطی‌شدن داده بین کاربرها زیر بار
- **یافته مهم:** به‌خاطر GIL پایتون، pipeline پیش‌بینی زیر thread همزمان *موازی* اجرا نمیشه (throughput محدود به یک هسته در هر process) — این یه محدودیت معماری‌ست، نه باگ. راه‌حل: چند replica/process پشت load balancer، نه تغییر کد.

---

## ۳. آمار نهایی تست

```
تعداد کل تست‌ها: ۱۲۳
همه پاس ✅

دسته‌بندی:
- تست‌های اصلی پروژه A (ML pipeline, validation, history, ...): ۶۲
- تست‌های Account/Auth: ۱۶
- تست‌های Plan Progress: ۷
- تست‌های JWT Token (شامل حمله‌ها): ۱۸
- تست‌های Concurrency (سرویس‌های جدید): ۴
- تست‌های Recommendation (guardrail content): +۳
- تست‌های SHAP Load: ۳
- تست‌های دیگر (validation edge cases و...): +۱۰
```

## ۴. چیزهایی که هنوز دست‌نخورده و تأیید شده (MD5)

```
artifacts/health_classifier.pkl  → ed8b7d02407f4c1bfcabc413a8fe095a
artifacts/health_regressor.pkl   → d6eed3e52dec8860ecb79d3d23d29c52
```
مدل‌ها، feature engineering، pipeline پیش‌بینی، SHAP — همه دقیقاً همونی هستن که پروژه A داشت.

---

## ۵. صفحات فعلی اپ (۱۱ صفحه)

| صفحه | وضعیت |
|---|---|
| Home | تغییریافته (نویگیشن) |
| Login | **جدید** |
| Onboarding | **جدید** |
| Prediction | تغییریافته (+ Quick Demo) |
| Dashboard | **جدید** |
| Weekly Insights | تغییریافته (+ Weekly Plan) |
| AI Coach | دست‌نخورده |
| Analytics | تغییریافته (+ روند تاریخی) |
| Model Performance | دست‌نخورده |
| Profile | **جدید** |
| What-if Simulator | دست‌نخورده |
| About | دست‌نخورده |

---

## ۶. چیزهایی که هنوز کار نشده (Tech Debt شناخته‌شده)

این‌ها همه **عمداً** کنار گذاشته شدن، نه فراموش‌شده:

1. **آپلود CSV/JSON دسته‌ای** توی Prediction — پروژه B داشت، ولی schema فیچرهای A فرق می‌کنه، پیاده‌سازی درستش یه کار مستقل می‌خواد
2. **پیگیری اکشن روی توصیه‌ها** (done/skip/...) — نیاز به یه مدل identity پایدار برای recommendation‌ها داره که فعلاً نیست
3. **جدول Personal Baseline** (انحراف از EWMA برای همه فیچرها) — فعلاً فقط یه فیچر این‌جوری ردیابی میشه
4. **تنظیمات tone/reminder/excluded-families** توی Profile — عمداً اضافه نشدن چون هیچی مصرفشون نمی‌کنه (تنظیمات بی‌اثر بدتر از نبودنشونه)
5. **`st.time_input` واقعی** — الان فیلد متنی HH:MM هست
6. **JWT هنوز به هیچ صفحه‌ای وصل نیست** — فقط زیرساخت آماده‌ست
7. **تأیید نهایی در sandbox** — این محیط اینترنت نداره، پس `pwdlib` واقعی (Argon2) رو نتونستم مستقیم تست کنم (فقط از طریق API مستندش شبیه‌سازی شد)

---

## ۷. نمره آمادگی برای Production: ۷.۵ / ۱۰

**چی خوبه:**
- لایه ML کاملاً حفظ و تأیید شده
- ۱۲۳ تست، شامل race condition واقعی و حمله‌های امنیتی واقعی
- هیچ نشت حافظه‌ای زیر بار سنگین
- کد جدید همه از الگوی concurrency-safe خود پروژه A استفاده می‌کنه (فایل جدید ننوشتم که ناامن باشه)

**چی کمه:**
- نبود rate limiting روی لاگین (محافظت timing-attack هست ولی lockout نیست)
- ذخیره‌سازی JSON برای تعداد کاربر خیلی زیاد مقیاس‌پذیر نیست (باید بره سمت دیتابیس واقعی)
- تأیید نهایی `pwdlib` باید توی محیط واقعی خودت با اینترنت انجام بشه

---

## ۸. مرحله بعدی چیه؟ (پیشنهاد ترتیب)

### گزینه ۱ — تست واقعی (توصیه می‌شه اول این)
قبل از هر کار توسعه‌ای بیشتر، پروژه رو با `streamlit run legacy/streamlit_legacy/streamlit_app/Home.py` توی محیط واقعی خودت (با اینترنت، بعد از `pip install -r requirements.txt`) اجرا کن و از نظر UX/ظاهر چک کن. من نمی‌تونم این بخش رو ببینم چون Streamlit واقعی توی sandbox من نصب نمیشه.

### گزینه ۲ — ساخت واقعی لایه FastAPI
حالا که بک‌اند آماده‌ست (services مستقل از UI، JWT آماده)، می‌تونیم واقعاً شروع کنیم به ساخت:
- `main.py` + route های FastAPI
- Pydantic schema برای request/response
- اتصال JWT به یه dependency واقعی (مثل `get_current_user`)
- تصمیم درباره اینکه storage همون JSON بمونه یا بره سمت دیتابیس

### گزینه ۳ — تکمیل Tech Debt باقی‌مونده
اگه فعلاً نمی‌خوای بری سمت FastAPI، می‌تونیم یکی از موارد بخش ۶ رو کامل کنیم (مثلاً آپلود CSV دسته‌ای یا پیگیری اکشن روی توصیه‌ها)

### گزینه ۴ — تست عمیق‌تر روی بخش دیگه
اگه هنوز به بخش خاصی مشکوکی (مثل `prediction_service.py` یا `report_service.py` یا خود مدل‌های ML)، می‌تونیم همون سطح تست سخت‌گیرانه رو روی اونجا هم ببریم

---

**فایل‌های مرجع دیگه:** `MERGE_REPORT.md` گزارش کامل‌تر فنی هر فاز مرج رو داره (تصمیمات معماری، دلایل، جزئیات فایل به فایل).
