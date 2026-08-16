"""
config/recommendation_i18n.py
-----------------------------
The four-language text for every recommendation rule (C-2, A-2), plus
the deterministic personalisation that puts the user's own numbers into
it.

Two constraints from the brief shape this file:

  * "The recommendation engine is deliberately deterministic (its rules).
    Do not add any random logic or machine learning. Personalisation
    must come from more parameters inside those same deterministic
    rules." So nothing here chooses, ranks or samples. The rules and
    their order are still decided by SHAP in RecommendationService; this
    module only computes a target from the value the user actually
    logged, with a fixed formula per rule, and supplies the words.

  * "Every recommendation must reference that user's own real number,
    with a reason, an exact action and a success metric." Hence the
    {observed} and {target} placeholders: the advice reads "down from
    your 380 minutes to 330", not "reduce your screen time".

Both the PDF report and the web client render from this one table.
Keeping it in Python rather than duplicating it in JavaScript is the
point - a second copy is how the two drift apart, which is the A-2 bug
in its most expensive form.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

LANGUAGES = ("en", "fa", "ar", "zh")


# --------------------------------------------------------------------
# Deterministic personalisation
# --------------------------------------------------------------------
# One fixed formula per rule, applied to the value the user logged.
# No randomness, no model, no lookup of anyone else's data - the same
# input always produces the same target.

def _reduce_by(fraction: float, floor: float = 0.0) -> Callable[[float], float]:
    return lambda observed: max(floor, round(observed * (1 - fraction)))


def _raise_to(minimum: float, step: float) -> Callable[[float], float]:
    """Nudge upward, but never propose less than the user already does -
    a 'target' below today's value reads as mockery."""
    return lambda observed: max(minimum, round(observed + step, 1))


def _reduce_to(ceiling: float, fraction: float) -> Callable[[float], float]:
    """Whichever is gentler: a proportional cut, or the ceiling. Someone
    already close to the ceiling gets a small step, not a token one."""
    return lambda observed: max(ceiling, round(observed * (1 - fraction)))


TARGETS: dict[str, Callable[[float], float]] = {
    "sleep_hours": _raise_to(7.0, 0.5),
    "pre_sleep_screen_min": _reduce_to(15, 0.4),
    "night_ratio": _reduce_to(0.10, 0.3),
    "stress_0_10": _reduce_by(0.2),
    "physical_activity_min_per_day": _raise_to(30, 10),
    "social_min": _reduce_to(60, 0.2),
    "notifications_per_day": _reduce_by(0.3),
    "total_screen_min": _reduce_by(0.125),          # midpoint of the stated 10-15%
    "fragmentation_index_0_100": _reduce_by(0.2),
    "gaming_ratio": _reduce_to(0.15, 0.25),
    "night_screen_min": _reduce_by(0.3),
    "productivity_0_100": _raise_to(60, 5),
    "sleep_quality_1_10": _raise_to(6, 1),
    # Added with the 16 new rules below. Same shape as the rest: one
    # fixed formula per rule, no randomness and no model.
    "pickups_per_day": _reduce_by(0.2),
    "pickup_density": _reduce_by(0.25),
    "app_opens_per_day": _reduce_by(0.2),
    "app_open_density": _reduce_by(0.25),
    "social_ratio": _reduce_to(0.25, 0.2),
    "work_study_ratio": _reduce_to(0.50, 0.1),
    "other_ratio": _reduce_to(0.15, 0.2),
    "video_min": _reduce_to(60, 0.2),
    "gaming_min": _reduce_to(60, 0.25),
    "pre_sleep_ratio": _reduce_to(0.08, 0.3),
    "mental_fatigue_0_10": _reduce_by(0.2),
    "focus_0_100": _raise_to(60, 5),
    "digital_dependence_0_100": _reduce_by(0.15),
    "caffeine_cups_per_day": _reduce_by(0.25),
    "fomo_1_10": _reduce_by(0.2),
    "social_comparison_1_10": _reduce_by(0.2),
}

# How each number is written out. A ratio is shown as a percentage,
# because "0.18" means nothing on a results page.
UNITS: dict[str, str] = {
    "sleep_hours": "h",
    "pre_sleep_screen_min": "min",
    "night_ratio": "%",
    "stress_0_10": "",
    "physical_activity_min_per_day": "min",
    "social_min": "min",
    "notifications_per_day": "",
    "total_screen_min": "min",
    "fragmentation_index_0_100": "",
    "gaming_ratio": "%",
    "night_screen_min": "min",
    "productivity_0_100": "",
    "sleep_quality_1_10": "",
    "pickups_per_day": "",
    "pickup_density": "",
    "app_opens_per_day": "",
    "app_open_density": "",
    "social_ratio": "%",
    "work_study_ratio": "%",
    "other_ratio": "%",
    "video_min": "min",
    "gaming_min": "min",
    "pre_sleep_ratio": "%",
    "mental_fatigue_0_10": "",
    "focus_0_100": "",
    "digital_dependence_0_100": "",
    "caffeine_cups_per_day": "",
    "fomo_1_10": "",
    "social_comparison_1_10": "",
}

PERCENT_FIELDS = {
    "night_ratio", "gaming_ratio",
    "social_ratio", "work_study_ratio", "other_ratio", "pre_sleep_ratio",
}


def personalise(field: str, user_data: dict[str, Any]) -> dict[str, Optional[float]]:
    """The user's own value for this rule's field, and the target the
    rule's fixed formula produces from it.

    Returns Nones when the field is absent - the caller then renders the
    generic wording rather than a sentence with a hole in it.
    """
    raw = user_data.get(field)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        return {"observed": None, "target": None}

    observed = float(raw)
    formula = TARGETS.get(field)
    target = float(formula(observed)) if formula else None

    if field in PERCENT_FIELDS:
        observed = round(observed * 100, 1)
        target = round(target * 100, 1) if target is not None else None

    return {"observed": observed, "target": target}


# --------------------------------------------------------------------
# The words
# --------------------------------------------------------------------
# {observed} = what this user logged, {target} = what the rule's formula
# produces from it. Any string without a placeholder is one where a
# number would not have helped.

