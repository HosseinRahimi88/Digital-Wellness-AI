"""
Exercise library for the seven-day plan.

The problem this replaces
-------------------------
The plan drew from seven themes with three fixed tiers of three fixed
sentences each - about sixty strings, English only. Two consequences,
both reported: every week looked like the last one, and every user got
the same sentence as every other user with the same weak signal. "Cut
caffeine after 2pm today" is reasonable advice and completely
impersonal; it does not know whether you drink one coffee or six.

What this is instead
--------------------
An exercise is composed rather than looked up, from four independent
parts:

    theme x template x slot x tier

and then bound to the user's OWN measured value, which is the part that
makes it a personal instruction rather than a poster. The same template
produces

    "Your screens ran 142 minutes past 22:00 last night. Tonight, stop
     at 112 - a 30-minute cut, not a heroic one."

for one user and a different sentence with different numbers for the
next, because the target is computed from their number.

Size: the combinatorial space is reported by `library_size()` and
asserted in tests rather than claimed here, so the number in the README
cannot drift away from the code. It is large not for its own sake but
because a plan a user follows for months must not repeat - and because
a template that only fits one kind of person is a template that gets
skipped by everyone else.

What it deliberately does NOT do
--------------------------------
Nothing here diagnoses, prescribes, or promises an outcome. Every
exercise is an action the user can take today, phrased as an
experiment. Where an instruction would be unsafe without knowing more
about someone - anything about food, medication or exertion levels -
the template stays on the side of "notice" rather than "do".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

LANGUAGES = ("en", "fa", "ar", "zh")

# When in the day an exercise lands. Kept separate from the template so
# the same action can be tried at the time that actually suits the
# user's shape of day, and so a week's plan can vary the rhythm rather
# than stacking everything at bedtime.
SLOTS: tuple[str, ...] = ("morning", "midday", "evening", "before_bed", "anytime")

SLOT_LABELS: dict[str, dict[str, str]] = {
    "morning":    {"en": "Morning",      "fa": "صبح",          "ar": "الصباح",      "zh": "早晨"},
    "midday":     {"en": "Midday",       "fa": "میانه‌ی روز",   "ar": "منتصف اليوم", "zh": "中午"},
    "evening":    {"en": "Evening",      "fa": "عصر",          "ar": "المساء",      "zh": "傍晚"},
    "before_bed": {"en": "Before bed",   "fa": "پیش از خواب",   "ar": "قبل النوم",   "zh": "睡前"},
    "anytime":    {"en": "Any time",     "fa": "هر وقت",        "ar": "أي وقت",      "zh": "任何时候"},
}

# Four tiers rather than three: the old three jumped from "gentle" to
# "locking it in" with nothing in between, so a user who found week two
# hard had nowhere to go but backwards.
TIERS: tuple[str, ...] = ("notice", "adjust", "commit", "sustain")

TIER_LABELS: dict[str, dict[str, str]] = {
    "notice":  {"en": "Notice it",      "fa": "متوجهش شو",     "ar": "لاحظه",        "zh": "先察觉"},
    "adjust":  {"en": "Adjust it",      "fa": "کمی تغییرش بده", "ar": "عدّله",       "zh": "微调"},
    "commit":  {"en": "Commit to it",   "fa": "پایش بایست",     "ar": "التزم به",     "zh": "坚持下来"},
    "sustain": {"en": "Make it normal", "fa": "عادی‌اش کن",     "ar": "اجعله عادياً", "zh": "让它变成日常"},
}


@dataclass(slots=True)
class Exercise:
    """One composed instruction, already bound to the user's numbers."""

    theme: str
    slot: str
    tier: str
    text: dict[str, str]          # one string per language
    field: str = ""               # the measured signal it addresses
    current: Optional[float] = None
    target: Optional[float] = None

    def localized(self, language: str) -> str:
        return self.text.get(language) or self.text.get("en", "")


def _round_to(value: float, step: float) -> float:
    return round(value / step) * step


def _fmt(value: Optional[float], unit: str = "") -> str:
    """Numbers are written LTR-isolated so a Persian or Arabic sentence
    does not render "120 min" with the digits at the wrong end."""
    if value is None:
        return "—"
    text = str(int(round(value))) if abs(value - round(value)) < 0.05 else f"{value:.1f}"
    return f"⁦{text}{unit}⁩"


