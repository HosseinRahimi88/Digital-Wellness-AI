"""
Improvement Plan Service
--------------------------
Generates a realistic, rule-based 7-day digital wellness improvement
plan from the user's most recent REAL prediction outputs:
    - predicted health class (PredictionService.CLASS_MAPPING label)
    - wellness score (PredictionService regression output, 0-100)
    - persona (utils.persona.generate_persona)
    - the raw/derived habit fields the user actually submitted

This is intentionally rule-based only - no LLM calls, no model
inference, no retraining. It is pure presentation logic layered on top
of outputs the ML pipeline already produced, exactly like
RecommendationService/StoryCard do for their features. It never
modifies user_data, never calls PredictionService, and never touches
anything under models/ or artifacts/.

Two personalization passes, both driven only by the user's own
submitted values (never a generic template):
  1. Focus areas are ranked by *severity* - how far each habit sits
     from its healthy threshold, normalized to 0-1 - so the weakest
     signal leads the week, not just whichever rule happens to be
     first in the list.
  2. Each theme escalates across its repeat occurrences in the week
     (gentle -> moderate -> stronger tasks) instead of repeating the
     exact same three tasks every time it comes up - a literal,
     visible "gradually address this" progression rather than a static
     checklist shown multiple times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_TIER_LABELS = ["Getting started", "Building the habit", "Locking it in"]

LANGUAGES = ("en", "fa", "ar", "zh")

# Everything wrapping the exercises used to be English-only. The
# exercises themselves already carried four languages, so a Persian
# reader got translated tasks sitting under an English theme title,
# an English tip and an English "Day 3" - which reads worse than a
# page that is honestly all one language.
_THEME_I18N: dict[str, dict[str, str]] = {
    "Sleep Recovery": {
        "en": "Sleep Recovery", "fa": "بازیابی خواب",
        "ar": "استعادة النوم", "zh": "睡眠恢复",
    },
    "Social Media Boundaries": {
        "en": "Social Media Boundaries", "fa": "مرزهای شبکه‌های اجتماعی",
        "ar": "حدود وسائل التواصل", "zh": "社交媒体边界",
    },
    "Stress Reset": {
        "en": "Stress Reset", "fa": "بازنشانی استرس",
        "ar": "إعادة ضبط التوتر", "zh": "压力重置",
    },
    "Movement": {
        "en": "Movement", "fa": "تحرک",
        "ar": "الحركة", "zh": "身体活动",
    },
    "Mindful Notifications": {
        "en": "Mindful Notifications", "fa": "اعلان‌های آگاهانه",
        "ar": "إشعارات واعية", "zh": "有意识的通知管理",
    },
    "Deep Focus": {
        "en": "Deep Focus", "fa": "تمرکز عمیق",
        "ar": "تركيز عميق", "zh": "深度专注",
    },
    "Maintain Your Momentum": {
        "en": "Maintain Your Momentum", "fa": "حفظ روند خوبت",
        "ar": "حافظ على زخمك", "zh": "保持你的势头",
    },
    "Reflect & Reset": {
        "en": "Reflect & Reset", "fa": "مرور و بازنشانی",
        "ar": "تأمّل وإعادة ضبط", "zh": "回顾与重置",
    },
}

_TIP_I18N: dict[str, dict[str, str]] = {
    "Sleep Recovery": {
        "en": "Small, consistent sleep gains compound fast - aim for +15-30 min a night rather than a big jump.",
        "fa": "بردهای کوچک و پیوسته در خواب سریع روی هم جمع می‌شوند — به‌جای یک جهش بزرگ، شبی ۱۵ تا ۳۰ دقیقه را هدف بگیر.",
        "ar": "المكاسب الصغيرة المنتظمة في النوم تتراكم بسرعة — استهدف ١٥ إلى ٣٠ دقيقة إضافية كل ليلة بدل قفزة كبيرة.",
        "zh": "睡眠上小而稳定的进步会快速累积——每晚多睡 15 到 30 分钟，比一次性大跨步更有效。",
    },
    "Social Media Boundaries": {
        "en": "You don't need to quit social media - just add a little friction before you open it.",
        "fa": "لازم نیست شبکه‌های اجتماعی را کنار بگذاری — فقط پیش از باز کردنشان کمی اصطکاک اضافه کن.",
        "ar": "لست مضطراً لترك وسائل التواصل — يكفي أن تضيف قليلاً من الاحتكاك قبل أن تفتحها.",
        "zh": "你不需要戒掉社交媒体——只要在打开它之前加一点阻力就够了。",
    },
    "Stress Reset": {
        "en": "Short, frequent resets beat one long break - they interrupt the stress build-up earlier.",
        "fa": "بازنشانی‌های کوتاه و پرتکرار از یک استراحت طولانی بهترند — زودتر جلوی انباشت استرس را می‌گیرند.",
        "ar": "فترات الاستعادة القصيرة المتكررة أفضل من استراحة واحدة طويلة — فهي تقطع تراكم التوتر مبكراً.",
        "zh": "短而频繁的重置比一次长休息更有效——它们能更早打断压力的累积。",
    },
    "Movement": {
        "en": "Movement is one of the fastest levers for mood and focus - even short bursts count.",
        "fa": "تحرک یکی از سریع‌ترین اهرم‌ها برای خلق‌وخو و تمرکز است — حتی تکان‌های کوتاه هم حساب می‌شوند.",
        "ar": "الحركة من أسرع الروافع للمزاج والتركيز — وحتى النوبات القصيرة منها تُحسب.",
        "zh": "身体活动是改善情绪和专注最快的杠杆之一——哪怕只是短暂的几下也算数。",
    },
    "Mindful Notifications": {
        "en": "Fewer interruptions means fewer chances to fall into an unplanned scrolling session.",
        "fa": "وقفه‌ی کمتر یعنی فرصت کمتر برای افتادن در یک اسکرول بی‌برنامه.",
        "ar": "مقاطعات أقل تعني فرصاً أقل للانزلاق في تصفّح غير مخطط له.",
        "zh": "更少的打断，意味着更少陷入计划外刷屏的机会。",
    },
    "Deep Focus": {
        "en": "Protecting one deep-focus block a day matters more than trying to be 'always on'.",
        "fa": "محافظت از یک بلوک تمرکز عمیق در روز، مهم‌تر از تلاش برای «همیشه در دسترس بودن» است.",
        "ar": "حماية فترة تركيز عميق واحدة يومياً أهم من محاولة أن تكون متاحاً طوال الوقت.",
        "zh": "每天守住一段深度专注的时间，比试图「随时在线」更重要。",
    },
    "Maintain Your Momentum": {
        "en": "You're already doing well on this front - protecting it is the goal, not overhauling it.",
        "fa": "در این زمینه داری خوب پیش می‌روی — هدف حفظش است، نه زیر و رو کردنش.",
        "ar": "أنت تبلي حسناً في هذا الجانب — الهدف حمايته لا إعادة بنائه.",
        "zh": "你在这方面已经做得不错——目标是守住它，而不是推倒重来。",
    },
    "Reflect & Reset": {
        "en": "A weekly reflection turns a one-off good day into a repeatable habit.",
        "fa": "یک مرور هفتگی، یک روزِ خوبِ اتفاقی را به عادتی تکرارشدنی تبدیل می‌کند.",
        "ar": "التأمل الأسبوعي يحوّل يوماً جيداً عابراً إلى عادة قابلة للتكرار.",
        "zh": "每周一次回顾，能把偶然的好日子变成可重复的习惯。",
    },
}

_TIER_LABEL_I18N: list[dict[str, str]] = [
    {"en": "Getting started", "fa": "شروع کردن", "ar": "البداية", "zh": "起步"},
    {"en": "Building the habit", "fa": "ساختن عادت", "ar": "بناء العادة", "zh": "养成习惯"},
    {"en": "Locking it in", "fa": "تثبیت کردن", "ar": "ترسيخها", "zh": "固定下来"},
]

_DAY_LABEL_I18N: dict[str, str] = {
    "en": "Day {n}", "fa": "روز {n}", "ar": "اليوم {n}", "zh": "第 {n} 天",
}




# Arabic and Persian separate list items with an Arabic comma; Chinese
# uses its own enumeration comma. Joining four themes with ", " in all
# four is one of those details that quietly marks a page as translated
# rather than written.
_LIST_SEPARATOR: dict[str, str] = {"en": ", ", "fa": "، ", "ar": "، ", "zh": "、"}

# The bottom half of the moderate band. Its own opener, because it is
# the band where an ordinary "you are Moderate, here are adjustments"
# reads as a verdict rather than a plan - see "moderate_low" below.
MODERATE_LOW_FLOOR = 50.0
MODERATE_LOW_CEILING = 60.0

# The intro sentence, per score band. Written per language rather than
# concatenated from translated fragments: Persian and Arabic put the
# number and the band in a different order than English, and a sentence
# assembled English-first reads as machine output in both.
_INTRO_BY_BAND: dict[str, dict[str, str]] = {
    "at risk": {
        "en": "Your current wellness score is {score}, which puts you in the **At Risk** range{persona}. This week is about small, sustainable resets - not a total overhaul.",
        "fa": "امتیاز سلامت فعلی‌ات {score} است، که تو را در محدوده‌ی **در معرض خطر** قرار می‌دهد{persona}. این هفته درباره‌ی بازنشانی‌های کوچک و پایدار است — نه زیر و رو کردن همه‌چیز.",
        "ar": "درجة عافيتك الحالية {score}، وهي تضعك في نطاق **معرّض للخطر**{persona}. هذا الأسبوع يدور حول إعادات ضبط صغيرة ومستدامة — لا إصلاح شامل.",
        "zh": "你当前的健康分是 {score}，处于**风险**区间{persona}。这一周的重点是小而可持续的重置——不是彻底推翻重来。",
    },
    "moderate": {
        "en": "You're at {score} and sitting in the **Moderate** range{persona}. A few focused adjustments this week can move the needle noticeably.",
        "fa": "روی {score} هستی و در محدوده‌ی **متوسط** قرار داری{persona}. چند تنظیم متمرکز در این هفته می‌تواند تفاوت محسوسی بسازد.",
        "ar": "أنت عند {score} وتقع في النطاق **المتوسط**{persona}. بضعة تعديلات مركّزة هذا الأسبوع قد تُحدث فرقاً ملحوظاً.",
        "zh": "你目前是 {score}，处于**中等**区间{persona}。这一周做几处有针对性的调整，就能带来明显变化。",
    },
    # The bottom of the moderate band, 50-60, gets its own opener - and
    # it leads with the credit before the label.
    #
    # It is the one place where the ordinary moderate sentence lands
    # wrong. Someone at 55 is either just out of the at-risk range or
    # about to fall back into it, and "you're at 55, Moderate range,
    # here are some adjustments" reads to them as a verdict. It is also
    # the band where people are most likely to stop: far enough from
    # healthy to feel pointless, close enough to at-risk to feel like
    # failure. So this one says what is working first, and explains
    # second. Nothing is softened and no number is hidden - the score
    # and the label are both still in the sentence, just not first.
    "moderate_low": {
        "en": "You are the right side of the at-risk line{persona}, and that is not nothing - most of the distance from a hard week to a good one is exactly here. You are at {score}, the lower half of the **Moderate** range, which is the part that moves fastest: this is where a couple of consistent habits show up in the number within days rather than weeks.",
        "fa": "تو سمت درستِ خط «در معرض خطر» ایستاده‌ای{persona}، و این چیز کمی نیست — بیشترِ فاصله‌ی یک هفته‌ی سخت تا یک هفته‌ی خوب دقیقاً همین‌جاست. روی {score} هستی، نیمه‌ی پایینی محدوده‌ی **متوسط**، که سریع‌ترین بخش برای جابه‌جا شدن است: اینجا دو تا عادتِ پیوسته در عرض چند روز خودشان را در عدد نشان می‌دهند، نه چند هفته.",
        "ar": "أنت في الجانب الصحيح من خط الخطر{persona}، وهذا ليس قليلاً — معظم المسافة بين أسبوع صعب وأسبوع جيد تقع هنا بالضبط. أنت عند {score}، النصف الأدنى من النطاق **المتوسط**، وهو الجزء الأسرع حركةً: هنا تظهر عادتان ثابتتان في الرقم خلال أيام لا أسابيع.",
        "zh": "你站在风险线正确的这一侧{persona}，这并不是小事——从一个难熬的星期到一个不错的星期，大部分距离恰恰就在这里。你目前是 {score}，处在**中等**区间的下半段，而这一段移动得最快：在这里，两个坚持下来的习惯，几天之内就会反映在数字上，而不用等上几周。",
    },
    "healthy": {
        "en": "You're at {score} and already in the **Healthy** range{persona}. This week is about protecting what's working and fine-tuning the rest.",
        "fa": "روی {score} هستی و همین حالا در محدوده‌ی **سالم** قرار داری{persona}. این هفته درباره‌ی محافظت از چیزی است که دارد کار می‌کند و تنظیم دقیق بقیه.",
        "ar": "أنت عند {score} وفي النطاق **الصحي** بالفعل{persona}. هذا الأسبوع يدور حول حماية ما ينجح وضبط الباقي بدقة.",
        "zh": "你目前是 {score}，已经处在**健康**区间{persona}。这一周的重点是守住有效的部分，并微调其余的。",
    },
    "unknown": {
        "en": "Your current wellness score is {score}{persona}.",
        "fa": "امتیاز سلامت فعلی‌ات {score} است{persona}.",
        "ar": "درجة عافيتك الحالية {score}{persona}.",
        "zh": "你当前的健康分是 {score}{persona}。",
    },
}

# The persona clause. The persona TITLE itself is never translated - it
# is produced by the persona service and appears elsewhere in the app
# under that exact name, so translating it here would put a label on
# screen that matches nothing the user can find again.
_INTRO_PERSONA: dict[str, str] = {
    "en": " as a **{persona}**",
    "fa": " به‌عنوان **{persona}**",
    "ar": " بوصفك **{persona}**",
    "zh": "（作为**{persona}**）",
}

_INTRO_FOCUS: dict[str, str] = {
    "en": " This plan focuses on: **{themes}**, starting with your weakest signal and getting a little more ambitious each time it comes back around this week.",
    "fa": " این برنامه روی این‌ها تمرکز دارد: **{themes}** — از ضعیف‌ترین سیگنالت شروع می‌کند و هر بار که در طول هفته دوباره برمی‌گردد، کمی جاه‌طلبانه‌تر می‌شود.",
    "ar": " تركّز هذه الخطة على: **{themes}** — تبدأ من أضعف إشاراتك، وتصبح أكثر طموحاً قليلاً في كل مرة تعود فيها خلال الأسبوع.",
    "zh": " 这份计划聚焦于：**{themes}**——从你最弱的信号开始，本周内每次再次出现时都会稍微进阶一点。",
}


@dataclass(slots=True)
class DailyPlan:
    """One day of the 7-day plan."""

    day_number: int
    day_label: str
    theme: str
    icon: str
    tasks: List[str] = field(default_factory=list)
    tip: str = ""
    tier_label: str = ""
    # Composed, value-bound exercises in all four languages. `tasks`
    # above is kept as the English-only fallback for any caller that
    # has not moved over yet - a plan that suddenly returned nothing
    # for them would be a worse outcome than a duplicated sentence.
    exercises: List[Dict[str, Any]] = field(default_factory=list)
    # {part: {lang: text}} for day_label, theme, tip and tier_label. The
    # flat fields above stay English so no existing caller changes.
    text_i18n: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True)
class ImprovementPlan:
    """The full 7-day plan plus a short intro tailored to the user."""

    intro: str
    focus_areas: List[str]
    days: List[DailyPlan] = field(default_factory=list)
    # {part: {lang: text}} - currently just "intro".
    text_i18n: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # One {lang: name} map per focus area, in the same order as
    # `focus_areas` above, so the chips can be rendered translated
    # without the caller having to match names back up.
    focus_areas_i18n: List[Dict[str, str]] = field(default_factory=list)


class ImprovementPlanService:
    """
    Builds a 7-day, rule-based improvement schedule.

    The plan is assembled from a small library of daily "themes" (sleep,
    screen boundaries, movement, mindful notifications, social balance,
    focus/deep work, reflection). Which themes get emphasized - and how
    assertive the language is - depends only on simple, transparent
    if/else rules over the real health class / wellness score / raw
    habit fields already collected. No black box, no LLM.
    """

    # config/onboarding_options.py SCHEDULE_OPTIONS values that mean the
    # user does not have the same day twice. This was collected at
    # onboarding from the start and then ignored by both engines; it is
    # exactly the population for whom "same bedtime every night" is
    # unrealistic advice and "one fixed anchor you can keep" is not.
    _IRREGULAR_SCHEDULES = frozenset({"rotating_shift", "irregular", "late_shift"})

    # Severity multiplier applied to a theme when the schedule is
    # irregular. Routine-anchored themes rise; themes that do not depend
    # on a stable day are untouched.
    _IRREGULAR_BOOST = {
        "Sleep Recovery": 0.35,
        "Stress Reset": 0.15,
    }

    # --- The rest of the onboarding answers -------------------------------
    # `schedule_type` above was the only one of the seven onboarding
    # answers that reached this service. The other six were stored,
    # echoed back by /progress, and read by nothing - which makes them
    # questions the app asks and then ignores. The three below now
    # re-rank the same way schedule_type does: they change WHICH of the
    # user's own flagged signals leads the week, and they never invent a
    # focus area the numbers did not already raise.

    # Somebody whose work REQUIRES a screen cannot act on "cut your total
    # screen time" - it is the one instruction their job overrules, and
    # an app that leads with it has told them to quit. What they can act
    # on is when and how they use it: the evening tail, the notification
    # load, the breaks. So volume themes drop and the controllable ones
    # rise. Down-weighting, never zero: a developer sleeping four hours
    # still needs to hear about their sleep.
    _WORK_SCREEN_WEIGHT = {
        "Deep Focus": -0.30,
        "Social Media Boundaries": -0.20,
        "Mindful Notifications": 0.25,
        "Movement": 0.20,
        "Sleep Recovery": 0.15,
    }

    # What the user says they mainly use their devices FOR. Same
    # mechanism: the themes they can actually move rise for each. The
    # keys are the values config/onboarding_options.py actually stores -
    # not paraphrases of them, which is the way a table like this
    # silently stops matching anything.
    _PURPOSE_WEIGHT = {
        "work_career": {"Deep Focus": 0.25, "Movement": 0.20, "Stress Reset": 0.15},
        "education": {"Deep Focus": 0.30, "Sleep Recovery": 0.15},
        "social_connection": {"Social Media Boundaries": 0.30, "Mindful Notifications": 0.20},
        "entertainment": {"Social Media Boundaries": 0.20, "Sleep Recovery": 0.25},
        "news_information": {"Mindful Notifications": 0.30, "Stress Reset": 0.15},
        "content_creation": {"Deep Focus": 0.20, "Stress Reset": 0.20},
        # "mixed" and "other" carry no weight on purpose: the honest
        # reading of "a bit of everything" is that it says nothing about
        # which theme to lead with.
    }

    # The sleep window the user says they aim for. A declared window
    # shorter than this is somebody telling the app, before any check-in
    # exists, that they intend to sleep less than they need - so sleep
    # leads earlier than their first week's numbers alone would put it.
    # Only ever a boost: a generous declared window does not lower the
    # priority of sleep that is measurably bad.
    _SHORT_DECLARED_SLEEP_HOURS = 7.0
    _DECLARED_SLEEP_BOOST = 0.25

    # How hard the user asked to be pushed. This one does NOT re-rank -
    # it moves the TIER, which is the honest place for it: the same
    # habit, worked at the pace the person asked for. `low` holds
    # somebody at the gentler tier for longer; `high` starts them a rung
    # up rather than spending a week on "set a fixed bedtime" when they
    # asked for a real push. Bounded by the tier list either way, so
    # neither setting can push past what the library actually contains.
    _EFFORT_TIER_SHIFT = {"low": -1, "moderate": 0, "medium": 0, "high": 1}

    # Habit field -> (theme key, "needs work" test, severity 0-1, icon,
    # 3-tier escalating task sets). `severity` ranks which weak signal
    # leads the week; `levels` is what makes a recurring theme feel like
    # real progress instead of a repeated checklist.
    _HABIT_RULES = [
        {
            "field": "sleep_hours",
            "lower_is_better": False,
            "theme": "Sleep Recovery",
            "icon": "😴",
            "needs_work": lambda v: v is not None and v < 7,
            "severity": lambda v: min(1.0, max(0.0, (7 - v) / 7)) if v is not None else 0.0,
            "levels": [
                [
                    "Set a fixed bedtime and wake-up time, even on weekends.",
                    "Stop screens 30-60 minutes before bed; read or stretch instead.",
                    "Keep your phone charging outside the bedroom tonight.",
                ],
                [
                    "Move your bedtime 15 minutes earlier than this week's average.",
                    "Cut caffeine after 2pm today.",
                    "Do the same 5-minute wind-down routine every night this week.",
                ],
                [
                    "Keep the same wake-up time even after a rough night - no catch-up sleeping in.",
                    "Phone stays in another room tonight, not just silenced.",
                    "Note how you feel in the morning - you're building evidence this works.",
                ],
            ],
            "tip": "Small, consistent sleep gains compound fast - aim for +15-30 min a night rather than a big jump.",
        },
        {
            "field": "social_min",
            "lower_is_better": True,
            "theme": "Social Media Boundaries",
            "icon": "📵",
            "needs_work": lambda v: v is not None and v > 90,
            "severity": lambda v: min(1.0, max(0.0, (v - 90) / 90)) if v is not None else 0.0,
            "levels": [
                [
                    "Turn off non-essential notifications for social apps.",
                    "Set a daily app timer and let it actually interrupt you.",
                    "Replace one scrolling session with a call or a walk.",
                ],
                [
                    "Move social apps off your home screen.",
                    "Add a deliberate 10-second pause before opening any social app.",
                    "Check your screen-time report and pick one app to cut by half today.",
                ],
                [
                    "Set a hard daily cap for social apps and stick to it.",
                    "Schedule one real, in-person or call-based catch-up instead of scrolling.",
                    "Go one full evening with social apps closed entirely.",
                ],
            ],
            "tip": "You don't need to quit social media - just add a little friction before you open it.",
        },
        {
            "field": "stress_0_10",
            "lower_is_better": True,
            "theme": "Stress Reset",
            "icon": "🧘",
            "needs_work": lambda v: v is not None and v >= 6,
            "severity": lambda v: min(1.0, max(0.0, (v - 6) / 4)) if v is not None else 0.0,
            "levels": [
                [
                    "Do a 5-minute breathing or grounding exercise this morning.",
                    "Take three screen-free breaks today, even 2 minutes each.",
                    "Write down one thing that's weighing on you and one small next step.",
                ],
                [
                    "Add a 10-minute mid-day reset away from screens.",
                    "Eat at least one meal today without a screen in front of you.",
                    "Talk to someone about what's actually stressing you out this week.",
                ],
                [
                    "Do your reset at the exact same time every day - make it automatic.",
                    "Identify the single biggest source of stress this week and change one thing about it.",
                    "Protect one full stress-free evening - no work, no doomscrolling.",
                ],
            ],
            "tip": "Short, frequent resets beat one long break - they interrupt the stress build-up earlier.",
        },
        {
            "field": "physical_activity_min_per_day",
            "lower_is_better": False,
            "theme": "Movement",
            "icon": "🏃",
            "needs_work": lambda v: v is None or v < 30,
            "severity": lambda v: min(1.0, max(0.0, (30 - v) / 30)) if v is not None else 1.0,
            "levels": [
                [
                    "Take a 10-15 minute walk, ideally without your phone.",
                    "Stand up and move for 2 minutes every hour you're at a screen.",
                    "Try one new form of movement today (stretching, stairs, a short workout).",
                ],
                [
                    "Extend today's walk or workout to 20-30 minutes.",
                    "Take the stairs, or park/get off farther away, on purpose.",
                    "Move during one call today instead of sitting through it.",
                ],
                [
                    "Do one structured 30+ minute activity today.",
                    "Put movement on your calendar as a fixed daily appointment.",
                    "Look back at this week's movement - keep whatever actually stuck.",
                ],
            ],
            "tip": "Movement is one of the fastest levers for mood and focus - even short bursts count.",
        },
        {
            "field": "notifications_per_day",
            "lower_is_better": True,
            "theme": "Mindful Notifications",
            "icon": "🔕",
            "needs_work": lambda v: v is not None and v > 100,
            "severity": lambda v: min(1.0, max(0.0, (v - 100) / 100)) if v is not None else 0.0,
            "levels": [
                [
                    "Turn off notifications for your three noisiest apps.",
                    "Batch-check messages at set times instead of reacting instantly.",
                    "Switch your phone to grayscale or Do Not Disturb during focus blocks.",
                ],
                [
                    "Turn off notifications for every non-essential app, not just the noisiest three.",
                    "Set two fixed check-in windows today and only check messages then.",
                    "Mute your busiest group chat for the rest of the week.",
                ],
                [
                    "Keep your phone in another room during every work block today.",
                    "Let only calls/texts from close contacts through for one full day.",
                    "Review what you muted this week - permanently turn off what you didn't miss.",
                ],
            ],
            "tip": "Fewer interruptions means fewer chances to fall into an unplanned scrolling session.",
        },
        {
            "field": "focus_0_100",
            "lower_is_better": False,
            "theme": "Deep Focus",
            "icon": "🎯",
            "needs_work": lambda v: v is not None and v < 60,
            "severity": lambda v: min(1.0, max(0.0, (60 - v) / 60)) if v is not None else 0.0,
            "levels": [
                [
                    "Block 25-45 minutes for one task with your phone in another room.",
                    "Close unused tabs/apps before you start a focus block.",
                    "Note what broke your focus today so you can remove it tomorrow.",
                ],
                [
                    "Run two focus blocks today instead of one.",
                    "Remove yesterday's top distraction before you even start.",
                    "Batch email/messages to two fixed times instead of checking freely.",
                ],
                [
                    "Protect your best-energy hour today with zero interruptions.",
                    "Plan tomorrow's single top priority tonight, before you stop working.",
                    "Try a full 'single-tasking' day - one thing at a time, nothing in parallel.",
                ],
            ],
            "tip": "Protecting one deep-focus block a day matters more than trying to be 'always on'.",
        },
    ]

    _DEFAULT_THEME = {
        "theme": "Maintain Your Momentum",
        "icon": "✅",
        "levels": [
            [
                "Keep today's habits steady - consistency is the win here.",
                "Notice one habit that's working well and do it again on purpose.",
                "Check in with how you feel at the end of the day.",
            ],
        ],
        "tip": "You're already doing well on this front - protecting it is the goal, not overhauling it.",
    }

    _CLOSING_THEME = {
        "theme": "Reflect & Reset",
        "icon": "🗓️",
        "levels": [
            [
                "Look back at the week: which day felt best, and why?",
                "Pick ONE habit from this week to keep going into next week.",
                "Run a new prediction to see how your habits shifted.",
            ],
        ],
        "tip": "A weekly reflection turns a one-off good day into a repeatable habit.",
    }

    # ------------------------------------------------------
    # Public API
    # ------------------------------------------------------

    def generate(
        self,
        health_class: Optional[str],
        wellness_score: Optional[float],
        persona: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        schedule_type: Optional[str] = None,
        theme_streaks: Optional[Dict[str, int]] = None,
        main_use_purpose: Optional[str] = None,
        preferred_effort: Optional[str] = None,
        work_screen_required: bool = False,
        usual_sleep_time: Optional[str] = None,
        usual_wake_time: Optional[str] = None,
    ) -> ImprovementPlan:
        """`history` and `schedule_type` are both optional and both only
        ever re-rank what `user_data` already flagged:

          - history gives each field a personal baseline, so a drop from
            the user's own normal counts even when the absolute value is
            still acceptable. Without it the behaviour is exactly the
            old absolute-threshold one, which is what keeps every
            existing caller and every stored plan valid.
          - schedule_type lifts routine-anchored themes for someone
            whose days are not alike, because "same bedtime nightly" is
            advice they cannot act on.
          - theme_streaks is how many consecutive PREVIOUS weeks each
            theme has already been a focus area. It is what makes week
            two onward a continuation rather than a restart: a theme
            carried over starts at the tier the user has already
            reached, so somebody in their third week on sleep is not
            handed "set a fixed bedtime" for the third time. Absent, or
            all zeros, and the behaviour is exactly the week-one one.
          - main_use_purpose and work_screen_required re-rank on the
            same terms as schedule_type: they lift the themes this
            particular person can act on and lower the ones their life
            overrules. Somebody whose job is a screen cannot follow
            "cut your screen time", and leading with it is how an app
            makes itself easy to stop opening.
          - preferred_effort moves the TIER rather than the ranking -
            the same habit, at the pace the user asked to be pushed.

        All of them default to "not told", and at those defaults this
        produces exactly the plan it produced before they existed.
        """
        user_data = user_data or {}
        theme_streaks = theme_streaks or {}

        focus_rules = self._select_focus_rules(
            user_data, history, schedule_type,
            main_use_purpose=main_use_purpose,
            work_screen_required=work_screen_required,
            declared_sleep_hours=self.declared_sleep_hours(
                usual_sleep_time, usual_wake_time,
            ),
        )
        # Clamped to +-1 by the table, and applied to every day below.
        effort_shift = self._EFFORT_TIER_SHIFT.get(
            (preferred_effort or "").strip().lower(), 0,
        )
        intro_all = self._build_intro_i18n(health_class, wellness_score, persona, focus_rules)
        intro = intro_all["en"]

        days: List[DailyPlan] = []
        occurrence_count: Dict[str, int] = {}
        for i in range(6):
            rule = focus_rules[i % len(focus_rules)] if focus_rules else self._DEFAULT_THEME
            theme = rule["theme"]
            occurrence = occurrence_count.get(theme, 0)
            occurrence_count[theme] = occurrence + 1

            levels = rule["levels"]
            # Carried forward from the weeks this theme has already been
            # worked on. Capped by the number of levels that exist, so
            # a long streak lands on the hardest tier and stays there
            # rather than falling off the end - and a theme the user is
            # meeting for the first time is unaffected.
            carried = max(0, int(theme_streaks.get(theme, 0) or 0))
            # The user's own answer about pace. Floored at 0 so "low"
            # cannot drop below the first tier, and the min() below
            # already stops "high" running off the end.
            level_index = min(
                max(0, occurrence + carried + effort_shift), len(levels) - 1,
            )
            tier_label = _TIER_LABELS[min(level_index, len(_TIER_LABELS) - 1)] if len(levels) > 1 else ""

            composed = self._compose_tasks(
                rule, user_data, i, occurrence, carried, effort_shift=effort_shift,
            )
            days.append(
                DailyPlan(
                    day_number=i + 1,
                    day_label=f"Day {i + 1}",
                    theme=theme,
                    icon=rule["icon"],
                    tasks=composed or list(levels[level_index]),
                    tip=rule["tip"],
                    tier_label=tier_label,
                    exercises=self._compose_exercises(
                        rule, user_data, i, occurrence, carried,
                        effort_shift=effort_shift,
                    ),
                    text_i18n=self._day_text_i18n(theme, i + 1, level_index, len(levels)),
                )
            )

        # Day 7 is always a reflection day, regardless of focus areas.
        days.append(
            DailyPlan(
                day_number=7,
                day_label="Day 7",
                theme=self._CLOSING_THEME["theme"],
                icon=self._CLOSING_THEME["icon"],
                tasks=list(self._CLOSING_THEME["levels"][0]),
                tip=self._CLOSING_THEME["tip"],
                exercises=self._compose_exercises(
                    {"exercise_theme": "reflection", "field": ""}, user_data, 6, 0),
                text_i18n=self._day_text_i18n(self._CLOSING_THEME["theme"], 7, 0, 1),
            )
        )

        areas = [r["theme"] for r in focus_rules] or [self._DEFAULT_THEME["theme"]]
        return ImprovementPlan(
            intro=intro,
            focus_areas=areas,
            days=days,
            text_i18n={"intro": intro_all},
            focus_areas_i18n=[
                dict(_THEME_I18N.get(name, {lang: name for lang in LANGUAGES}))
                for name in areas
            ],
        )

    @staticmethod
    def _day_text_i18n(
        theme: str, day_number: int, level_index: int, level_count: int,
    ) -> Dict[str, Dict[str, str]]:
        """A day's wrapper text in every language.

        The tier label is only meaningful for a theme that recurs with
        escalating levels; a single-level theme gets an empty string in
        every language rather than a translated label for a tier that
        does not exist.
        """
        theme_all = _THEME_I18N.get(theme, {lang: theme for lang in LANGUAGES})
        tip_all = _TIP_I18N.get(theme, {lang: "" for lang in LANGUAGES})
        if level_count > 1:
            tier_all = _TIER_LABEL_I18N[min(level_index, len(_TIER_LABEL_I18N) - 1)]
        else:
            tier_all = {lang: "" for lang in LANGUAGES}
        return {
            "day_label": {
                lang: _DAY_LABEL_I18N[lang].format(n=day_number) for lang in LANGUAGES
            },
            "theme": dict(theme_all),
            "tip": dict(tip_all),
            "tier_label": dict(tier_all),
        }

    # ------------------------------------------------------
    # Internals
    # ------------------------------------------------------

    # Which exercise-library theme each habit rule draws from. Kept as a
    # mapping rather than renaming the rules, so the severity ranking
    # and the wording stay independently changeable.
    _EXERCISE_THEME_FOR_FIELD = {
        "sleep_hours": "sleep",
        "total_screen_min": "screen",
        "social_min": "screen",
        "night_usage_min": "night",
        "pre_sleep_screen_min": "night",
        "phone_pickups_per_day": "focus",
        "notifications_per_day": "focus",
        "focus_level_1_10": "focus",
        "stress_0_10": "mood",
        "social_comparison_1_10": "mood",
        "physical_activity_min_per_day": "movement",
    }

    _SLOT_FOR_THEME = {
        "sleep": "before_bed",
        "night": "before_bed",
        "screen": "midday",
        "focus": "morning",
        "mood": "anytime",
        "movement": "midday",
        "reflection": "evening",
    }

    def _exercise_theme(self, rule: Dict[str, Any]) -> str:
        if rule.get("exercise_theme"):
            return str(rule["exercise_theme"])
        return self._EXERCISE_THEME_FOR_FIELD.get(str(rule.get("field", "")), "reflection")

    def _compose_exercises(
        self, rule: Dict[str, Any], user_data: Dict[str, Any], day_index: int,
        occurrence: int, carried: int = 0, effort_shift: int = 0,
    ) -> List[Dict[str, Any]]:
        """Three exercises for one day, bound to this user's own value.

        Deterministic in (theme, day, occurrence, carried): the same user
        opening the same plan twice sees the same week, which is what
        makes a plan followable. Varied ACROSS days because the template
        index walks with the day - the old version repeated one of three
        fixed sets, so a fortnight of plans contained six distinct days.

        `carried` is how many consecutive previous weeks this theme has
        already been worked on. It moves BOTH the tier and the template
        index, and it has to move both: `compose()` builds its text from
        the template alone and never reads the tier, so raising the tier
        by itself changes the label above three tasks that are word for
        word the ones the user was given last week. A third week on
        sleep that opens with "set a fixed bedtime" for the third time
        is not a plan, it is a loop. At 0 - a first week, or a theme met
        for the first time - every value here is exactly what it was
        before this parameter existed.
        """
        from config.exercise_library import THEMES_BY_KEY, TIERS, compose

        theme_key = self._exercise_theme(rule)
        theme = THEMES_BY_KEY.get(theme_key)
        if theme is None:
            return []

        field_name = theme.field
        raw = user_data.get(field_name) if field_name else None
        try:
            current = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            current = None

        # `effort_shift` is the user's own answer about pace, and it has
        # to move the TEMPLATE as well as the tier for the same reason
        # `carried` does - compose() builds its text from the template
        # alone and never reads the tier, so shifting the tier by itself
        # relabels three tasks that are word for word the ones a
        # different setting would have produced.
        step = max(0, carried) + effort_shift
        tier = TIERS[min(max(0, occurrence + step), len(TIERS) - 1)]
        slot = self._SLOT_FOR_THEME.get(theme_key, "anytime")
        # `compose()` selects with `template_index % len(templates)`, so
        # the DAY's contribution has to be coprime with the template
        # count or it cancels out entirely. It was `day_index * 3`, and
        # most themes have 3 or 6 templates: 3-template themes
        # (reflection, night, movement) gave day_index*3 % 3 == 0 for
        # every day, so all six days of a plan were byte-identical -
        # which is exactly what a healthy user saw, six copies of
        # "Maintain Your Momentum" with the same tasks. 6-template
        # themes collapsed to two distinct days for the same reason.
        #
        # Striding the day by 1 can never cancel, and spacing the three
        # daily slots by a third of the library keeps them apart within
        # the day.
        template_count = max(1, len(theme.templates))
        slot_step = max(1, template_count // 3)
        out: List[Dict[str, Any]] = []
        for offset in range(3):
            index = day_index + offset * slot_step + max(0, step)
            exercise = compose(theme_key, index, slot, tier, current)
            if exercise is None:
                continue
            out.append({
                "theme": exercise.theme,
                "slot": exercise.slot,
                "tier": exercise.tier,
                "text": exercise.text,
                "field": exercise.field,
                "current": exercise.current,
                "target": exercise.target,
            })
        return out

    def _compose_tasks(
        self, rule: Dict[str, Any], user_data: Dict[str, Any], day_index: int,
        occurrence: int, carried: int = 0, effort_shift: int = 0,
    ) -> List[str]:
        """The English strings, for callers still reading `tasks`."""
        return [
            e["text"].get("en", "")
            for e in self._compose_exercises(
                rule, user_data, day_index, occurrence, carried, effort_shift,
            )
            if e["text"].get("en")
        ]

    # How far below their own baseline a field has to drift before that
    # counts as a personal regression worth acting on. 12% is roughly
    # the point where a change stops looking like ordinary day-to-day
    # noise on these fields.
    _PERSONAL_DRIFT_FLOOR = 0.12

    @staticmethod
    def personal_baselines(
        history: Optional[List[Dict[str, Any]]],
        fields: List[str],
        min_days: int = 4,
    ) -> Dict[str, float]:
        """Median of each field over the user's own recent history.

        Median rather than mean: one catastrophic night should not drag
        a whole week's baseline down and then make every following night
        look like an improvement.

        Days the user marked as exceptions are dropped, for the same
        reason every other statistic drops them - a day they explicitly
        said was unusual must not define what "usual" means for them.
        Fields with fewer than `min_days` real values get no baseline at
        all rather than one computed from two points.
        """
        if not history:
            return {}
        out: Dict[str, float] = {}
        for name in fields:
            values = [
                row[name] for row in history
                if row and not row.get("excluded")
                and isinstance(row.get(name), (int, float))
                and not isinstance(row.get(name), bool)
            ]
            if len(values) < min_days:
                continue
            values.sort()
            mid = len(values) // 2
            out[name] = (
                values[mid] if len(values) % 2
                else (values[mid - 1] + values[mid]) / 2
            )
        return out

    def _personal_severity(
        self, rule: Dict[str, Any], value: Any, baseline: Optional[float],
    ) -> float:
        """How far this value has slipped from THIS user's own normal.

        Direction matters: for a field where lower is better, a value
        above the baseline is the regression; for a "higher is better"
        field it is the other way round. Returns 0 when the user is at
        or better than their own baseline, so this can only ever add
        urgency, never excuse a genuinely bad absolute value.
        """
        if baseline in (None, 0) or not isinstance(value, (int, float)):
            return 0.0
        lower_is_better = rule.get("lower_is_better", False)
        drift = (value - baseline) / abs(baseline)
        if not lower_is_better:
            drift = -drift          # dropping below baseline is the bad direction
        if drift <= self._PERSONAL_DRIFT_FLOOR:
            return 0.0
        # 12% drift -> ~0, 60% drift -> 1.0
        return min(1.0, (drift - self._PERSONAL_DRIFT_FLOOR) / 0.48)

    # The healthy target each rule is measured against, in the rule's
    # own units. Written out rather than derived from `needs_work`,
    # because those are lambdas and a threshold read out of a closure is
    # a threshold nobody can check.
    _RULE_TARGETS = {
        "sleep_hours": 7.0,
        "social_min": 90.0,
        "stress_0_10": 6.0,
        "physical_activity_min_per_day": 30.0,
        "notifications_per_day": 100.0,
        "focus_0_100": 60.0,
    }

    # How far past the target a signal has to sit before it counts as a
    # strength rather than as merely acceptable. Without a margin, a
    # value one minute the right side of the line would be celebrated as
    # a habit worth protecting, which is not true and would make the
    # whole "what is already working" list meaningless.
    _STRENGTH_MARGIN = 0.10

    def signal_tracks(
        self,
        user_data: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        schedule_type: Optional[str] = None,
        main_use_purpose: Optional[str] = None,
        work_screen_required: bool = False,
        usual_sleep_time: Optional[str] = None,
        usual_wake_time: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """The two halves of a week's plan, side by side.

        A plan that only ever names what is wrong reads as a list of
        faults, and it also throws away the more useful half of the
        picture: the habits that are already holding. So this returns
        both.

          `strengthen` - the signals that need work, weakest first, each
            with the user's own current value and the target it is being
            measured against. Same severity arithmetic the 7-day plan
            uses (absolute vs personal, whichever is worse), so the two
            can never disagree about what is wrong.

          `maintain` - the signals already comfortably the right side of
            their target, with how much room to spare. These are what a
            week's plan is protecting; naming them is the difference
            between "keep going" and a number the user can actually
            defend.

        Every entry carries the user's real value. Nothing here is
        generic advice: a signal with no value logged simply does not
        appear on either list, rather than being guessed at.
        """
        baselines = self.personal_baselines(
            history, [r["field"] for r in self._HABIT_RULES],
        )
        strengthen: List[Dict[str, Any]] = []
        maintain: List[Dict[str, Any]] = []

        for rule in self._HABIT_RULES:
            field_name = rule["field"]
            value = user_data.get(field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            target = self._RULE_TARGETS.get(field_name)
            if target is None:
                continue

            try:
                absolute = rule["severity"](value) if rule["needs_work"](value) else 0.0
            except TypeError:
                absolute = 0.0
            personal = self._personal_severity(rule, value, baselines.get(field_name))
            severity = max(absolute, personal)

            entry = {
                "field": field_name,
                "theme": rule["theme"],
                "theme_i18n": dict(_THEME_I18N.get(rule["theme"], {})),
                "icon": rule["icon"],
                "current": round(float(value), 1),
                "target": target,
                "lower_is_better": bool(rule.get("lower_is_better", False)),
                "baseline": baselines.get(field_name),
            }

            if severity > 0:
                # The same weighting the 7-day plan ranks by, so the two
                # cannot disagree about which signal leads the week.
                severity *= self._theme_weight(
                    rule["theme"], schedule_type,
                    main_use_purpose, work_screen_required,
                    self.declared_sleep_hours(usual_sleep_time, usual_wake_time),
                )
                # Reported clamped, SORTED unclamped. Clamping first is
                # what made this panel disagree with the week's plan:
                # two signals at 1.0 and 1.4 both become 1.0, the sort
                # sees a tie, and the order falls back to whatever
                # position the rule happens to occupy in _HABIT_RULES.
                # The panel then names a different worst signal than the
                # theme the plan leads with, which is the app
                # contradicting itself on one screen.
                entry["severity"] = round(min(1.0, severity), 3)
                entry["_rank"] = severity
                strengthen.append(entry)
                continue

            # Comfortably the right side of the line, not merely on it.
            margin = (target - value) / target if entry["lower_is_better"] else (value - target) / target
            if margin >= self._STRENGTH_MARGIN:
                entry["margin"] = round(margin, 3)
                maintain.append(entry)

        strengthen.sort(key=lambda e: e.pop("_rank", e.get("severity", 0.0)), reverse=True)
        maintain.sort(key=lambda e: e.get("margin", 0.0), reverse=True)
        return {"strengthen": strengthen, "maintain": maintain}

    @staticmethod
    def declared_sleep_hours(
        usual_sleep_time: Optional[str], usual_wake_time: Optional[str],
    ) -> Optional[float]:
        """Hours between the two "HH:MM" times the user gave, or None.

        Wraps past midnight, which is the ordinary case - 23:00 to 07:00
        is eight hours, not minus sixteen. None for anything unparseable
        rather than a guess, because a guessed sleep window would change
        which theme leads somebody's week.
        """
        def minutes(value: Optional[str]) -> Optional[int]:
            try:
                hh, mm = str(value).strip().split(":")
                hh, mm = int(hh), int(mm)
            except (AttributeError, TypeError, ValueError):
                return None
            if not (0 <= hh < 24 and 0 <= mm < 60):
                return None
            return hh * 60 + mm

        start, end = minutes(usual_sleep_time), minutes(usual_wake_time)
        if start is None or end is None:
            return None
        span = (end - start) % (24 * 60)
        return round(span / 60.0, 2) if span else None

    def _theme_weight(
        self,
        theme: str,
        schedule_type: Optional[str],
        main_use_purpose: Optional[str],
        work_screen_required: bool,
        declared_sleep_hours: Optional[float] = None,
    ) -> float:
        """The multiplier this person's own answers put on one theme.

        Every term is additive and then floored, so no combination of
        answers can drive a theme to zero: an answer re-ranks what the
        user's numbers already flagged, and is never allowed to silence
        a signal entirely. Somebody whose job is a screen AND who says
        they mainly work still hears about their sleep.
        """
        weight = 1.0
        if schedule_type in self._IRREGULAR_SCHEDULES:
            weight += self._IRREGULAR_BOOST.get(theme, 0.0)
        if work_screen_required:
            weight += self._WORK_SCREEN_WEIGHT.get(theme, 0.0)
        purpose = (main_use_purpose or "").strip().lower()
        weight += self._PURPOSE_WEIGHT.get(purpose, {}).get(theme, 0.0)
        if (
            theme == "Sleep Recovery"
            and declared_sleep_hours is not None
            and declared_sleep_hours < self._SHORT_DECLARED_SLEEP_HOURS
        ):
            weight += self._DECLARED_SLEEP_BOOST
        # 0.5 rather than 0.0: a down-weighted theme falls down the
        # ranking, it does not disappear from the app.
        return max(0.5, weight)

    def _select_focus_rules(
        self,
        user_data: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        schedule_type: Optional[str] = None,
        main_use_purpose: Optional[str] = None,
        work_screen_required: bool = False,
        declared_sleep_hours: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Pick the habit areas that actually need work, weakest signal first.

        Severity is the WORSE of two readings, which is the whole point
        of making the signal personal without making it permissive:

          - absolute: how far the value sits from a healthy target.
            Keeps a chronically bad habit flagged even though it is that
            user's normal - someone who always sleeps four hours must
            not be told their sleep is fine because it matches their
            baseline.
          - personal: how far the value has slipped from that user's own
            median. Catches a real regression that is not yet absolutely
            bad - 8h down to 6.5h is worth naming even though 6.5h is
            not alarming in isolation.

        Taking max() means personalisation can only ever raise urgency,
        never lower it below the absolute floor.
        """
        baselines = self.personal_baselines(
            history, [r["field"] for r in self._HABIT_RULES],
        )
        needing_work: List[tuple[float, Dict[str, Any]]] = []
        for rule in self._HABIT_RULES:
            value = user_data.get(rule["field"])
            baseline = baselines.get(rule["field"])
            try:
                absolute = rule["severity"](value) if rule["needs_work"](value) else 0.0
            except TypeError:
                absolute = 0.0
            personal = self._personal_severity(rule, value, baseline)
            severity = max(absolute, personal)
            if severity > 0:
                needing_work.append((severity, rule))

        if needing_work:
            # The user's own answers about their life decide the order.
            # An irregular schedule makes routine-anchored themes the
            # ones that actually pay off - a fixed wake-up time is worth
            # more to someone on rotating shifts than one more screen
            # rule - and a job that requires a screen makes "use it
            # less" the one instruction they cannot follow. This
            # re-ranks; it never invents a focus area that the user's
            # own numbers did not already flag, and never removes one.
            needing_work = [
                (
                    sev * self._theme_weight(
                        rule["theme"], schedule_type,
                        main_use_purpose, work_screen_required,
                        declared_sleep_hours,
                    ),
                    rule,
                )
                for sev, rule in needing_work
            ]
            needing_work.sort(key=lambda pair: pair[0], reverse=True)
            return [rule for _, rule in needing_work[:4]]

        # Nothing flagged as needing work - keep the plan useful by
        # rotating through "maintain" guidance instead of leaving it empty.
        return [self._DEFAULT_THEME]

    @staticmethod
    def _build_intro(
        health_class: Optional[str],
        wellness_score: Optional[float],
        persona: Optional[str],
        focus_rules: List[Dict[str, Any]],
    ) -> str:
        """The English intro. Kept for callers reading the flat field."""
        return ImprovementPlanService._build_intro_i18n(
            health_class, wellness_score, persona, focus_rules)["en"]

    @staticmethod
    def _build_intro_i18n(
        health_class: Optional[str],
        wellness_score: Optional[float],
        persona: Optional[str],
        focus_rules: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """The intro in every shipped language.

        The score, the class band and the persona are substituted into a
        per-language sentence rather than concatenated onto a translated
        stem: Persian and Arabic put the number and the band in a
        different order than English does, and a sentence assembled from
        English-ordered fragments reads as machine output in both.

        The persona itself is not translated - it is a title the persona
        service produces, and inventing a translation for it here would
        put a name on screen that exists nowhere else in the app.
        """
        label = str(health_class or "").strip().lower()
        score_str = f"{wellness_score:.1f}/100" if wellness_score is not None else "N/A"

        band_key = label if label in _INTRO_BY_BAND else "unknown"
        # 50-60 is the bottom of the moderate band and the one place the
        # ordinary moderate sentence lands wrong - see the note on
        # "moderate_low" above.
        if (
            band_key == "moderate"
            and wellness_score is not None
            and MODERATE_LOW_FLOOR <= float(wellness_score) < MODERATE_LOW_CEILING
        ):
            band_key = "moderate_low"
        out: Dict[str, str] = {}
        for lang in LANGUAGES:
            persona_str = (
                _INTRO_PERSONA[lang].format(persona=persona) if persona else ""
            )
            opener = _INTRO_BY_BAND[band_key][lang].format(
                score=score_str, persona=persona_str)
            if focus_rules:
                names = _LIST_SEPARATOR[lang].join(
                    _THEME_I18N.get(r["theme"], {}).get(lang, r["theme"])
                    for r in focus_rules
                )
                opener += _INTRO_FOCUS[lang].format(themes=names)
            out[lang] = opener
        return out