RULE_TEXT: dict[str, dict[str, dict[str, str]]] = {
    "sleep_hours": {
        "title": {
            "en": "Give sleep more room",
            "fa": "به خواب جای بیشتری بده",
            "ar": "امنح النوم مساحة أكبر",
            "zh": "给睡眠留出更多空间",
        },
        "description": {
            "en": "You logged {observed} hours. Sleep is the signal that moves your score most, and it is also the one most affected by the hour before bed.",
            "fa": "تو {observed} ساعت ثبت کردی. خواب سیگنالی است که بیشترین اثر را روی امتیازت دارد، و خودش هم بیش از همه از ساعت پیش از خواب اثر می‌گیرد.",
            "ar": "سجّلت {observed} ساعة. النوم هو الإشارة الأكثر تأثيراً في درجتك، وهو أيضاً الأكثر تأثراً بالساعة التي تسبق النوم.",
            "zh": "你记录了 {observed} 小时。睡眠是对你分数影响最大的信号，同时它自己也最受睡前那一小时的影响。",
        },
        "action": {
            "en": "Aim for {target} hours, and move lights-out fifteen minutes earlier rather than trying to wake later.",
            "fa": "{target} ساعت را هدف بگیر، و به‌جای تلاش برای دیرتر بیدارشدن، پانزده دقیقه زودتر چراغ را خاموش کن.",
            "ar": "استهدف {target} ساعة، وقدّم إطفاء الضوء خمس عشرة دقيقة بدل محاولة الاستيقاظ متأخراً.",
            "zh": "以 {target} 小时为目标，把熄灯时间提前十五分钟，而不是试着晚点起床。",
        },
        "success_metric": {
            "en": "{target} hours or more on at least 5 of the next 7 nights.",
            "fa": "{target} ساعت یا بیشتر، در دست‌کم ۵ شب از ۷ شب آینده.",
            "ar": "{target} ساعة أو أكثر في 5 ليالٍ على الأقل من الليالي السبع القادمة.",
            "zh": "在接下来七晚中至少五晚达到 {target} 小时或以上。",
        },
    },
    "pre_sleep_screen_min": {
        "title": {
            "en": "Quieten the last hour",
            "fa": "ساعت آخر را آرام کن",
            "ar": "هدّئ الساعة الأخيرة",
            "zh": "让睡前一小时安静下来",
        },
        "description": {
            "en": "You logged {observed} minutes of screen time in the hour before sleep. That hour affects how quickly you fall asleep more than the total does.",
            "fa": "تو {observed} دقیقه زمان صفحه در ساعت پیش از خواب ثبت کردی. آن یک ساعت، بیشتر از کل زمان، روی سرعت به‌خواب‌رفتنت اثر می‌گذارد.",
            "ar": "سجّلت {observed} دقيقة أمام الشاشة في الساعة التي تسبق النوم. تلك الساعة تؤثر في سرعة نومك أكثر من الإجمالي.",
            "zh": "你在睡前一小时记录了 {observed} 分钟的屏幕时间。相比总时长，这一小时对你多快入睡的影响更大。",
        },
        "action": {
            "en": "Bring it down to {target} minutes by moving one habit — the last scroll, the last episode — to before dinner.",
            "fa": "با جابه‌جا کردن یک عادت — آخرین اسکرول، آخرین قسمت — به قبل از شام، آن را به {target} دقیقه برسان.",
            "ar": "اخفضها إلى {target} دقيقة بنقل عادة واحدة — آخر تصفح، آخر حلقة — إلى ما قبل العشاء.",
            "zh": "把一个习惯——最后一次刷手机、最后一集剧——挪到晚饭前，把它降到 {target} 分钟。",
        },
        "success_metric": {
            "en": "Under {target} minutes before sleep on most nights this week.",
            "fa": "کمتر از {target} دقیقه پیش از خواب، در بیشتر شب‌های این هفته.",
            "ar": "أقل من {target} دقيقة قبل النوم في معظم ليالي هذا الأسبوع.",
            "zh": "本周大多数晚上睡前低于 {target} 分钟。",
        },
    },
    "night_ratio": {
        "title": {
            "en": "Shift use out of the small hours",
            "fa": "استفاده را از دل شب بیرون بیاور",
            "ar": "انقل الاستخدام خارج ساعات الليل المتأخرة",
            "zh": "把使用挪出深夜时段",
        },
        "description": {
            "en": "{observed}% of your screen time happened during night hours. Late use pushes sleep onset back even when the total is reasonable.",
            "fa": "{observed}٪ از زمان صفحه‌ات در ساعات شب بوده. استفاده‌ی دیرهنگام شروع خواب را عقب می‌اندازد، حتی وقتی کل زمان معقول است.",
            "ar": "{observed}٪ من وقت شاشتك كان في ساعات الليل. الاستخدام المتأخر يؤخّر بدء النوم حتى لو كان الإجمالي معقولاً.",
            "zh": "你 {observed}% 的屏幕时间发生在夜间。即使总量合理，深夜使用也会推迟入睡。",
        },
        "action": {
            "en": "Aim for {target}% by setting one hard cutoff time and charging the phone outside the bedroom.",
            "fa": "با تعیین یک ساعت قطع قطعی و شارژ کردن گوشی بیرون از اتاق خواب، {target}٪ را هدف بگیر.",
            "ar": "استهدف {target}٪ بتحديد وقت توقف صارم وشحن الهاتف خارج غرفة النوم.",
            "zh": "设定一个硬性的截止时间，并把手机放在卧室外充电，以 {target}% 为目标。",
        },
        "success_metric": {
            "en": "Night-hours use at or under {target}% of your total this week.",
            "fa": "استفاده در ساعات شب، {target}٪ از کل یا کمتر، در این هفته.",
            "ar": "استخدام ساعات الليل عند {target}٪ من إجماليك أو أقل هذا الأسبوع.",
            "zh": "本周夜间使用占总量的 {target}% 或更低。",
        },
    },
    "stress_0_10": {
        "title": {
            "en": "Build in a reset",
            "fa": "یک وقفه‌ی بازنشانی بگذار",
            "ar": "أدخِل استراحة لإعادة الضبط",
            "zh": "安排一次重启",
        },
        "description": {
            "en": "You rated your stress at {observed}. This is your own rating of your own day, not a diagnosis — but it tracks closely with fragmented attention.",
            "fa": "تو استرست را {observed} ارزیابی کردی. این ارزیابی خودت از روز خودت است، نه یک تشخیص — اما با تکه‌تکه‌شدن تمرکز هم‌حرکت است.",
            "ar": "قيّمت توترك بـ {observed}. هذا تقييمك أنت ليومك أنت، لا تشخيص — لكنه يتحرك مع تشتت الانتباه.",
            "zh": "你把压力评为 {observed}。这是你自己对自己一天的评分，不是诊断——但它与注意力的碎片化密切相关。",
        },
        "action": {
            "en": "Take one deliberate screen-free break a day, long enough to be noticed — ten minutes counts.",
            "fa": "روزی یک وقفه‌ی عمدی بدون صفحه بگیر، آن‌قدر که حس شود — ده دقیقه هم حساب است.",
            "ar": "خذ استراحة واحدة مقصودة بلا شاشة يومياً، طويلة بما يكفي لتُلاحَظ — عشر دقائق تكفي.",
            "zh": "每天有意识地休息一次、完全离开屏幕，久到能被感觉到——十分钟就算。",
        },
        "success_metric": {
            "en": "A stress rating at or under {target} on 5 or more days this week.",
            "fa": "امتیاز استرس {target} یا کمتر، در ۵ روز یا بیشتر از این هفته.",
            "ar": "تقييم توتر عند {target} أو أقل في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天压力评分在 {target} 或以下。",
        },
    },
    "physical_activity_min_per_day": {
        "title": {
            "en": "Move a little more",
            "fa": "کمی بیشتر تحرک داشته باش",
            "ar": "تحرّك أكثر قليلاً",
            "zh": "多活动一点",
        },
        "description": {
            "en": "You logged {observed} minutes of activity. Movement shows up in this app mainly through sleep and focus rather than on its own.",
            "fa": "تو {observed} دقیقه فعالیت ثبت کردی. تحرک در این برنامه بیشتر از راه خواب و تمرکز دیده می‌شود تا به‌تنهایی.",
            "ar": "سجّلت {observed} دقيقة من النشاط. الحركة تظهر في هذا التطبيق أساساً عبر النوم والتركيز لا بذاتها.",
            "zh": "你记录了 {observed} 分钟的活动。在这个应用里，运动主要通过睡眠和专注度体现，而不是自己单独出现。",
        },
        "action": {
            "en": "Get to {target} minutes. A walk counts, and it does not need to be one continuous block.",
            "fa": "به {target} دقیقه برس. پیاده‌روی هم حساب است، و لازم نیست یک‌جا و پیوسته باشد.",
            "ar": "اصل إلى {target} دقيقة. المشي يُحتسب، ولا يلزم أن يكون كتلة واحدة متصلة.",
            "zh": "达到 {target} 分钟。散步也算，而且不必是连续的一整段。",
        },
        "success_metric": {
            "en": "{target} minutes or more on at least 5 of the next 7 days.",
            "fa": "{target} دقیقه یا بیشتر، در دست‌کم ۵ روز از ۷ روز آینده.",
            "ar": "{target} دقيقة أو أكثر في 5 أيام على الأقل من الأيام السبعة القادمة.",
            "zh": "在接下来七天中至少五天达到 {target} 分钟或以上。",
        },
    },
    "social_min": {
        "title": {
            "en": "Trim the social feed",
            "fa": "از شبکه‌های اجتماعی کم کن",
            "ar": "قلّل من تطبيقات التواصل",
            "zh": "削减社交动态",
        },
        "description": {
            "en": "You logged {observed} minutes on social apps. For most people this one tracks with how much they compare themselves to others, more than with total time.",
            "fa": "تو {observed} دقیقه در شبکه‌های اجتماعی ثبت کردی. برای بیشتر آدم‌ها این یکی بیشتر با میزان مقایسه‌ی خود با دیگران هم‌حرکت است تا با کل زمان.",
            "ar": "سجّلت {observed} دقيقة على تطبيقات التواصل. عند معظم الناس ترتبط هذه بمقدار مقارنتهم بأنفسهم مع الآخرين أكثر من ارتباطها بالوقت الإجمالي.",
            "zh": "你在社交应用上记录了 {observed} 分钟。对大多数人来说，这一项更多地与他们把自己和别人比较的程度相关，而不是和总时长。",
        },
        "action": {
            "en": "Set a {target}-minute daily limit, and mute a handful of accounts rather than trying to use the apps less in general.",
            "fa": "یک محدودیت روزانه‌ی {target} دقیقه‌ای بگذار، و به‌جای تلاش برای کم‌کردن کلی استفاده، چند حساب را بی‌صدا کن.",
            "ar": "اضبط حداً يومياً قدره {target} دقيقة، واكتم حفنة من الحسابات بدل محاولة تقليل الاستخدام عموماً.",
            "zh": "设定每天 {target} 分钟的上限，并静音几个账号，而不是笼统地想少用这些应用。",
        },
        "success_metric": {
            "en": "Under {target} minutes on 5 or more days this week.",
            "fa": "کمتر از {target} دقیقه، در ۵ روز یا بیشتر از این هفته.",
            "ar": "أقل من {target} دقيقة في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天低于 {target} 分钟。",
        },
    },
    "notifications_per_day": {
        "title": {
            "en": "Cut the interruptions",
            "fa": "وقفه‌ها را کم کن",
            "ar": "قلّل المقاطعات",
            "zh": "减少打断",
        },
        "description": {
            "en": "You logged {observed} notifications. This is the fastest input in the whole app to change — it takes about a minute and the effect is immediate.",
            "fa": "تو {observed} اعلان ثبت کردی. این سریع‌ترین ورودیِ قابل‌تغییر در کل برنامه است — حدود یک دقیقه وقت می‌برد و اثرش فوری است.",
            "ar": "سجّلت {observed} إشعاراً. هذا أسرع مُدخل يمكن تغييره في التطبيق كله — يستغرق دقيقة تقريباً وأثره فوري.",
            "zh": "你记录了 {observed} 条通知。这是整个应用里最快能改变的输入项——大约一分钟，效果立竿见影。",
        },
        "action": {
            "en": "Get to about {target} by turning off notifications for the single noisiest app, not all of them.",
            "fa": "با خاموش‌کردن اعلان پرسروصداترین برنامه — نه همه‌شان — به حدود {target} برس.",
            "ar": "اصل إلى نحو {target} بإيقاف إشعارات التطبيق الأكثر ضجيجاً وحده، لا كلها.",
            "zh": "只关掉最吵的那一个应用的通知，而不是全部，把它降到大约 {target}。",
        },
        "success_metric": {
            "en": "A daily count at or under {target} for a full week.",
            "fa": "شمار روزانه‌ی {target} یا کمتر، به‌مدت یک هفته‌ی کامل.",
            "ar": "عدد يومي عند {target} أو أقل لأسبوع كامل.",
            "zh": "整整一周每天的数量都在 {target} 或以下。",
        },
    },
    "total_screen_min": {
        "title": {
            "en": "Take the total down a step",
            "fa": "کل زمان را یک پله پایین بیاور",
            "ar": "اخفض الإجمالي درجة",
            "zh": "把总量降一档",
        },
        "description": {
            "en": "You logged {observed} minutes in total. If most of that is work, this number is describing your job rather than your habits — the category split says which.",
            "fa": "تو در مجموع {observed} دقیقه ثبت کردی. اگر بیشترش کار است، این عدد شغلت را توصیف می‌کند نه عادت‌هایت — تفکیک دسته‌ها می‌گوید کدام.",
            "ar": "سجّلت {observed} دقيقة إجمالاً. إن كان معظمها عملاً، فهذا الرقم يصف وظيفتك لا عاداتك — والتقسيم حسب الفئة يخبرك أيهما.",
            "zh": "你总共记录了 {observed} 分钟。如果其中大部分是工作，这个数字描述的是你的职业而不是你的习惯——按类别的拆分会告诉你是哪一种。",
        },
        "action": {
            "en": "Aim for {target} minutes. One removed habit gets you there more reliably than trying to use everything a bit less.",
            "fa": "{target} دقیقه را هدف بگیر. حذف یک عادت مطمئن‌تر از کم‌کردن کمی از همه‌چیز تو را به آن می‌رساند.",
            "ar": "استهدف {target} دقيقة. حذف عادة واحدة يوصلك إلى ذلك بثبات أكثر من تقليل كل شيء قليلاً.",
            "zh": "以 {target} 分钟为目标。去掉一个习惯，比每样都少用一点更可靠地把你带到那里。",
        },
        "success_metric": {
            "en": "A daily total at or under {target} minutes on 5 or more days this week.",
            "fa": "مجموع روزانه‌ی {target} دقیقه یا کمتر، در ۵ روز یا بیشتر از این هفته.",
            "ar": "إجمالي يومي عند {target} دقيقة أو أقل في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天每日总量在 {target} 分钟或以下。",
        },
    },
    "fragmentation_index_0_100": {
        "title": {
            "en": "Gather the day back up",
            "fa": "روز را دوباره جمع کن",
            "ar": "اجمع يومك من جديد",
            "zh": "把一天重新收拢",
        },
        "description": {
            "en": "Your day scored {observed} for fragmentation. Scattered check-ins break sustained attention even when the total screen time is otherwise fine.",
            "fa": "روزت از نظر تکه‌تکه‌شدگی {observed} گرفته. سرزدن‌های پراکنده تمرکز پیوسته را می‌شکنند، حتی وقتی کل زمان صفحه مشکلی ندارد.",
            "ar": "سجّل يومك {observed} في التجزؤ. عمليات التفقد المتناثرة تكسر الانتباه المتواصل حتى لو كان إجمالي وقت الشاشة جيداً.",
            "zh": "你这一天的碎片化得分是 {observed}。零散的查看会打断持续的注意力，即便总屏幕时间本身没什么问题。",
        },
        "action": {
            "en": "Batch phone checks into a few set windows. One protected half-hour is easier to defend than a whole reorganised day.",
            "fa": "سرزدن به گوشی را در چند بازه‌ی مشخص جمع کن. یک نیم‌ساعتِ محافظت‌شده راحت‌تر از یک روزِ کاملاً بازچینی‌شده حفظ می‌شود.",
            "ar": "اجمع تفقد الهاتف في نوافذ محددة قليلة. نصف ساعة محمية أسهل في الدفاع عنها من إعادة تنظيم يوم كامل.",
            "zh": "把查看手机集中到几个固定时段。守住一个受保护的半小时，比重新安排一整天要容易。",
        },
        "success_metric": {
            "en": "A fragmentation score at or under {target} on 5 or more days this week.",
            "fa": "امتیاز تکه‌تکه‌شدگی {target} یا کمتر، در ۵ روز یا بیشتر از این هفته.",
            "ar": "درجة تجزؤ عند {target} أو أقل في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天碎片化得分在 {target} 或以下。",
        },
    },
    "gaming_ratio": {
        "title": {
            "en": "Keep gaming where you want it",
            "fa": "بازی را همان‌جا نگه دار که می‌خواهی",
            "ar": "أبقِ اللعب حيث تريده",
            "zh": "让游戏待在你想要的位置",
        },
        "description": {
            "en": "Gaming was {observed}% of your screen time. Gaming is not a problem here by itself — what matters is whether it is landing after midnight.",
            "fa": "بازی {observed}٪ از زمان صفحه‌ات بوده. بازی به‌خودی‌خود اینجا مشکل نیست — چیزی که مهم است این است که بعد از نیمه‌شب می‌افتد یا نه.",
            "ar": "شكّل اللعب {observed}٪ من وقت شاشتك. اللعب بحد ذاته ليس مشكلة هنا — المهم هو ما إذا كان يقع بعد منتصف الليل.",
            "zh": "游戏占了你屏幕时间的 {observed}%。游戏本身在这里不是问题——重要的是它是否发生在午夜之后。",
        },
        "action": {
            "en": "Set a daily budget that lands around {target}% and put a timer on it, rather than deciding session by session.",
            "fa": "یک سقف روزانه بگذار که حدود {target}٪ در بیاید و برایش تایمر بگذار، به‌جای تصمیم‌گیری جلسه‌به‌جلسه.",
            "ar": "اضبط ميزانية يومية تقارب {target}٪ وضع لها مؤقتاً، بدل أن تقرر جلسة بجلسة.",
            "zh": "设定一个大约落在 {target}% 的每日预算并配上计时器，而不是每次临时决定。",
        },
        "success_metric": {
            "en": "Gaming at or under {target}% of screen time on 5 or more days this week.",
            "fa": "بازی {target}٪ از زمان صفحه یا کمتر، در ۵ روز یا بیشتر از این هفته.",
            "ar": "اللعب عند {target}٪ من وقت الشاشة أو أقل في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天游戏占屏幕时间的 {target}% 或更低。",
        },
    },
    "night_screen_min": {
        "title": {
            "en": "Set a real cutoff",
            "fa": "یک ساعت قطع واقعی بگذار",
            "ar": "حدّد وقت توقف حقيقي",
            "zh": "定一个真正的截止时间",
        },
        "description": {
            "en": "You logged {observed} minutes of screen time during night hours. This is the single input most tied to how rested the next day feels.",
            "fa": "تو {observed} دقیقه زمان صفحه در ساعات شب ثبت کردی. این ورودی بیش از هر ورودی دیگری با سرحال‌بودن روز بعد گره خورده.",
            "ar": "سجّلت {observed} دقيقة أمام الشاشة في ساعات الليل. هذا هو المُدخل الأوثق ارتباطاً بمدى شعورك بالراحة في اليوم التالي.",
            "zh": "你在夜间记录了 {observed} 分钟的屏幕时间。在所有输入里，它与第二天有多精神的关系最紧密。",
        },
        "action": {
            "en": "Bring it to {target} minutes by picking one cutoff time and charging devices outside the bedroom.",
            "fa": "با انتخاب یک ساعت قطع و شارژ کردن دستگاه‌ها بیرون از اتاق خواب، آن را به {target} دقیقه برسان.",
            "ar": "اخفضها إلى {target} دقيقة باختيار وقت توقف واحد وشحن الأجهزة خارج غرفة النوم.",
            "zh": "选定一个截止时间并把设备放在卧室外充电，把它降到 {target} 分钟。",
        },
        "success_metric": {
            "en": "Night-time screen minutes at or under {target} on 5 or more nights this week.",
            "fa": "دقایق صفحه در شب، {target} یا کمتر، در ۵ شب یا بیشتر از این هفته.",
            "ar": "دقائق الشاشة الليلية عند {target} أو أقل في 5 ليالٍ أو أكثر هذا الأسبوع.",
            "zh": "本周有五晚或更多晚夜间屏幕分钟数在 {target} 或以下。",
        },
    },
    "productivity_0_100": {
        "title": {
            "en": "Protect one focused block",
            "fa": "یک بازه‌ی متمرکز را محافظت کن",
            "ar": "احمِ كتلة تركيز واحدة",
            "zh": "守住一个专注时段",
        },
        "description": {
            "en": "You rated productivity at {observed}. A quiet week is allowed to be a quiet week — but this number usually follows sleep and interruptions rather than effort.",
            "fa": "تو بهره‌وری را {observed} ارزیابی کردی. یک هفته‌ی آرام حق دارد آرام باشد — اما این عدد معمولاً دنبال خواب و وقفه‌ها می‌آید نه دنبال تلاش.",
            "ar": "قيّمت الإنتاجية بـ {observed}. من حق الأسبوع الهادئ أن يكون هادئاً — لكن هذا الرقم يتبع عادةً النوم والمقاطعات لا الجهد.",
            "zh": "你把效率评为 {observed}。安静的一周本就可以是安静的——但这个数字通常跟随睡眠和打断，而不是努力程度。",
        },
        "action": {
            "en": "Block one distraction-free period a day and silence notifications inside it.",
            "fa": "روزی یک بازه‌ی بدون حواس‌پرتی کنار بگذار و در همان بازه اعلان‌ها را بی‌صدا کن.",
            "ar": "خصّص فترة واحدة يومياً بلا مشتتات واكتم الإشعارات خلالها.",
            "zh": "每天留出一段不受干扰的时间，并在其中静音通知。",
        },
        "success_metric": {
            "en": "A productivity rating at or above {target} on 5 or more days this week.",
            "fa": "امتیاز بهره‌وری {target} یا بالاتر، در ۵ روز یا بیشتر از این هفته.",
            "ar": "تقييم إنتاجية عند {target} أو أعلى في 5 أيام أو أكثر هذا الأسبوع.",
            "zh": "本周有五天或更多天效率评分在 {target} 或以上。",
        },
    },
    "sleep_quality_1_10": {
        "title": {
            "en": "Steady the routine, not the hours",
            "fa": "نظم را ثابت کن، نه ساعت‌ها را",
            "ar": "ثبّت الروتين لا الساعات",
            "zh": "稳住作息，而不是时长",
        },
        "description": {
            "en": "You rated sleep quality at {observed}. Quality and hours are different numbers and yours may disagree — regularity usually explains the gap.",
            "fa": "تو کیفیت خواب را {observed} ارزیابی کردی. کیفیت و ساعت دو عدد متفاوت‌اند و ممکن است با هم نخوانند — نظم معمولاً این فاصله را توضیح می‌دهد.",
            "ar": "قيّمت جودة النوم بـ {observed}. الجودة والساعات رقمان مختلفان وقد لا يتفقان لديك — والانتظام عادةً يفسّر الفارق.",
            "zh": "你把睡眠质量评为 {observed}。质量和时长是两个不同的数字，你的这两个也可能并不一致——通常是规律性解释了这个差距。",
        },
        "action": {
            "en": "Keep bedtime within half an hour of the same time each night, which is usually easier to hold than a fixed duration.",
            "fa": "زمان خواب را هر شب در محدوده‌ی نیم‌ساعتِ یک ساعت ثابت نگه دار؛ این معمولاً از نگه‌داشتن یک مدت ثابت آسان‌تر است.",
            "ar": "أبقِ موعد النوم ضمن نصف ساعة من الوقت نفسه كل ليلة، فهذا عادةً أسهل من الحفاظ على مدة ثابتة.",
            "zh": "让上床时间每晚都在同一时间前后半小时内，这通常比守住一个固定时长更容易。",
        },
        "success_metric": {
            "en": "A sleep-quality rating at or above {target} on 5 or more nights this week.",
            "fa": "امتیاز کیفیت خواب {target} یا بالاتر، در ۵ شب یا بیشتر از این هفته.",
            "ar": "تقييم جودة نوم عند {target} أو أعلى في 5 ليالٍ أو أكثر هذا الأسبوع.",
            "zh": "本周有五晚或更多晚睡眠质量评分在 {target} 或以上。",
        },
    },

    # ------------------------------------------------------------------
    # The 16 rules added so the model's own findings stop falling on the
    # floor. RecommendationService drops a harmful SHAP factor that has
    # no template (`if template is None: continue`), so before these the
    # engine would name the thing dragging a score down and the result
    # page would say nothing about it. Measured on the at-risk demo
    # profile: 2 of its 4 harmful factors produced no advice at all.
    # ------------------------------------------------------------------
    "pickups_per_day": {
        "title": {
            "en": "Reach for the phone less often",
            "fa": "کمتر سراغ گوشی برو",
            "ar": "امتد إلى هاتفك أقل",
            "zh": "少去拿手机",
        },
        "description": {
            "en": "You picked the phone up {observed} times. How often you reach for it shapes your attention more than how long you hold it.",
            "fa": "تو {observed} بار گوشی را برداشتی. اینکه چند بار سراغش می‌روی، بیشتر از مدتی که در دستت است، توجهت را شکل می‌دهد.",
            "ar": "التقطت هاتفك {observed} مرة. عدد المرات التي تمتد فيها إليه يشكّل انتباهك أكثر من مدة إمساكك به.",
            "zh": "你拿起手机 {observed} 次。你伸手去拿它的频率，比你握着它多久更能塑造你的注意力。",
        },
        "action": {
            "en": "Aim for {target} by parking the phone across the room while you work, so a pickup costs a decision.",
            "fa": "{target} را هدف بگیر: موقع کار گوشی را آن سر اتاق بگذار تا هر بار برداشتنش یک تصمیم بخواهد.",
            "ar": "استهدف {target} بترك الهاتف في الطرف الآخر من الغرفة أثناء العمل، حتى يكلّفك التقاطه قراراً.",
            "zh": "把目标定在 {target}：工作时把手机放在房间另一头，让每次拿起都需要一个决定。",
        },
        "success_metric": {
            "en": "At or under {target} pickups on most days this week.",
            "fa": "{target} بار یا کمتر، در بیشتر روزهای این هفته.",
            "ar": "{target} مرة أو أقل في معظم أيام هذا الأسبوع.",
            "zh": "本周大多数日子不超过 {target} 次。",
        },
    },
    "pickup_density": {
        "title": {
            "en": "Break the checking loop",
            "fa": "حلقه‌ی چک‌کردن را بشکن",
            "ar": "اكسر حلقة التفقّد",
            "zh": "打破反复查看的循环",
        },
        "description": {
            "en": "You picked the phone up about {observed} times per hour of actual use. That is a checking loop rather than using it for something.",
            "fa": "تو حدود {observed} بار در هر ساعتِ استفاده‌ی واقعی گوشی را برداشتی. این یک حلقه‌ی چک‌کردن است، نه استفاده برای کاری.",
            "ar": "التقطت هاتفك نحو {observed} مرة في كل ساعة استخدام فعلي. هذه حلقة تفقّد، لا استخدام لغرض.",
            "zh": "在每小时的实际使用中，你大约拿起手机 {observed} 次。这是一个反复查看的循环，而不是在用它做事。",
        },
        "action": {
            "en": "Bring it toward {target} by picking one hour a day and leaving the phone face-down in another room for all of it.",
            "fa": "با انتخاب یک ساعت در روز و گذاشتن گوشی رو‌به‌پایین در اتاقی دیگر برای تمام آن ساعت، به سمت {target} برو.",
            "ar": "اقترب من {target} باختيار ساعة واحدة يومياً تترك فيها الهاتف مقلوباً في غرفة أخرى طوال الوقت.",
            "zh": "选一个小时，把手机正面朝下放在另一个房间整整一小时，朝 {target} 靠近。",
        },
        "success_metric": {
            "en": "One protected phone-free hour on at least five days.",
            "fa": "دست‌کم پنج روز، یک ساعتِ محافظت‌شده‌ی بدون گوشی.",
            "ar": "ساعة واحدة محمية بلا هاتف في خمسة أيام على الأقل.",
            "zh": "至少五天，有一个受保护的无手机小时。",
        },
    },
    "app_opens_per_day": {
        "title": {
            "en": "Open fewer apps, more deliberately",
            "fa": "اپ‌های کمتر، آگاهانه‌تر",
            "ar": "افتح تطبيقات أقل وبقصد أوضح",
            "zh": "更少、更有意识地打开应用",
        },
        "description": {
            "en": "You opened apps {observed} times. A high count usually means opening without a reason already in mind.",
            "fa": "تو {observed} بار اپ باز کردی. عدد بالا معمولاً یعنی باز کردن بدون اینکه از قبل دلیلی در ذهن باشد.",
            "ar": "فتحت التطبيقات {observed} مرة. العدد المرتفع يعني عادةً الفتح دون سبب حاضر في ذهنك.",
            "zh": "你打开应用 {observed} 次。次数偏高通常意味着打开时心里并没有一个理由。",
        },
        "action": {
            "en": "Aim for {target} by moving your two most-opened apps off the home screen, so opening them takes a search.",
            "fa": "{target} را هدف بگیر: دو اپی را که بیشتر از همه باز می‌کنی از صفحه‌ی اصلی بردار تا باز کردنشان به جست‌وجو نیاز داشته باشد.",
            "ar": "استهدف {target} بنقل أكثر تطبيقين تفتحهما خارج الشاشة الرئيسية، حتى يتطلّب فتحهما بحثاً.",
            "zh": "把目标定在 {target}：把你最常打开的两个应用移出主屏幕，让打开它们需要先搜索。",
        },
        "success_metric": {
            "en": "At or under {target} app opens on most days this week.",
            "fa": "{target} بار یا کمتر، در بیشتر روزهای این هفته.",
            "ar": "{target} مرة أو أقل في معظم أيام هذا الأسبوع.",
            "zh": "本周大多数日子不超过 {target} 次。",
        },
    },
    "app_open_density": {
        "title": {
            "en": "Slow the app switching",
            "fa": "جابه‌جایی بین اپ‌ها را کند کن",
            "ar": "أبطئ التنقّل بين التطبيقات",
            "zh": "放慢应用切换",
        },
        "description": {
            "en": "You switched apps about {observed} times per hour of use. That fragments attention even when the total time is fine.",
            "fa": "تو حدود {observed} بار در هر ساعت استفاده بین اپ‌ها جابه‌جا شدی. این توجه را تکه‌تکه می‌کند، حتی وقتی زمان کل مشکلی ندارد.",
            "ar": "تنقّلت بين التطبيقات نحو {observed} مرة في الساعة. هذا يفتّت الانتباه حتى لو كان الوقت الإجمالي مقبولاً.",
            "zh": "你每小时大约切换应用 {observed} 次。即使总时长没问题，这也会把注意力切碎。",
        },
        "action": {
            "en": "Bring it toward {target} by finishing one thing before opening the next app — even for two minutes at a time.",
            "fa": "با تمام کردن یک کار پیش از باز کردن اپ بعدی — حتی دو دقیقه‌ای — به سمت {target} برو.",
            "ar": "اقترب من {target} بإنهاء أمر واحد قبل فتح التطبيق التالي — ولو لدقيقتين في كل مرة.",
            "zh": "朝 {target} 靠近：先做完一件事再打开下一个应用——哪怕一次只有两分钟。",
        },
        "success_metric": {
            "en": "A density at or under {target} on most days this week.",
            "fa": "چگالی {target} یا کمتر، در بیشتر روزهای این هفته.",
            "ar": "كثافة عند {target} أو أقل في معظم أيام هذا الأسبوع.",
            "zh": "本周大多数日子密度不超过 {target}。",
        },
    },
    "social_ratio": {
        "title": {
            "en": "Rebalance what your screen time is for",
            "fa": "تعادل را در کاربرد زمان صفحه‌ات برگردان",
            "ar": "أعد توازن ما يذهب إليه وقت شاشتك",
            "zh": "重新平衡你的屏幕时间用途",
        },
        "description": {
            "en": "Social apps are {observed}% of your screen time. The same minutes affect mood differently depending on where they go.",
            "fa": "اپ‌های اجتماعی {observed}٪ از زمان صفحه‌ات هستند. همان دقیقه‌ها بسته به اینکه کجا صرف شوند، اثر متفاوتی روی خلق‌وخو دارند.",
            "ar": "تشكّل تطبيقات التواصل {observed}٪ من وقت شاشتك. الدقائق نفسها تؤثر في المزاج بشكل مختلف حسب أين تذهب.",
            "zh": "社交应用占你屏幕时间的 {observed}%。同样的分钟数，花在哪里，对情绪的影响并不相同。",
        },
        "action": {
            "en": "Bring it to {target}% by swapping one social session a day for something else you already do on the phone.",
            "fa": "با جایگزین کردن یک نشست اجتماعی در روز با کار دیگری که همین حالا با گوشی می‌کنی، آن را به {target}٪ برسان.",
            "ar": "اخفضها إلى {target}٪ باستبدال جلسة تواصل واحدة يومياً بشيء آخر تفعله أصلاً على الهاتف.",
            "zh": "把它降到 {target}%：每天用你本来就在手机上做的别的事，替换一次社交时段。",
        },
        "success_metric": {
            "en": "Social apps at or under {target}% of screen time this week.",
            "fa": "اپ‌های اجتماعی {target}٪ یا کمتر از زمان صفحه در این هفته.",
            "ar": "تطبيقات التواصل عند {target}٪ أو أقل من وقت الشاشة هذا الأسبوع.",
            "zh": "本周社交应用占屏幕时间不超过 {target}%。",
        },
    },
    "work_study_ratio": {
        "title": {
            "en": "Put an edge on the working day",
            "fa": "به روز کاری‌ات یک لبه بده",
            "ar": "ضع حدّاً لنهاية يوم العمل",
            "zh": "给工作日划一条边",
        },
        "description": {
            "en": "Work and study are {observed}% of your screen time. That is not a fault — but without an end to it, recovery never starts.",
            "fa": "کار و تحصیل {observed}٪ از زمان صفحه‌ات هستند. این ایراد نیست — اما تا وقتی پایانی نداشته باشد، بازیابی هرگز شروع نمی‌شود.",
            "ar": "يشكّل العمل والدراسة {observed}٪ من وقت شاشتك. ليس هذا عيباً — لكن بلا نهاية له، لا يبدأ التعافي أبداً.",
            "zh": "工作和学习占你屏幕时间的 {observed}%。这不是缺点——但如果它没有结束的时刻，恢复就永远不会开始。",
        },
        "action": {
            "en": "Aim for {target}% by picking a time your work screen closes, and letting the rest of the evening be a different kind of screen or none.",
            "fa": "{target}٪ را هدف بگیر: ساعتی را انتخاب کن که صفحه‌ی کاری‌ات بسته می‌شود، و بگذار بقیه‌ی شب نوع دیگری از صفحه باشد یا هیچ صفحه‌ای.",
            "ar": "استهدف {target}٪ باختيار وقت تُغلق فيه شاشة العمل، ودع بقية المساء لنوع آخر من الشاشات أو لا شاشة.",
            "zh": "把目标定在 {target}%：定一个关掉工作屏幕的时间，让晚上剩下的时间属于别的屏幕，或者没有屏幕。",
        },
        "success_metric": {
            "en": "A clear stop time kept on at least four working days.",
            "fa": "یک ساعت پایان مشخص، در دست‌کم چهار روز کاری.",
            "ar": "وقت توقّف واضح يُلتزم به في أربعة أيام عمل على الأقل.",
            "zh": "至少四个工作日守住一个明确的结束时间。",
        },
    },
    "other_ratio": {
        "title": {
            "en": "Notice the unaccounted screen time",
            "fa": "زمان صفحه‌ی حساب‌نشده را ببین",
            "ar": "انتبه لوقت الشاشة غير المحسوب",
            "zh": "留意那些说不清的屏幕时间",
        },
        "description": {
            "en": "{observed}% of your screen time is not in any named category, which usually means it was unplanned.",
            "fa": "{observed}٪ از زمان صفحه‌ات در هیچ دسته‌ی مشخصی نیست، و این معمولاً یعنی بی‌برنامه بوده.",
            "ar": "{observed}٪ من وقت شاشتك خارج أي فئة مسمّاة، وهذا يعني عادةً أنه لم يكن مخططاً.",
            "zh": "你有 {observed}% 的屏幕时间不属于任何已命名的类别，这通常意味着它是计划外的。",
        },
        "action": {
            "en": "Bring it toward {target}% by noting, for two days, what those sessions actually were — naming it is most of the fix.",
            "fa": "با یادداشت کردن اینکه آن نشست‌ها واقعاً چه بودند، برای دو روز، به سمت {target}٪ برو — نام‌گذاری‌اش بیشترِ حلِ مسئله است.",
            "ar": "اقترب من {target}٪ بتدوين ما كانت عليه تلك الجلسات فعلاً على مدى يومين — التسمية وحدها معظم الحل.",
            "zh": "朝 {target}% 靠近：花两天记下这些时段究竟在做什么——说出它是什么，就解决了大半。",
        },
        "success_metric": {
            "en": "A smaller unlabelled share once you know what it is.",
            "fa": "سهم بی‌برچسبِ کمتر، وقتی فهمیدی چیست.",
            "ar": "حصة أصغر غير مصنّفة بعد أن تعرف ما هي.",
            "zh": "在你弄清它是什么之后，未标注的占比变小。",
        },
    },
    "video_min": {
        "title": {
            "en": "Make watching a choice, not a default",
            "fa": "تماشا را انتخاب کن، نه حالت پیش‌فرض",
            "ar": "اجعل المشاهدة اختياراً لا وضعاً افتراضياً",
            "zh": "让观看成为选择，而不是默认",
        },
        "description": {
            "en": "You logged {observed} minutes of video. It is the easiest kind of screen time to lose track of, because nothing in it asks you to stop.",
            "fa": "تو {observed} دقیقه ویدیو ثبت کردی. این آسان‌ترین نوع زمان صفحه برای از دست دادن حساب است، چون هیچ‌چیزی در آن از تو نمی‌خواهد بایستی.",
            "ar": "سجّلت {observed} دقيقة من الفيديو. هذا أسهل أنواع وقت الشاشة فقداناً للحساب، لأن لا شيء فيه يطلب منك التوقف.",
            "zh": "你记录了 {observed} 分钟视频。这是最容易失去时间感的一类屏幕时间，因为其中没有任何东西提醒你停下。",
        },
        "action": {
            "en": "Aim for {target} minutes by deciding what you are watching before you open the app, and stopping when it ends.",
            "fa": "{target} دقیقه را هدف بگیر: پیش از باز کردن اپ تصمیم بگیر چه چیزی تماشا می‌کنی، و وقتی تمام شد بایست.",
            "ar": "استهدف {target} دقيقة بأن تقرّر ما ستشاهده قبل فتح التطبيق، وتتوقف حين ينتهي.",
            "zh": "把目标定在 {target} 分钟：打开应用前先决定看什么，看完就停。",
        },
        "success_metric": {
            "en": "Under {target} minutes of video on most days this week.",
            "fa": "کمتر از {target} دقیقه ویدیو، در بیشتر روزهای این هفته.",
            "ar": "أقل من {target} دقيقة فيديو في معظم أيام هذا الأسبوع.",
            "zh": "本周大多数日子视频少于 {target} 分钟。",
        },
    },
    "gaming_min": {
        "title": {
            "en": "Give gaming a finish line",
            "fa": "برای بازی یک خط پایان بگذار",
            "ar": "ضع خط نهاية للّعب",
            "zh": "给游戏一条终点线",
        },
        "description": {
            "en": "You logged {observed} minutes of gaming. Gaming is fine as a choice and costly as a default — the difference is whether it has an end.",
            "fa": "تو {observed} دقیقه بازی ثبت کردی. بازی به‌عنوان انتخاب اشکالی ندارد و به‌عنوان پیش‌فرض پرهزینه است — تفاوتش این است که پایانی داشته باشد یا نه.",
            "ar": "سجّلت {observed} دقيقة من اللعب. اللعب بوصفه اختياراً لا بأس به، وبوصفه وضعاً افتراضياً مكلف — والفارق أن تكون له نهاية.",
            "zh": "你记录了 {observed} 分钟游戏。作为选择，游戏没问题；作为默认，它代价不小——区别在于它有没有终点。",
        },
        "action": {
            "en": "Aim for {target} minutes by setting the stopping point before you start: one match, one session, one hour.",
            "fa": "{target} دقیقه را هدف بگیر: پیش از شروع نقطه‌ی توقف را تعیین کن — یک مسابقه، یک نشست، یک ساعت.",
            "ar": "استهدف {target} دقيقة بتحديد نقطة التوقف قبل أن تبدأ: مباراة واحدة، جلسة واحدة، ساعة واحدة.",
            "zh": "把目标定在 {target} 分钟：开始前先定好停下的点——一局、一场、一小时。",
        },
        "success_metric": {
            "en": "Under {target} minutes of gaming on most days this week.",
            "fa": "کمتر از {target} دقیقه بازی، در بیشتر روزهای این هفته.",
            "ar": "أقل من {target} دقيقة لعب في معظم أيام هذا الأسبوع.",
            "zh": "本周大多数日子游戏少于 {target} 分钟。",
        },
    },
    "pre_sleep_ratio": {
        "title": {
            "en": "Shift screen time away from bedtime",
            "fa": "زمان صفحه را از ساعت خواب دور کن",
            "ar": "انقل وقت الشاشة بعيداً عن موعد النوم",
            "zh": "把屏幕时间从睡前挪开",
        },
        "description": {
            "en": "{observed}% of your screen time lands right before sleep. That is the costliest hour for it.",
            "fa": "{observed}٪ از زمان صفحه‌ات درست پیش از خواب می‌افتد. این پرهزینه‌ترین ساعت برای آن است.",
            "ar": "{observed}٪ من وقت شاشتك يقع مباشرة قبل النوم. تلك أغلى ساعة له.",
            "zh": "你有 {observed}% 的屏幕时间正好落在睡前。那是代价最高的一小时。",
        },
        "action": {
            "en": "Bring it to {target}% by moving one pre-sleep habit to before dinner — the same minutes, several hours earlier.",
            "fa": "با جابه‌جا کردن یک عادت پیش از خواب به قبل از شام، آن را به {target}٪ برسان — همان دقیقه‌ها، چند ساعت زودتر.",
            "ar": "اخفضها إلى {target}٪ بنقل عادة واحدة قبل النوم إلى ما قبل العشاء — الدقائق نفسها، قبلها بساعات.",
            "zh": "把它降到 {target}%：把一个睡前习惯挪到晚饭前——同样的分钟，只是提前几小时。",
        },
        "success_metric": {
            "en": "At or under {target}% before sleep on most nights this week.",
            "fa": "{target}٪ یا کمتر پیش از خواب، در بیشتر شب‌های این هفته.",
            "ar": "عند {target}٪ أو أقل قبل النوم في معظم ليالي هذا الأسبوع.",
            "zh": "本周大多数晚上，睡前不超过 {target}%。",
        },
    },
    "mental_fatigue_0_10": {
        "title": {
            "en": "Build in real breaks",
            "fa": "استراحت‌های واقعی بگذار",
            "ar": "أدرج استراحات حقيقية",
            "zh": "安排真正的休息",
        },
        "description": {
            "en": "You rated mental fatigue at {observed}. That is the signal that recovery is not keeping up with load — not that you need to push harder.",
            "fa": "خستگی ذهنی‌ات را {observed} ثبت کردی. این نشانه‌ی آن است که بازیابی به پای بار نمی‌رسد — نه اینکه باید بیشتر فشار بیاوری.",
            "ar": "قيّمت الإرهاق الذهني بـ {observed}. هذه إشارة إلى أن التعافي لا يواكب الحِمل — لا إلى أنك تحتاج دفعاً أقوى.",
            "zh": "你把精神疲劳评为 {observed}。这是恢复跟不上负荷的信号——不是你需要更用力。",
        },
        "action": {
            "en": "Aim for {target} by taking one break away from all screens, outdoors if you can, in the middle of your longest working stretch.",
            "fa": "{target} را هدف بگیر: در میانه‌ی طولانی‌ترین بازه‌ی کاری‌ات یک استراحت دور از همه‌ی صفحه‌ها بگیر، اگر می‌شود بیرون از خانه.",
            "ar": "استهدف {target} بأخذ استراحة واحدة بعيداً عن كل الشاشات، في الهواء الطلق إن أمكن، في منتصف أطول فترة عمل لديك.",
            "zh": "把目标定在 {target}：在你最长的一段工作时间中间，离开所有屏幕休息一次，可以的话到户外。",
        },
        "success_metric": {
            "en": "One genuine screen-free break on at least five days.",
            "fa": "دست‌کم پنج روز، یک استراحت واقعیِ بدون صفحه.",
            "ar": "استراحة حقيقية بلا شاشات في خمسة أيام على الأقل.",
            "zh": "至少五天有一次真正无屏幕的休息。",
        },
    },
    "focus_0_100": {
        "title": {
            "en": "Protect one block of focus",
            "fa": "یک بلوک تمرکز را حفظ کن",
            "ar": "احمِ فترة تركيز واحدة",
            "zh": "守住一段专注时间",
        },
        "description": {
            "en": "Your focus score is {observed}. That is low enough to be costing you time, not just to feel frustrating.",
            "fa": "امتیاز تمرکزت {observed} است. این آن‌قدر پایین هست که واقعاً وقتت را بگیرد، نه فقط آزاردهنده باشد.",
            "ar": "درجة تركيزك {observed}. هذه منخفضة بما يكفي لتكلّفك وقتاً فعلياً، لا لتكون مزعجة فحسب.",
            "zh": "你的专注分是 {observed}。这已经低到在实实在在耗掉你的时间，而不只是让人心烦。",
        },
        "action": {
            "en": "Aim for {target} by protecting one 25-minute block with notifications off and one task open.",
            "fa": "{target} را هدف بگیر: یک بلوک ۲۵ دقیقه‌ای را با اعلان‌های خاموش و فقط یک کارِ باز حفظ کن.",
            "ar": "استهدف {target} بحماية فترة واحدة من 25 دقيقة، بإشعارات مغلقة ومهمة واحدة مفتوحة.",
            "zh": "把目标定在 {target}：守住一个 25 分钟的时段，关掉通知，只开一项任务。",
        },
        "success_metric": {
            "en": "One protected focus block on at least five days.",
            "fa": "دست‌کم پنج روز، یک بلوک تمرکزِ محافظت‌شده.",
            "ar": "فترة تركيز محمية واحدة في خمسة أيام على الأقل.",
            "zh": "至少五天有一个受保护的专注时段。",
        },
    },
    "digital_dependence_0_100": {
        "title": {
            "en": "Loosen the pull a little",
            "fa": "کمی از کِشش کم کن",
            "ar": "خفّف الشدّ قليلاً",
            "zh": "让那股拉力松一点",
        },
        "description": {
            "en": "Your digital dependence score is {observed}. It measures how strongly the phone pulls at you, not how much you use it — and it responds to friction, not willpower.",
            "fa": "امتیاز وابستگی دیجیتالت {observed} است. این می‌سنجد گوشی چقدر تو را می‌کِشد، نه اینکه چقدر از آن استفاده می‌کنی — و به اصطکاک پاسخ می‌دهد، نه به اراده.",
            "ar": "درجة اعتمادك الرقمي {observed}. تقيس مدى شدّ الهاتف لك، لا مقدار استخدامك له — وتستجيب للاحتكاك لا لقوة الإرادة.",
            "zh": "你的数字依赖分是 {observed}。它衡量的是手机对你的拉力有多强，而不是你用了多少——它回应的是阻力，不是意志力。",
        },
        "action": {
            "en": "Aim for {target} by adding one deliberate obstacle: greyscale, a login screen, or the phone in a drawer during meals.",
            "fa": "{target} را هدف بگیر: یک مانع عمدی اضافه کن — حالت خاکستری، صفحه‌ی ورود، یا گوشی در کشو هنگام غذا.",
            "ar": "استهدف {target} بإضافة عائق واحد متعمَّد: تدرّج رمادي، شاشة تسجيل دخول، أو الهاتف في درج أثناء الوجبات.",
            "zh": "把目标定在 {target}：加一个刻意的阻碍——灰度模式、一道登录界面，或吃饭时把手机放进抽屉。",
        },
        "success_metric": {
            "en": "One friction change kept in place for the whole week.",
            "fa": "یک تغییرِ اصطکاکی که تمام هفته سر جایش بماند.",
            "ar": "تغيير احتكاك واحد يبقى قائماً طوال الأسبوع.",
            "zh": "一项阻力改动，整周都保持不变。",
        },
    },
    "caffeine_cups_per_day": {
        "title": {
            "en": "Move caffeine earlier",
            "fa": "کافئین را جلوتر بیاور",
            "ar": "قدّم موعد الكافيين",
            "zh": "把咖啡因提前",
        },
        "description": {
            "en": "You logged {observed} cups. Caffeine has a long tail — the cup that feels harmless at 4pm is often still working at bedtime.",
            "fa": "تو {observed} فنجان ثبت کردی. کافئین دنباله‌ی بلندی دارد — فنجانی که ساعت ۴ بعدازظهر بی‌ضرر به نظر می‌رسد، اغلب موقع خواب هنوز کار می‌کند.",
            "ar": "سجّلت {observed} أكواب. للكافيين ذيل طويل — الكوب الذي يبدو غير ضار في الرابعة عصراً كثيراً ما يظل فاعلاً وقت النوم.",
            "zh": "你记录了 {observed} 杯。咖啡因的尾巴很长——下午四点看似无害的那一杯，往往到睡觉时还在起作用。",
        },
        "action": {
            "en": "Keep the same number if you like, but make the last one before 2pm — or bring it toward {target} cups.",
            "fa": "اگر دوست داری همان تعداد را نگه دار، ولی آخری را قبل از ۲ بعدازظهر بنوش — یا به سمت {target} فنجان برو.",
            "ar": "أبقِ العدد نفسه إن شئت، لكن اجعل الأخير قبل الثانية ظهراً — أو اقترب من {target} أكواب.",
            "zh": "杯数不变也行，但把最后一杯放在下午两点前——或者朝 {target} 杯靠近。",
        },
        "success_metric": {
            "en": "No caffeine after 2pm on at least five days.",
            "fa": "دست‌کم پنج روز، بدون کافئین بعد از ۲ بعدازظهر.",
            "ar": "لا كافيين بعد الثانية ظهراً في خمسة أيام على الأقل.",
            "zh": "至少五天下午两点后不摄入咖啡因。",
        },
    },
    "fomo_1_10": {
        "title": {
            "en": "Test what you actually miss",
            "fa": "امتحان کن واقعاً چه چیزی را از دست می‌دهی",
            "ar": "اختبر ما تفوّته فعلاً",
            "zh": "测试你到底错过了什么",
        },
        "description": {
            "en": "You rated fear of missing out at {observed}. That feeling is usually much larger than what is genuinely missed.",
            "fa": "ترس از جا ماندن را {observed} ثبت کردی. این حس معمولاً خیلی بزرگ‌تر از چیزی است که واقعاً از دست می‌رود.",
            "ar": "قيّمت الخوف من التفويت بـ {observed}. هذا الشعور عادةً أكبر بكثير مما يُفوَّت فعلاً.",
            "zh": "你把错失恐惧评为 {observed}。这种感觉通常远大于真正错过的东西。",
        },
        "action": {
            "en": "Aim for {target} by leaving one app closed for a full evening, then checking whether anything needed you.",
            "fa": "{target} را هدف بگیر: یک اپ را یک شبِ کامل بسته نگه دار، بعد ببین آیا چیزی به تو نیاز داشت.",
            "ar": "استهدف {target} بترك تطبيق واحد مغلقاً مساءً كاملاً، ثم تحقّق إن كان أي شيء يحتاجك.",
            "zh": "把目标定在 {target}：让一个应用整晚都不打开，然后看看有没有什么真的需要你。",
        },
        "success_metric": {
            "en": "One evening away from the app, and an honest look at what changed.",
            "fa": "یک شب دور از آن اپ، و یک نگاه صادقانه به اینکه چه تغییر کرد.",
            "ar": "مساء واحد بعيداً عن التطبيق، ونظرة صادقة إلى ما تغيّر.",
            "zh": "一个晚上离开那个应用，然后诚实地看看有什么变化。",
        },
    },
    "social_comparison_1_10": {
        "title": {
            "en": "Change what your feed shows you",
            "fa": "چیزی را که فیدت نشانت می‌دهد عوض کن",
            "ar": "غيّر ما يعرضه لك موجزك",
            "zh": "改变你的信息流给你看什么",
        },
        "description": {
            "en": "You rated social comparison at {observed}. It is driven far more by which accounts you see than by how long you look.",
            "fa": "مقایسه‌ی اجتماعی را {observed} ثبت کردی. این خیلی بیشتر از مدت نگاه‌کردن، از این می‌آید که چه حساب‌هایی را می‌بینی.",
            "ar": "قيّمت المقارنة الاجتماعية بـ {observed}. تحرّكها الحسابات التي تراها أكثر بكثير من مدة نظرك.",
            "zh": "你把社会比较评为 {observed}。它更多取决于你看到哪些账号，而不是你看了多久。",
        },
        "action": {
            "en": "Aim for {target} by muting or unfollowing three accounts that consistently leave you feeling worse.",
            "fa": "{target} را هدف بگیر: سه حسابی را که همیشه حالت را بدتر می‌کنند بی‌صدا کن یا دنبال نکن.",
            "ar": "استهدف {target} بكتم أو إلغاء متابعة ثلاثة حسابات تتركك دائماً في حال أسوأ.",
            "zh": "把目标定在 {target}：静音或取消关注三个总让你感觉更糟的账号。",
        },
        "success_metric": {
            "en": "Three accounts muted, and a week to notice the difference.",
            "fa": "سه حساب بی‌صدا شده، و یک هفته برای دیدن تفاوت.",
            "ar": "ثلاثة حسابات مكتومة، وأسبوع لملاحظة الفرق.",
            "zh": "静音三个账号，用一周来感受差别。",
        },
    },
}


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(value, 1))