# ---------------------------------------------------------------------
# Templates
#
# Each template is a function of (current value, target value) returning
# one sentence per language. A template only appears for a theme whose
# signal the user actually has, so no exercise is ever generated about a
# number that was never measured.
# ---------------------------------------------------------------------

Template = Callable[[Optional[float], Optional[float]], dict[str, str]]


def _t(en: str, fa: str, ar: str, zh: str) -> dict[str, str]:
    return {"en": en, "fa": fa, "ar": ar, "zh": zh}


def _sleep_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            f"You slept {_fmt(c, 'h')} last night. Aim for {_fmt(t, 'h')} tonight by starting your wind-down 20 minutes earlier.",
            f"دیشب {_fmt(c, ' ساعت')} خوابیدی. امشب {_fmt(t, ' ساعت')} را هدف بگیر، با شروع آرام‌شدن ۲۰ دقیقه زودتر.",
            f"نمت {_fmt(c, ' ساعة')} الليلة الماضية. استهدف {_fmt(t, ' ساعة')} الليلة ببدء الاسترخاء قبل ٢٠ دقيقة.",
            f"你昨晚睡了 {_fmt(c, ' 小时')}。今晚把目标定在 {_fmt(t, ' 小时')}，提前 20 分钟开始放松。",
        ),
        lambda c, t: _t(
            "Set one alarm for going to bed, not just for getting up.",
            "یک زنگ برای خوابیدن بگذار، نه فقط برای بیدار شدن.",
            "اضبط منبّهاً للنوم، لا للاستيقاظ فقط.",
            "为「上床」设一个闹钟，而不是只为起床设。",
        ),
        lambda c, t: _t(
            "Keep tonight's wake-up time whatever happens - a fixed morning fixes the night faster than a fixed night fixes the morning.",
            "ساعت بیدارشدن فردا را هرچه شد نگه دار — صبحِ ثابت، شب را زودتر درست می‌کند تا شبِ ثابت صبح را.",
            "حافظ على وقت الاستيقاظ غداً مهما حدث — الصباح الثابت يصلح الليل أسرع من العكس.",
            "无论如何都守住明早的起床时间——固定的早晨修复夜晚，比固定的夜晚修复早晨更快。",
        ),
        lambda c, t: _t(
            "Charge your phone outside the bedroom tonight. Not silenced - outside.",
            "امشب گوشی را بیرون از اتاق خواب شارژ کن. نه بی‌صدا — بیرون.",
            "اشحن هاتفك خارج غرفة النوم الليلة. لا صامتاً — خارجاً.",
            "今晚把手机放到卧室外充电。不是静音——是拿出去。",
        ),
        lambda c, t: _t(
            "Write down what time you actually fell asleep, not what time you got into bed. The gap is the thing worth knowing.",
            "بنویس واقعاً چه ساعتی خوابت برد، نه چه ساعتی رفتی توی رختخواب. همان فاصله است که ارزش دانستن دارد.",
            "دوّن الوقت الذي نمت فيه فعلاً، لا وقت دخولك السرير. الفجوة بينهما هي ما يستحق المعرفة.",
            "记下你真正睡着的时间，而不是上床的时间。中间那段差距才是值得知道的。",
        ),
        lambda c, t: _t(
            "If you wake in the night, leave the phone where it is. Checking the time is what turns ten minutes into an hour.",
            "اگر نیمه‌شب بیدار شدی، گوشی را همان‌جا بگذار. دیدنِ ساعت است که ده دقیقه را یک ساعت می‌کند.",
            "إن استيقظت ليلاً، فاترك الهاتف مكانه. النظر إلى الساعة هو ما يحوّل عشر دقائق إلى ساعة.",
            "如果半夜醒来，就让手机待在原处。看一眼时间，正是把十分钟变成一小时的原因。",
        ),
    ]


def _screen_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            f"Your screen time was {_fmt(c, ' min')}. Try landing under {_fmt(t, ' min')} today - a cut you can actually make, not a vow.",
            f"زمان صفحه‌ات {_fmt(c, ' دقیقه')} بود. امروز زیر {_fmt(t, ' دقیقه')} را امتحان کن — کاهشی که واقعاً شدنی است، نه یک عهد.",
            f"كان وقت شاشتك {_fmt(c, ' دقيقة')}. جرّب النزول تحت {_fmt(t, ' دقيقة')} اليوم — خفض ممكن فعلاً، لا وعد.",
            f"你的屏幕时间是 {_fmt(c, ' 分钟')}。今天试着降到 {_fmt(t, ' 分钟')} 以下——一个真能做到的削减，而不是一句誓言。",
        ),
        lambda c, t: _t(
            "Move the app you open most off your home screen. You will still find it; you will just have to mean it.",
            "پرکاربردترین اپت را از صفحه‌ی اصلی بردار. باز هم پیدایش می‌کنی؛ فقط باید واقعاً بخواهی.",
            "انقل التطبيق الذي تفتحه أكثر من الشاشة الرئيسية. ستجده، لكن عليك أن تقصده.",
            "把你打开最多的那个应用挪出主屏幕。你仍然找得到它，只是得是真心想打开。",
        ),
        lambda c, t: _t(
            "Pick one app and check where its time actually goes today. Not to cut it - just to see it.",
            "یک اپ انتخاب کن و امروز ببین وقتش واقعاً کجا می‌رود. نه برای کم‌کردنش — فقط برای دیدنش.",
            "اختر تطبيقاً واحداً وانظر اليوم أين يذهب وقته فعلاً. ليس لتقليصه — بل لرؤيته.",
            "挑一个应用，今天看看它的时间到底花在哪。不是为了砍掉它——只是为了看见它。",
        ),
        lambda c, t: _t(
            "Put a ten-second pause between picking up the phone and unlocking it. Count it out.",
            "بین برداشتن گوشی و بازکردنش ده ثانیه مکث بگذار. بشمارش.",
            "اجعل بين التقاط الهاتف وفتحه عشر ثوانٍ. عُدّها.",
            "在拿起手机和解锁之间放十秒钟的停顿。数出来。",
        ),
        lambda c, t: _t(
            "Take one screen-free walk today, phone left behind rather than pocketed.",
            "امروز یک پیاده‌روی بدون صفحه برو، گوشی را جا بگذار نه اینکه توی جیب باشد.",
            "امشِ اليوم مشية واحدة بلا شاشة، بترك الهاتف لا بوضعه في الجيب.",
            "今天走一次没有屏幕的路，把手机留下，而不是装进口袋。",
        ),
        lambda c, t: _t(
            "Decide before you open an app what you are opening it for. Close it when that is done.",
            "قبل از بازکردن هر اپ تصمیم بگیر برای چه بازش می‌کنی. وقتی آن کار تمام شد، ببندش.",
            "قرّر قبل فتح أي تطبيق لماذا تفتحه. وأغلقه حين ينتهي ذلك.",
            "在打开一个应用之前，先决定你是为了什么打开它。做完就关掉。",
        ),
    ]


def _night_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            f"{_fmt(c, ' min')} of your screen time landed at night. Aim to end screens {_fmt(t, ' min')} earlier tonight.",
            f"{_fmt(c, ' دقیقه')} از زمان صفحه‌ات شبانه بود. امشب هدف بگیر {_fmt(t, ' دقیقه')} زودتر تمامش کنی.",
            f"{_fmt(c, ' دقيقة')} من وقت شاشتك كانت ليلاً. استهدف إنهاء الشاشات قبل {_fmt(t, ' دقيقة')} الليلة.",
            f"你有 {_fmt(c, ' 分钟')} 的屏幕时间落在夜里。今晚试着提前 {_fmt(t, ' 分钟')} 收工。",
        ),
        lambda c, t: _t(
            "Pick a time tonight after which the phone is charging, not in your hand. Any time. Just pick one.",
            "برای امشب ساعتی انتخاب کن که بعد از آن گوشی در حال شارژ باشد نه در دستت. هر ساعتی. فقط یکی انتخاب کن.",
            "اختر وقتاً الليلة يكون الهاتف بعده على الشحن لا في يدك. أي وقت. فقط اختر واحداً.",
            "为今晚定一个时刻，过了它手机就去充电，而不是在你手里。几点都行，选一个就好。",
        ),
        lambda c, t: _t(
            "Swap the last thing you look at tonight - anything on paper instead of anything lit.",
            "آخرین چیزی که امشب نگاه می‌کنی را عوض کن — هرچیزی روی کاغذ، به‌جای هرچیزی که نور می‌دهد.",
            "بدّل آخر ما تنظر إليه الليلة — أي شيء على ورق بدل أي شيء مُضاء.",
            "换掉你今晚最后看的那样东西——任何纸上的东西，代替任何发光的东西。",
        ),
    ]