def localized_text(field: str, numbers: dict[str, Optional[float]]) -> dict[str, dict[str, str]]:
    """{field_name: {lang: filled string}} for one rule.

    A rule with no entry returns {} and the caller keeps the registry's
    original English, so an un-translated new rule degrades to the old
    behaviour rather than to a blank card.
    """
    entry = RULE_TEXT.get(field)
    if not entry:
        return {}

    replacements = {
        "{observed}": _format_number(numbers["observed"]) if numbers.get("observed") is not None else "",
        "{target}": _format_number(numbers["target"]) if numbers.get("target") is not None else "",
    }

    out: dict[str, dict[str, str]] = {}
    for part, table in entry.items():
        out[part] = {}
        for lang in LANGUAGES:
            text = table.get(lang) or table["en"]
            for token, value in replacements.items():
                text = text.replace(token, value)
            out[part][lang] = text
    return out


# --------------------------------------------------------------------
# Priority label and safety note, both closed, small vocabularies -
# unlike RULE_TEXT above (one entry per rule), these apply across every
# recommendation regardless of which rule produced it, so one small
# table each is enough.
# --------------------------------------------------------------------

PRIORITY_I18N: dict[str, dict[str, str]] = {
    "high": {"en": "High", "fa": "بالا", "ar": "عالية", "zh": "高"},
    "medium": {"en": "Medium", "fa": "متوسط", "ar": "متوسطة", "zh": "中"},
    "low": {"en": "Low", "fa": "پایین", "ar": "منخفضة", "zh": "低"},
}