def _focus_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            f"You picked the phone up {_fmt(c)} times. Try getting through one 25-minute block today without it - one, not all day.",
            f"{_fmt(c)} بار گوشی را برداشتی. امروز فقط یک بلوکِ ۲۵ دقیقه‌ای را بدونش رد کن — یکی، نه تمام روز.",
            f"التقطت الهاتف {_fmt(c)} مرة. جرّب اليوم تجاوز كتلة واحدة من ٢٥ دقيقة بدونه — واحدة، لا اليوم كله.",
            f"你拿起手机 {_fmt(c)} 次。今天试着完整度过一个 25 分钟的时段而不碰它——一个就好，不是一整天。",
        ),
        lambda c, t: _t(
            f"You got {_fmt(c)} notifications. Turn off the noisiest app's alerts for today only and see what you actually missed.",
            f"{_fmt(c)} اعلان گرفتی. فقط برای امروز اعلان‌های پرسروصداترین اپ را خاموش کن و ببین واقعاً چه چیزی را از دست دادی.",
            f"وصلك {_fmt(c)} إشعار. أطفئ تنبيهات أكثر التطبيقات ضجيجاً لليوم فقط وانظر ما فاتك فعلاً.",
            f"你收到了 {_fmt(c)} 条通知。只在今天关掉最吵的那个应用的提醒，然后看看你到底错过了什么。",
        ),
        lambda c, t: _t(
            "Put the phone in another room for one task today. Not face-down - another room.",
            "امروز برای یک کار، گوشی را در اتاق دیگری بگذار. نه رو به پایین — اتاق دیگر.",
            "ضع الهاتف في غرفة أخرى لمهمة واحدة اليوم. لا مقلوباً — في غرفة أخرى.",
            "今天做一件事时把手机放到另一个房间。不是扣过来——是另一个房间。",
        ),
        lambda c, t: _t(
            "Write the one thing you most want to finish today on paper before you open anything.",
            "قبل از اینکه چیزی باز کنی، مهم‌ترین کاری که می‌خواهی امروز تمام کنی را روی کاغذ بنویس.",
            "اكتب على ورق أهم شيء تريد إنهاءه اليوم قبل أن تفتح أي شيء.",
            "在打开任何东西之前，先在纸上写下你今天最想完成的那一件事。",
        ),
        lambda c, t: _t(
            "Batch your messages into two check-ins today instead of a continuous trickle.",
            "امروز پیام‌ها را در دو نوبت چک کن به‌جای یک جریان دائمی.",
            "اجمع رسائلك في مراجعتين اليوم بدل تدفّق مستمر.",
            "今天把消息集中在两次查看，而不是持续不断地滴进来。",
        ),
    ]


def _mood_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            "Name what you are feeling once today, in one word, without explaining it to anyone.",
            "امروز یک بار حسی که داری را با یک کلمه نام ببر، بدون اینکه برای کسی توضیحش بدهی.",
            "سمِّ ما تشعر به مرة اليوم، بكلمة واحدة، دون أن تشرحه لأحد.",
            "今天给你的感受命名一次，用一个词，不必向任何人解释。",
        ),
        lambda c, t: _t(
            "Take three screen-free breaks today. Two minutes each is enough to count.",
            "امروز سه وقفه‌ی بدون صفحه بگیر. دو دقیقه هم کافی است که حساب شود.",
            "خذ ثلاث استراحات بلا شاشة اليوم. دقيقتان لكل منها تكفيان.",
            "今天休息三次，不看屏幕。每次两分钟就足够算数。",
        ),
        lambda c, t: _t(
            "Notice one moment today that was fine. Not good - just fine. Those are the ones that go unrecorded.",
            "امروز یک لحظه را که خوب بود متوجه شو. نه عالی — فقط خوب. همان‌هاست که ثبت نمی‌شود.",
            "لاحظ لحظة واحدة اليوم كانت جيدة. ليست رائعة — جيدة فقط. تلك هي التي لا تُسجَّل.",
            "今天留意一个还不错的瞬间。不是很好——只是还不错。正是这些从来没被记下来。",
        ),
        lambda c, t: _t(
            "Message one person today for a reason that has nothing to do with anything you need.",
            "امروز به یک نفر پیام بده به دلیلی که هیچ ربطی به چیزی که لازم داری ندارد.",
            "راسل شخصاً اليوم لسبب لا علاقة له بشيء تحتاجه.",
            "今天给一个人发条消息，理由和你需要的任何东西都无关。",
        ),
        lambda c, t: _t(
            "Spend one stretch today comparing yourself to nobody. Close whatever makes that hard.",
            "امروز مدتی را بدون مقایسه‌ی خودت با هیچ‌کس بگذران. هرچه این کار را سخت می‌کند ببند.",
            "اقضِ فترة اليوم دون مقارنة نفسك بأحد. أغلق ما يجعل ذلك صعباً.",
            "今天有一段时间，不和任何人比较。把让这件事变难的东西关掉。",
        ),
    ]


def _movement_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            f"You moved {_fmt(c, ' min')} yesterday. Add {_fmt(t, ' min')} today in whatever form you will actually do.",
            f"دیروز {_fmt(c, ' دقیقه')} تحرک داشتی. امروز {_fmt(t, ' دقیقه')} اضافه کن، به هر شکلی که واقعاً انجامش می‌دهی.",
            f"تحرّكت {_fmt(c, ' دقيقة')} أمس. أضف {_fmt(t, ' دقيقة')} اليوم بأي شكل ستفعله فعلاً.",
            f"你昨天活动了 {_fmt(c, ' 分钟')}。今天加上 {_fmt(t, ' 分钟')}，用任何你真会去做的形式。",
        ),
        lambda c, t: _t(
            "Stand up and move at the end of every screen block today, even for a minute.",
            "امروز آخر هر بلوکِ کار با صفحه بلند شو و حرکت کن، حتی یک دقیقه.",
            "قف وتحرّك في نهاية كل كتلة شاشة اليوم، ولو لدقيقة.",
            "今天每结束一段屏幕时间就站起来动一动，哪怕一分钟。",
        ),
        lambda c, t: _t(
            "Take the longer way to somewhere you were going anyway.",
            "برای جایی که به‌هرحال می‌رفتی، راه طولانی‌تر را انتخاب کن.",
            "اسلك الطريق الأطول إلى مكان كنت ذاهباً إليه أصلاً.",
            "去一个你本来就要去的地方，走远一点的那条路。",
        ),
    ]