def priority_i18n(priority: str) -> dict[str, str]:
    """{lang: label} for a priority string, case-insensitively.

    Falls back to the raw value in every language rather than raising,
    matching localized_text()'s "degrade gracefully" contract - an
    unrecognised priority should not blank a whole recommendation card.
    """
    table = PRIORITY_I18N.get((priority or "").lower())
    if table:
        return dict(table)
    return {lang: priority for lang in LANGUAGES}


# The three safety notes actually used in config/recommendation_registry.py
# (RecommendationTemplate.safety_note), keyed by the English string so
# the registry itself never has to change. Checked against the registry
# in tests/wellness/test_recommendation_i18n.py - a fourth note added there
# without an entry here would ship English-only rather than fail loudly,
# so that test exists specifically to catch the gap instead.
SAFETY_NOTE_I18N: dict[str, dict[str, str]] = {
    "This is general guidance, not a mental-health diagnosis or treatment. If stress feels overwhelming or unmanageable, please talk to a healthcare professional or a crisis line in your area.": {
        "en": "This is general guidance, not a mental-health diagnosis or treatment. If stress feels overwhelming or unmanageable, please talk to a healthcare professional or a crisis line in your area.",
        "fa": "این یک راهنمایی کلی است، نه تشخیص یا درمان سلامت روان. اگر استرس طاقت‌فرسا یا غیرقابل‌کنترل به نظر می‌رسد، لطفاً با یک متخصص سلامت یا خط بحران در منطقه‌ات صحبت کن.",
        "ar": "هذا إرشاد عام، وليس تشخيصاً أو علاجاً نفسياً. إذا شعرت أن التوتر ساحق أو يصعب التحكم به، يُرجى التحدث إلى مختص رعاية صحية أو خط أزمات في منطقتك.",
        "zh": "这只是一般性建议，不是心理健康诊断或治疗。如果压力让你感到难以承受或无法控制，请联系你所在地区的医疗专业人士或危机热线。",
    },
    "Build up activity gradually and within your own physical limits. Consult a doctor before starting a new exercise routine if you have a medical condition.": {
        "en": "Build up activity gradually and within your own physical limits. Consult a doctor before starting a new exercise routine if you have a medical condition.",
        "fa": "فعالیت را کم‌کم و در محدوده‌ی توان بدنی خودت افزایش بده. اگر شرایط پزشکی خاصی داری، پیش از شروع یک برنامه‌ی ورزشی جدید با پزشک مشورت کن.",
        "ar": "زِد نشاطك تدريجياً وضمن حدودك الجسدية. استشر طبيباً قبل بدء أي برنامج تمارين جديد إذا كانت لديك حالة طبية.",
        "zh": "循序渐进地增加活动量，并保持在自己的身体承受范围内。如果你有基础病，开始新的运动计划前请先咨询医生。",
    },
    "This is general digital-wellness guidance, not medical advice. If sleep, mood, or anxiety concerns persist, consider talking to a healthcare professional.": {
        "en": "This is general digital-wellness guidance, not medical advice. If sleep, mood, or anxiety concerns persist, consider talking to a healthcare professional.",
        "fa": "این یک راهنمایی کلی درباره‌ی سلامت دیجیتال است، نه توصیه‌ی پزشکی. اگر نگرانی درباره‌ی خواب، خلق‌وخو یا اضطراب ادامه پیدا کرد، صحبت با یک متخصص سلامت را در نظر بگیر.",
        "ar": "هذا إرشاد عام حول العافية الرقمية، وليس نصيحة طبية. إذا استمرت مخاوف تتعلق بالنوم أو المزاج أو القلق، ففكّر في التحدث إلى مختص رعاية صحية.",
        "zh": "这只是一般性的数字健康建议，不是医疗建议。如果睡眠、情绪或焦虑方面的担忧持续存在，请考虑咨询医疗专业人士。",
    },
}


def safety_note_i18n(note: str) -> dict[str, str]:
    """{lang: text} for a safety note, falling back to the raw string in
    every language if it doesn't match one of the three known notes -
    same degrade-gracefully contract as priority_i18n()."""
    table = SAFETY_NOTE_I18N.get(note or "")
    if table:
        return dict(table)
    return {lang: (note or "") for lang in LANGUAGES}