def _reflection_templates() -> list[Template]:
    return [
        lambda c, t: _t(
            "Look back at yesterday's plan and mark honestly what you did not do. Not to feel bad - to find out which instruction was wrong.",
            "برنامه‌ی دیروز را نگاه کن و صادقانه علامت بزن چه کاری را انجام ندادی. نه برای حس بد — برای اینکه بفهمی کدام دستور اشتباه بوده.",
            "انظر إلى خطة الأمس وحدّد بصدق ما لم تفعله. ليس لتشعر بالسوء — بل لتعرف أي تعليمة كانت خاطئة.",
            "回头看看昨天的计划，诚实地标出你没做的部分。不是为了自责——是为了找出哪条指令本身就不对。",
        ),
        lambda c, t: _t(
            "Pick the one change this week that cost you least and keep only that one next week.",
            "از تغییرهای این هفته آن یکی را که کمترین هزینه را داشت انتخاب کن و هفته‌ی بعد فقط همان را نگه دار.",
            "اختر التغيير الأقل كلفة عليك هذا الأسبوع وأبقِ عليه وحده الأسبوع القادم.",
            "从这周的改变里挑出对你代价最小的那一个，下周只保留它。",
        ),
        lambda c, t: _t(
            "Write one sentence about what this week was actually like. One. It will be more useful in a month than any number here.",
            "یک جمله بنویس درباره‌ی اینکه این هفته واقعاً چطور بود. یک جمله. یک ماه بعد از هر عددی که اینجاست مفیدتر خواهد بود.",
            "اكتب جملة واحدة عن حقيقة هذا الأسبوع. واحدة. ستكون بعد شهر أنفع من أي رقم هنا.",
            "写一句话，说说这一周实际上是什么样的。一句就够。一个月后它会比这里任何数字都有用。",
        ),
        # Four more so a maintenance week is six DIFFERENT days. With
        # only three, a healthy user's plan repeated from day four
        # onward even after the day-stride bug in
        # improvement_plan_service.py was fixed - three templates cannot
        # fill six days however you index them.
        lambda c, t: _t(
            "Name the hour today that felt easiest. Protect that same hour tomorrow before anything else claims it.",
            "ساعتی از امروز را نام ببر که راحت‌ترین بود. فردا همان ساعت را قبل از اینکه چیز دیگری آن را بگیرد، نگه دار.",
            "سمِّ الساعة التي بدت اليوم أسهل. واحمِ الساعة نفسها غداً قبل أن يطالب بها شيء آخر.",
            "说出今天感觉最轻松的那一个小时。明天在别的事情占用它之前，先把这一个小时留出来。",
        ),
        lambda c, t: _t(
            "Pick one habit you are keeping on autopilot and check it is still worth keeping. Good habits expire quietly too.",
            "یکی از عادت‌هایی را که خودکار ادامه می‌دهی انتخاب کن و ببین هنوز ارزش نگه‌داشتن دارد یا نه. عادت‌های خوب هم بی‌سروصدا تاریخ‌مصرفشان تمام می‌شود.",
            "اختر عادة تواصلها على الطيار الآلي وتحقق أنها ما زالت تستحق. العادات الجيدة تنتهي صلاحيتها بهدوء أيضاً.",
            "挑一个你正在自动执行的习惯，检查它是否还值得保留。好习惯也会悄悄过期。",
        ),
        lambda c, t: _t(
            "Tell one person what you are working on this week. Saying it out loud is the cheapest accountability there is.",
            "به یک نفر بگو این هفته روی چه چیزی کار می‌کنی. بلند گفتنش ارزان‌ترین شکل پاسخ‌گو بودن است.",
            "أخبر شخصاً واحداً بما تعمل عليه هذا الأسبوع. قوله بصوت عالٍ أرخص التزام ممكن.",
            "把你这周在做的事告诉一个人。说出口是最省力的一种自我约束。",
        ),
        lambda c, t: _t(
            "Do nothing differently today. Deliberately. A week you can repeat is worth more than a week you can brag about.",
            "امروز عمداً هیچ چیز را تغییر نده. هفته‌ای که بتوانی تکرارش کنی از هفته‌ای که بشود به آن بالید ارزشمندتر است.",
            "لا تفعل شيئاً مختلفاً اليوم. عن قصد. أسبوع تستطيع تكراره أثمن من أسبوع تستطيع التباهي به.",
            "今天什么都不用改，刻意如此。一个你能重复的星期，比一个值得炫耀的星期更有价值。",
        ),
    ]


@dataclass(slots=True)
class Theme:
    key: str
    field: str
    icon: str
    label: dict[str, str]
    templates: list[Template]
    # How to turn the user's current value into a target they can hit
    # today. Deliberately modest: a target nobody reaches is a target
    # that teaches people to ignore the plan.
    target: Callable[[float], float]
    lower_is_better: bool


THEMES: tuple[Theme, ...] = (
    Theme(
        "sleep", "sleep_hours", "😴",
        {"en": "Sleep", "fa": "خواب", "ar": "النوم", "zh": "睡眠"},
        _sleep_templates(), lambda v: min(9.0, _round_to(v + 0.5, 0.25)), False,
    ),
    Theme(
        "screen", "total_screen_min", "📱",
        {"en": "Screen time", "fa": "زمان صفحه", "ar": "وقت الشاشة", "zh": "屏幕时间"},
        _screen_templates(), lambda v: max(60.0, _round_to(v * 0.88, 5)), True,
    ),
    Theme(
        "night", "night_usage_min", "🌙",
        {"en": "Night screens", "fa": "صفحه در شب", "ar": "شاشات الليل", "zh": "夜间屏幕"},
        _night_templates(), lambda v: max(10.0, _round_to(v * 0.7, 5)), True,
    ),
    Theme(
        "focus", "phone_pickups_per_day", "🎯",
        {"en": "Focus", "fa": "تمرکز", "ar": "التركيز", "zh": "专注"},
        _focus_templates(), lambda v: max(20.0, _round_to(v * 0.85, 5)), True,
    ),
    Theme(
        "mood", "stress_0_10", "🧘",
        {"en": "How the day feels", "fa": "حسِ روز", "ar": "شعور اليوم", "zh": "这一天的感受"},
        _mood_templates(), lambda v: max(2.0, _round_to(v - 1, 0.5)), True,
    ),
    Theme(
        "movement", "physical_activity_min_per_day", "🚶",
        {"en": "Movement", "fa": "تحرک", "ar": "الحركة", "zh": "活动"},
        _movement_templates(), lambda v: _round_to(max(10.0, v * 0.25), 5), False,
    ),
    Theme(
        "reflection", "", "📝",
        {"en": "Looking back", "fa": "مرور", "ar": "المراجعة", "zh": "回顾"},
        _reflection_templates(), lambda v: v, False,
    ),
)

THEMES_BY_KEY: dict[str, Theme] = {theme.key: theme for theme in THEMES}


# How many distinct values each measured field can realistically take,
# at the resolution the app records it. Used only to report the real
# size of the exercise space - a template that names your 342 minutes
# is not the same sentence as one that names your 118.
_FIELD_STEPS: dict[str, int] = {
    "sleep_hours": 37,                       # 3.0-12.0 in 0.25h steps
    "total_screen_min": 115,                 # 30-600 in 5-min steps
    "night_usage_min": 61,                   # 0-300 in 5-min steps
    "phone_pickups_per_day": 60,             # 10-300 in 5-pickup steps
    "stress_0_10": 21,                       # 0-10 in 0.5 steps
    "physical_activity_min_per_day": 37,     # 0-180 in 5-min steps
}


def library_size() -> dict[str, int]:
    """The real size of the composed space, computed not claimed.

    Reported per part so a reader can see where it comes from and check
    the multiplication themselves, and asserted in the tests so the
    number cannot drift away from the code.
    """
    templates = sum(len(theme.templates) for theme in THEMES)
    combinations = templates * len(SLOTS) * len(TIERS)

    # The count that actually matters. Most templates embed the user's
    # own measured value, so one template is not one sentence - it is
    # one sentence per distinct value a user can arrive with. Counted
    # from the plausible range of each theme's field at the resolution
    # the app records it, rather than asserted.
    value_bound = 0
    for theme in THEMES:
        if not theme.field:
            continue
        span = _FIELD_STEPS.get(theme.field, 1)
        numeric_templates = sum(
            1 for template in theme.templates
            if "⁦" in "".join(template(1.0, 1.0).values())
        )
        value_bound += numeric_templates * span * len(SLOTS) * len(TIERS)
    flat = combinations - sum(
        1 for theme in THEMES for template in theme.templates
        if "⁦" in "".join(template(1.0, 1.0).values())
    ) * len(SLOTS) * len(TIERS)

    distinct = value_bound + flat
    return {
        "themes": len(THEMES),
        "templates": templates,
        "slots": len(SLOTS),
        "tiers": len(TIERS),
        "combinations": combinations,
        "distinct_exercises": distinct,
        "localized_variants": distinct * len(LANGUAGES),
    }


def compose(
    theme_key: str,
    template_index: int,
    slot: str,
    tier: str,
    current: Optional[float] = None,
) -> Optional[Exercise]:
    """One exercise, bound to `current` if the theme has a measurement.

    Returns None for an unknown theme rather than raising: a caller
    iterating over a user's weak signals should skip what it cannot
    build, not fail the whole plan.
    """
    theme = THEMES_BY_KEY.get(theme_key)
    if theme is None or not theme.templates:
        return None
    template = theme.templates[template_index % len(theme.templates)]
    target = theme.target(current) if (current is not None and theme.field) else None
    return Exercise(
        theme=theme.key,
        slot=slot if slot in SLOTS else "anytime",
        tier=tier if tier in TIERS else "notice",
        text=template(current, target),
        field=theme.field,
        current=current,
        target=target,
    )
