# -*- coding: utf-8 -*-
"""
Amazon-воронка: Telegram-бот.  Боевая сборка для @vadjik.

╔══════════════════════════════════════════════════════════════════════╗
║  Перед запуском задай переменную окружения BOT_TOKEN.                 ║
║  Локальный запуск:  BOT_TOKEN=твой_токен python bot.py                ║
║  Деплой на Railway: переменные задаются в Variables                   ║
║                                                                       ║
║  Подробнее: ДЕПЛОЙ.md / НАСТРОЙКА.md                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime

from urllib.parse import quote, urlencode
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    WebAppInfo,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                          C   O   N   F   I   G                       ║
# ║                 Редактируй только то, что в этом блоке.              ║
# ╚══════════════════════════════════════════════════════════════════════╝


# ──────────────────────────────────────────────────────────────────────
# 1) СЕКРЕТЫ И ССЫЛКИ.
#    BOT_TOKEN — только через переменную окружения (не светим в коде).
#    Остальное — дефолты в коде, можно переопределить через env.
# ──────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID  = int(os.getenv("ADMIN_ID", "0") or "0") or 630926654

# Ссылка для созвона/контакта — на твою личку.
CALL_LINK = os.getenv("CALL_LINK", "").strip() or "https://t.me/vadjik"

# Ссылка на твой сайт с результатами учеников.
SITE_LINK = os.getenv("SITE_LINK", "").strip() or "https://vadjik.com/"

# Ссылка на Telegram Mini App (витрина тарифов + результатов).
# Это HTTPS-адрес, где захостен mini_app/index.html (см. MINI_APP.md).
# Если пусто — кнопка «Что входит» покажет тарифы текстом (fallback).
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()


# ──────────────────────────────────────────────────────────────────────
# ПРОМО-СКИДКА (персональная ссылка со скидкой + таймер, синхрон с сайтом).
#
#   PROMO_SECRET   — ОБЩИЙ секрет с сайтом. Должен совпадать байт-в-байт.
#                    Задаётся ТОЛЬКО через переменную окружения.
#   DISCOUNT_URL   — страница скидок на сайте.
#   PROMO_HOURS    — на сколько часов даётся персональная скидка.
#
#   Бонус к скидке — личный созвон с Вадимом (текст в TXT["promo_*"]).
#   Промо выдаётся ТЁПЛЫМ и ГОРЯЧИМ после квиза (не холодным).
# ──────────────────────────────────────────────────────────────────────

PROMO_SECRET = os.getenv("PROMO_SECRET", "").strip()
DISCOUNT_URL = os.getenv("DISCOUNT_URL", "").strip() or "https://vadjik.com/discount"
PROMO_HOURS  = int(os.getenv("PROMO_HOURS", "24") or "24")


# ──────────────────────────────────────────────────────────────────────
# 2) ЛИД-МАГНИТ (подписка на канал в обмен на гайд).
#
#    CHANNEL_USERNAME — публичный @username твоего канала.
#    Бот ДОЛЖЕН быть админом этого канала, иначе не сможет проверять
#    подписку.
#
#    Гайд бот берёт так:
#      - если задан GUIDE_FILE_ID (env) — отправляет его (быстрее);
#      - иначе — отправляет файл guide.pdf, лежащий рядом с bot.py.
#    Просто положи guide.pdf в репозиторий рядом с этим файлом.
# ──────────────────────────────────────────────────────────────────────

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip() or "@ВПИШИ_КАНАЛ"

GUIDE_FILE_ID = os.getenv("GUIDE_FILE_ID", "").strip()  # опционально
GUIDE_FILENAME = "guide.pdf"  # имя файла рядом с bot.py


# ──────────────────────────────────────────────────────────────────────
# 3) ВИДЕО И КРУЖКИ — твои file_id уже вставлены.
#
#    Поле "kind": "video" / "document" / нет (авто-детект по префиксу).
#    Твои видео отправлены КАК ФАЙЛ → kind="document".  Они работают,
#    но в чате выглядят как карточка-файл. Чтобы играли inline —
#    перешли боту через «прикрепить → Видео» и обнови file_id.
# ──────────────────────────────────────────────────────────────────────

MEDIA = {

    # КРУЖОК «КТО Я» (58 сек) — после /start.
    "circle_intro":  {
        "file_id": "DQACAgIAAxkBAAFKzAdqFyStU7gV6l0pGGGAAhWYjnYljQACWZkAAkGloEiiEfuL4azkRTsE",
    },

    # ВИДЕО 1 — кейс про Игоря и $750.
    "video_1":       {
        "file_id": "BQACAgIAAxkBAAFKzENqFycwLExX8ZHgxFguDHQQkUE8FQACNawAAhyisEs4n-Kxr_JWDzsE",
        "kind": "document",
    },

    # ВИДЕО 2 — как работает механика.
    "video_2":       {
        "file_id": "BQACAgIAAxkBAAFKzFNqFygSOGbm-sL8eKcVrMhQLJvmSQACy6EAAhx_uEjFH5jE4gKh4TsE",
        "kind": "document",
    },

    # ВИДЕО 3 — кому НЕ стоит.
    "video_3":       {
        "file_id": "BQACAgIAAxkBAAFKzEhqFyeNaAvqb01pjfBfviHTPQQRMgACx6EAAhx_uEh7lyH6ZsTeXzsE",
        "kind": "document",
    },

    # КРУЖОК-РАЗВИЛКА (47 сек) — после видео 3, мост к офферу.
    "circle_fork":   {
        "file_id": "DQACAgIAAxkBAAFKzAVqFySUkfDwTwx7KrtI4tYmZe9fSwACWpoAAkGlqEgKegxUI1KocTsE",
    },
}


# ──────────────────────────────────────────────────────────────────────
# 4) СКРИНЫ-ПРУФЫ. Берутся с postimg.cc — Telegram сам качает по URL.
#    Захочешь зашить как file_id: включи /id, перешли скрин боту,
#    замени "url" на "file_id".
# ──────────────────────────────────────────────────────────────────────

# Блок A — после видео 1.
PROOFS_AFTER_V1 = [
    {"url": "https://i.postimg.cc/N0gpZWrD/photo-2026-05-26-17-43-03.jpg"},
    {"url": "https://i.postimg.cc/5txnDZFp/photo-2026-05-26-17-43-22.jpg"},
]

# Блок B — после видео 2.
PROOFS_AFTER_V2 = [
    {"url": "https://i.postimg.cc/MZM2sQwp/photo-2024-05-09-21-42-26.jpg"},
    {"url": "https://i.postimg.cc/5N8cJWjT/photo-2024-05-09-21-42-27.jpg"},
    {"url": "https://i.postimg.cc/2SYs89ZY/photo-2026-05-26-17-43-48.jpg"},
    {"url": "https://i.postimg.cc/nh16sK4k/photo-2026-05-26-17-44-17.jpg"},
]

# Блок C — стек учеников по странам (по кнопке «Результаты учеников»).
PROOFS_STUDENTS = [
    {"url": "https://i.postimg.cc/bvN41GLJ/Aleksej-SSA.png"},
    {"url": "https://i.postimg.cc/hGy6sS3Z/Andrej-Francia.jpg"},
    {"url": "https://i.postimg.cc/5txnDZFp/photo-2026-05-26-17-43-22.jpg"},
    {"url": "https://i.postimg.cc/J0JFRj7y/Valeria-Germania.jpg"},
    {"url": "https://i.postimg.cc/MZM2sQwp/photo-2024-05-09-21-42-26.jpg"},
    {"url": "https://i.postimg.cc/RV58XpGd/Igori-Italia.png"},
    {"url": "https://i.postimg.cc/bNx5M0BJ/Kiril-Germania.jpg"},
    {"url": "https://i.postimg.cc/VN6HdxLt/Marina-Kanada.png"},
]

# Скрин страницы с результатами с сайта.
SITE_SCREEN = {"url": "https://i.postimg.cc/Twnjw0m1/Screenshot-138.png"}


# ──────────────────────────────────────────────────────────────────────
# 5) ЗАДЕРЖКИ ДОГОНЯЮЩИХ (в часах).
# ──────────────────────────────────────────────────────────────────────

DRIP_HOURS = {
    "after_v1":     3,
    "after_v3":     6,
    "after_offer":  24,
    "after_lead":   12,
}


# ──────────────────────────────────────────────────────────────────────
# 6) ТЕКСТЫ. Меняй формулировки свободно.
# ──────────────────────────────────────────────────────────────────────

TXT = {
    "start": (
        "Вы здесь, потому что вам интересен Amazon — как там реально "
        "зарабатывают, сколько нужно вложить и стоит ли оно того.\n\n"
        "Я не буду грузить вас теорией. Покажу 3 коротких видео:\n"
        "— реальный кейс человека, который начал с нуля;\n"
        "— как именно работает эта модель по шагам;\n"
        "— и честно — кому этим заниматься НЕ стоит.\n\n"
        "Всего минут 15. После этого вы сами поймёте, ваше это или нет. "
        "Без давления."
    ),
    "after_circle_intro": (
        "Дальше — тот самый кейс. Парень, компания и $1000 на старте. "
        "Что из этого вышло — в видео."
    ),
    "before_v1": (
        "Здесь важна не сумма. Важно, ЧТО он сделал и в каком порядке — "
        "это можно повторить. Смотрите внимательно на момент с возвратами, "
        "многие на этом сыпятся."
    ),
    "proofs_v1_caption": (
        "Это аккуратный старт новичка. А вот к чему приходят, когда "
        "механика отлажена.\n\n"
        "Разные люди, разные страны, разные суммы. Результат зависит от "
        "того, сколько человек вложил в навык — гарантий тут нет ни у кого. "
        "Но механика у всех одна."
    ),
    "after_v1": (
        "Понятно, кейс есть. Но КАК это работает технически — дальше."
    ),
    "bridge_v2": (
        "В кейсе вы видели результат. Сейчас разберём саму механику — "
        "почему Amazon вообще позволяет так делать и где здесь ваше место."
    ),
    "proofs_v2_caption": (
        "В видео это мелькнуло быстро, поэтому отдельно — это не только США."
    ),
    "after_v2": "Теперь самое честное.",
    "bridge_v3": (
        "Это видео отговорит часть людей — и хорошо. Я не хочу, чтобы вы "
        "тратили деньги, если это не ваше. Но если после него вы всё ещё "
        "в деле — значит, разговор серьёзный."
    ),
    "after_v3": (
        "Если вы досмотрели до конца — это уже о многом говорит. "
        "Большинство закрывает на первой минуте.\n\n"
        "Теперь у вас на руках вся базовая картина: вы знаете, как "
        "работает модель, видели реальный результат и понимаете, кому "
        "это не подходит.\n\n"
        "Дальше развилка. О ней — на минуту ниже."
    ),
    "after_fork_circle": (
        "Никаких автоматических списаний и продаж в три клика. Следующий "
        "шаг — короткая анкета и 30-минутный разбор по видеосвязи. "
        "На разборе смотрим вашу ситуацию, я говорю — подходит вам это "
        "или нет. Дальше решаете вы."
    ),
    "offer_text": (
        "Что вы получаете — коротко:\n"
        "— Поиск поставщиков и прохождение верификации\n"
        "— Поиск прибыльных товаров и расчёт юнит-экономики\n"
        "— Первая отправка без ошибок, которые банят аккаунт\n"
        "— Сопровождение и разборы\n\n"
        "Это не «курс из видео». Это доведение вас до первых рабочих "
        "отправок."
    ),
    # Подарок — бонусные продукты, входят в любой тариф
    "offer_gift": (
        "🎁 И сразу подарок: в любой тариф входят 5 бонусных инструментов "
        "на ~$1839 — помощь с закрытыми брендами, поиск товаров и "
        "поставщиков, программа проверки товаров и автонастройка цены. "
        "Бесплатно.\n\n"
        "Нажмите «Что входит в обучение» — там все программы простыми "
        "словами, 19 результатов учеников и короткий словарь Amazon, "
        "если какие-то слова непонятны."
    ),
    # Текстовый fallback, если Mini App не настроен (WEBAPP_URL пуст)
    "programs_text": (
        "Программы обучения:\n\n"
        "1️⃣ Обучаюсь сам — $671\n"
        "   75 видео-уроков, программы-помощники, записи 9 онлайн-встреч, "
        "доступ навсегда. Без личных созвонов.\n\n"
        "2️⃣ Поток — $975\n"
        "   Всё выше + 9 онлайн-встреч в группе и 2 личных созвона, "
        "1 проверенный поставщик, поддержка 24/7. Доводим до первых "
        "продаж.\n\n"
        "3️⃣ Продвинутый — $1455  ⭐ популярный\n"
        "   Всё выше + 4 личных созвона, 3 поставщика для старта, "
        "выбор рынка (США или Европа), 4 месяца поддержки.\n\n"
        "4️⃣ Про уровень — $4200  💎 VIP\n"
        "   Бизнес под ключ: 12 личных созвонов, 10 поставщиков + помощь "
        "с 50 товарами, личный сайт + программа учёта (CRM), 6 месяцев "
        "поддержки. Цель — $15 000+ продаж в месяц.\n\n"
        "🎁 В каждый тариф входят бонусы на ~$1839.\n\n"
        "Какой подойдёт именно вам — разберём на созвоне."
    ),
    "offer_price_and_call": (
        "Сколько это стоит. Программа — в диапазоне [X–Y]. Финальная "
        "цифра зависит от формата: групповой поток или индивидуальное "
        "сопровождение. Точную сумму обсуждаем на разборе, после того "
        "как я посмотрю вашу ситуацию.\n\n"
        "Что будет на разборе (30 минут, по видеосвязи):\n"
        "— Вы рассказываете, где сейчас: бюджет, время, опыт\n"
        "— Я говорю честно, подходит ли вам Amazon\n"
        "— Если подходит — показываю, как именно сделаем\n"
        "— Если не подходит — говорю, что делать вместо этого\n\n"
        "Никакого давления. Если после разбора надо подумать — "
        "думайте сколько надо."
    ),
    "offer_risk": (
        "Когда оформляемся — по договору. Гарантия: [впиши свою "
        "формулировку]. Все вопросы — на разборе."
    ),
    "students_caption": (
        "Ученики из США, Франции, Германии, Италии и Канады. У каждого "
        "свой темп и свой формат — но механика везде одна."
    ),
    "site_caption": (
        "Это не все — на сайте больше результатов, отзывы и подробности. "
        "Загляните если интересно."
    ),
    "back_to_offer": "Готовы записаться на разбор?",

    "q1": "Сколько готовы вложить в товар на старте?",
    "q1_opts": ["до $300", "$300–1000", "$1000+", "Пока не готов"],
    "q2": "Сколько времени в день реально есть?",
    "q2_opts": ["меньше часа", "1–2 часа", "2+ часа"],
    "q3": "Когда хотите начать?",
    "q3_opts": ["сейчас", "в течение месяца", "просто изучаю"],

    "after_quiz": (
        "Спасибо. Я свяжусь с вами лично в ближайшее время. Если удобнее "
        "написать сразу — кнопка ниже."
    ),
    # Финал для холодных лидов (просто изучаю / пока не готов)
    "cold_finish": (
        "Понял вас — спешить некуда, это нормально. Раз вы пока "
        "присматриваетесь, у меня есть кое-что полезное на это время."
    ),

    "drip_after_v1": (
        "Вы остановились на кейсе. Самое важное — механика — в следующем "
        "видео, это 5 минут."
    ),
    "drip_after_v3": (
        "Вы досмотрели почти всё. Остался один шаг — что с этим делать "
        "дальше."
    ),
    "drip_after_offer": (
        "Видимо, что-то остановило — возможно, неудобный момент или "
        "остались вопросы. Если хотите спросить лично — напишите мне "
        "прямо сейчас. Или можете записаться на разбор. А если пока "
        "просто изучаете — заберите бесплатный гайд ниже."
    ),
    "drip_after_lead": (
        "Вы оставили заявку, я свяжусь. Если удобнее написать самому — "
        "вот контакт:"
    ),

    # ── ЛИД-МАГНИТ ──
    "lm_offer": (
        "Хотите забрать топ-3 ошибки Amazon-продавца, из-за которых "
        "чаще всего теряют деньги? Бесплатно, 1 шаг."
    ),
    "lm_subscribe": (
        "Супер. Всё, что нужно — подписаться на мой канал. Как только "
        "подпишетесь и нажмёте кнопку ниже, гайд придёт сюда автоматически."
    ),
    "lm_not_subscribed": (
        "Пока не вижу подписки. Подпишитесь на канал по кнопке выше и "
        "нажмите «Я подписался» ещё раз."
    ),
    "lm_delivered": (
        "Держите. Внутри — 3 ошибки, на которых чаще всего сливают "
        "деньги новички, и как их не допустить.\n\n"
        "Когда прочитаете — если захотите разобрать свою ситуацию лично, "
        "вот разбор:"
    ),
    "lm_skip": (
        "Хорошо. Если передумаете — гайд всегда можно забрать позже. "
        "А если будут вопросы — пишите лично:"
    ),
    "lm_error": (
        "Не получилось проверить подписку — возможно, канал ещё "
        "настраивается. Напишите мне лично, и я пришлю гайд вручную:"
    ),

    # ── ПРОМО-СКИДКА (тёплым/горячим после квиза) ──
    "promo_hot": (
        "🔥 У меня для вас персональное предложение.\n\n"
        "Раз вы готовы стартовать — даю на 24 часа скидку на обучение "
        "плюс бонусом личный созвон со мной, где разберём именно вашу "
        "ситуацию.\n\n"
        "Скидка действует {hours} часа по кнопке ниже — там цены уже "
        "пересчитаны, и идёт таймер. После — обычная цена."
    ),
    "promo_warm": (
        "Раз вам это интересно — вот персональное предложение.\n\n"
        "На 24 часа: скидка на обучение + бонусом личный созвон со мной "
        "для разбора вашей ситуации.\n\n"
        "Цены со скидкой и таймер — по кнопке ниже. Через {hours} часа "
        "предложение закрывается."
    ),
    "promo_pinned": (
        "⏳ Ваша скидка + личный созвон в подарок активны.\n"
        "Осталось: {left}\n\n"
        "Оформить со скидкой — кнопка в сообщении выше."
    ),
    "promo_expired": (
        "⌛ Время персональной скидки вышло. Но вы всё ещё можете "
        "записаться на разбор — напишите мне, обсудим варианты."
    ),
    "promo_drip": (
        "Напоминаю: ваша персональная скидка и личный созвон в подарок "
        "ещё действуют, но скоро закроются. Успеете — кнопка ниже."
    ),
}


# ──────────────────────────────────────────────────────────────────────
# 7) НАДПИСИ НА КНОПКАХ.
# ──────────────────────────────────────────────────────────────────────

BTN = {
    "start":      "Покажи, с чего начать",
    "to_v1":      "Смотреть кейс",
    "to_v2":      "Как это работает",
    "to_v3":      "Кому не стоит этим заниматься",
    "to_fork":    "Что дальше",
    "to_offer":   "Расскажи подробнее",
    "students":   "Результаты учеников",
    "programs":   "💎 Что входит в обучение",
    "site":       "Открыть сайт с результатами",
    "to_lead":    "Записаться на разбор",
    "contact":    "Написать @vadjik",
    # лид-магнит
    "lm_grab":    "Забрать топ-3 ошибки (бесплатно)",
    "lm_want":    "Хочу забрать",
    "lm_skip":    "Пропустить",
    "lm_goto":    "Перейти в канал",
    "lm_check":   "Я подписался ✅",
    # промо
    "promo_get":  "🔥 Забрать скидку + созвон",
    "promo_app":  "💎 Программы со скидкой",
}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║                       К О Н Е Ц    C O N F I G                       ║
# ╚══════════════════════════════════════════════════════════════════════╝


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO
)
log = logging.getLogger("amazon_bot")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "users.json")
GUIDE_PATH = os.path.join(BASE_DIR, GUIDE_FILENAME)

CHANNEL_LINK = "https://t.me/" + CHANNEL_USERNAME.lstrip("@")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("save_state failed: %s", e)


STATE = load_state()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def u(uid):
    uid = str(uid)
    if uid not in STATE:
        STATE[uid] = {"step": "start", "answers": {}, "joined": _now()}
    return STATE[uid]


def set_step(uid, step):
    rec = u(uid)
    rec["step"] = step
    rec["step_at"] = _now()
    save_state(STATE)


def _mk_btn(text, data, kind):
    """kind: False=callback, True/'url'=ссылка, 'webapp'=Mini App."""
    if kind == "webapp":
        return InlineKeyboardButton(text, web_app=WebAppInfo(url=data))
    if kind is True or kind == "url":
        return InlineKeyboardButton(text, url=data)
    return InlineKeyboardButton(text, callback_data=data)


def kb(rows):
    """Inline-клавиатура. Строка = (text, data, kind) или список таких."""
    buttons = []
    for row in rows:
        if isinstance(row, list):
            buttons.append([_mk_btn(t, d, k) for (t, d, k) in row])
        else:
            t, d, k = row
            buttons.append([_mk_btn(t, d, k)])
    return InlineKeyboardMarkup(buttons)


def webapp_url_full():
    """URL Mini App с подставленными ссылками contact/site."""
    if not WEBAPP_URL:
        return ""
    return (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
            f"&site={quote(SITE_LINK, safe='')}")


# ---------------- ПРОМО ----------------

def promo_sig(uid, deadline):
    """HMAC-SHA256 от '{uid}.{deadline}', hex lowercase — как ждёт сайт."""
    msg = f"{uid}.{deadline}".encode("utf-8")
    return hmac.new(PROMO_SECRET.encode("utf-8"), msg,
                    hashlib.sha256).hexdigest()


def build_discount_link(uid, deadline):
    """Подписанная ссылка на скидочную страницу сайта."""
    sig = promo_sig(uid, deadline)
    qs = urlencode({"uid": uid, "deadline": deadline, "sig": sig})
    return f"{DISCOUNT_URL}?{qs}"


def webapp_promo_url(uid, deadline, discount_link):
    """URL Mini App с проброшенным дедлайном — чтобы там тикал таймер."""
    if not WEBAPP_URL:
        return ""
    sig = promo_sig(uid, deadline)
    return (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
            f"&site={quote(SITE_LINK, safe='')}"
            f"&uid={uid}&deadline={deadline}&sig={sig}"
            f"&discount={quote(discount_link, safe='')}")


def lead_temperature(answers):
    """hot / warm — по ответам квиза (cold обрабатывается отдельно)."""
    budget = answers.get("q1", "")
    is_big_budget = budget == "$1000+"
    is_max_time = answers.get("q2", "") == "2+ часа"
    is_now = answers.get("q3", "") == "сейчас"
    if is_big_budget and is_max_time and is_now:
        return "hot"
    return "warm"


def fmt_left(deadline):
    """'Xч Yмин' до дедлайна, либо 'истекло'."""
    left = int(deadline - time.time())
    if left <= 0:
        return "истекло"
    h = left // 3600
    m = (left % 3600) // 60
    if h > 0:
        return f"{h}ч {m}мин"
    return f"{m}мин"


def detect_kind(file_id: str) -> str:
    if not file_id:
        return ""
    return {
        "BAAC": "video",
        "BQAC": "document",
        "DQAC": "video_note",
        "AgAC": "photo",
    }.get(file_id[:4], "")


async def send_media_file(bot, chat_id, key):
    ref = MEDIA.get(key, {})
    file_id = ref.get("file_id")
    if not file_id:
        path = ref.get("path")
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                await bot.send_video(chat_id, f)
        return
    kind = ref.get("kind") or detect_kind(file_id)
    try:
        if kind == "document":
            await bot.send_document(chat_id, file_id)
        else:
            await bot.send_video(chat_id, file_id)
    except Exception as e:
        log.error("send_media_file %s failed: %s", key, e)


async def send_circle(bot, chat_id, key):
    ref = MEDIA.get(key, {})
    fid = ref.get("file_id")
    if not fid:
        return
    try:
        await bot.send_video_note(chat_id, fid)
    except Exception as e:
        log.error("send_circle %s failed: %s", key, e)


def _resolve_photo_source(item):
    if item.get("file_id"):
        return item["file_id"]
    if item.get("url"):
        return item["url"]
    if item.get("path") and os.path.exists(item["path"]):
        return item["path"]
    return None


async def send_proofs(bot, chat_id, proofs, caption=None):
    sources = [_resolve_photo_source(p) for p in proofs]
    sources = [s for s in sources if s]
    if not sources:
        if caption:
            await bot.send_message(chat_id, caption)
        return
    try:
        if len(sources) == 1:
            src = sources[0]
            if isinstance(src, str) and os.path.exists(src):
                with open(src, "rb") as f:
                    await bot.send_photo(chat_id, f, caption=caption or None)
            else:
                await bot.send_photo(chat_id, src, caption=caption or None)
            return
        media = []
        files = []
        for i, src in enumerate(sources[:10]):
            cap = caption if i == 0 else None
            if isinstance(src, str) and os.path.exists(src):
                fh = open(src, "rb")
                files.append(fh)
                media.append(InputMediaPhoto(fh, caption=cap))
            else:
                media.append(InputMediaPhoto(src, caption=cap))
        await bot.send_media_group(chat_id, media)
        for fh in files:
            fh.close()
    except Exception as e:
        log.error("send_proofs failed: %s", e)
        if caption:
            await bot.send_message(chat_id, caption)


# ---------------- ЛИД-МАГНИТ ----------------

async def is_subscribed(bot, user_id) -> bool:
    """Проверяет, подписан ли пользователь на CHANNEL_USERNAME.
    Бот должен быть админом канала."""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("creator", "administrator", "member"):
            return True
        if member.status == "restricted":
            return bool(getattr(member, "is_member", False))
        return False
    except Exception as e:
        log.error("is_subscribed failed (%s): %s", CHANNEL_USERNAME, e)
        return None  # None = не смогли проверить (канал/права)


async def show_lead_magnet_offer(bot, chat_id, intro=None):
    """Показывает предложение лид-магнита с выбором Хочу/Пропустить."""
    text = (intro + "\n\n" if intro else "") + TXT["lm_offer"]
    await bot.send_message(
        chat_id, text,
        reply_markup=kb([
            (BTN["lm_want"], "lm_want", False),
            (BTN["lm_skip"], "lm_skip", False),
        ]),
    )


async def lm_want(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(
        uid, TXT["lm_subscribe"],
        reply_markup=kb([
            (BTN["lm_goto"], CHANNEL_LINK, True),
            (BTN["lm_check"], "lm_check", False),
        ]),
    )


async def lm_skip(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(
        uid, TXT["lm_skip"],
        reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
    )


async def lm_check(update, context):
    uid = update.effective_user.id
    bot = context.bot
    sub = await is_subscribed(bot, uid)

    if sub is None:
        # не смогли проверить — отдадим контакт, не теряем человека
        await bot.send_message(
            uid, TXT["lm_error"],
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
        return

    if not sub:
        await bot.send_message(
            uid, TXT["lm_not_subscribed"],
            reply_markup=kb([
                (BTN["lm_goto"], CHANNEL_LINK, True),
                (BTN["lm_check"], "lm_check", False),
            ]),
        )
        return

    # подписан — выдаём гайд
    await send_guide(bot, uid)
    rec = u(uid)
    rec["got_guide"] = True
    save_state(STATE)
    await bot.send_message(
        uid, TXT["lm_delivered"],
        reply_markup=kb([(BTN["to_lead"], "go_lead", False)]),
    )


async def send_guide(bot, chat_id):
    try:
        if GUIDE_FILE_ID:
            await bot.send_document(chat_id, GUIDE_FILE_ID)
            return
        if os.path.exists(GUIDE_PATH):
            with open(GUIDE_PATH, "rb") as f:
                await bot.send_document(chat_id, f, filename=GUIDE_FILENAME)
            return
        log.error("guide not found: GUIDE_FILE_ID пуст и нет %s", GUIDE_PATH)
        await bot.send_message(
            chat_id,
            "Гайд временно недоступен — напишите мне лично, пришлю вручную.",
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
    except Exception as e:
        log.error("send_guide failed: %s", e)


# ---------------- ПОКАЗ ПРОМО ----------------

async def show_promo(context, uid, user, temperature):
    """Выдаёт персональную скидку: ссылка с подписью, закреп, таймер."""
    bot = context.bot
    rec = u(uid)

    if not PROMO_SECRET:
        # секрет не задан — не выдаём кривую ссылку, ведём на разбор
        await bot.send_message(
            uid, TXT["after_quiz"],
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
        log.warning("PROMO_SECRET не задан — промо не выдано, отдан контакт")
        return

    deadline = int(time.time()) + PROMO_HOURS * 3600
    link = build_discount_link(uid, deadline)

    rec["promo"] = {
        "issued_at": int(time.time()),
        "deadline": deadline,
        "link": link,
        "temperature": temperature,
    }
    save_state(STATE)

    intro = TXT["promo_hot"] if temperature == "hot" else TXT["promo_warm"]
    intro = intro.format(hours=PROMO_HOURS)

    # кнопки: оформить со скидкой, программы со скидкой (Mini App), контакт
    rows = [(BTN["promo_get"], link, True)]
    if WEBAPP_URL:
        rows.append((BTN["promo_app"], webapp_promo_url(uid, deadline, link), "webapp"))
    rows.append((BTN["contact"], CALL_LINK, True))

    await bot.send_message(uid, intro, reply_markup=kb(rows))

    # закреплённое сообщение с таймером
    try:
        pin = await bot.send_message(
            uid, TXT["promo_pinned"].format(left=fmt_left(deadline)))
        await bot.pin_chat_message(uid, pin.message_id,
                                   disable_notification=True)
        rec["promo"]["pin_msg_id"] = pin.message_id
        save_state(STATE)
        # обновляем закреп раз в 30 минут (не чаще — бережём лимиты Telegram)
        context.application.job_queue.run_repeating(
            promo_tick, interval=1800, first=1800,
            name=f"promotick_{uid}", data={"uid": uid},
        )
    except Exception as e:
        log.error("promo pin failed: %s", e)

    # напоминание за пару часов до конца
    remind_in = max(60, (PROMO_HOURS - 2) * 3600)
    context.application.job_queue.run_once(
        promo_remind, when=remind_in,
        name=f"promoremind_{uid}", data={"uid": uid},
    )


async def promo_tick(context: ContextTypes.DEFAULT_TYPE):
    """Обновляет закреплённое сообщение с обратным отсчётом."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    pin_id = promo.get("pin_msg_id")
    deadline = promo.get("deadline", 0)
    if not pin_id:
        context.job.schedule_removal()
        return
    bot = context.bot
    if time.time() >= deadline:
        # истекло — финальный текст, открепить, остановить джоб
        try:
            await bot.edit_message_text(TXT["promo_expired"], uid, pin_id)
            await bot.unpin_chat_message(uid, pin_id)
        except Exception as e:
            log.error("promo expire failed: %s", e)
        context.job.schedule_removal()
        return
    try:
        await bot.edit_message_text(
            TXT["promo_pinned"].format(left=fmt_left(deadline)), uid, pin_id)
    except Exception:
        pass  # текст не изменился или сообщение удалено — не страшно


async def promo_remind(context: ContextTypes.DEFAULT_TYPE):
    """Однократное напоминание ближе к концу промо."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    deadline = promo.get("deadline", 0)
    if time.time() >= deadline:
        return
    try:
        await context.bot.send_message(
            uid, TXT["promo_drip"],
            reply_markup=kb([(BTN["promo_get"], promo.get("link"), True)]),
        )
    except Exception as e:
        log.error("promo_remind failed: %s", e)


# ---------------- ДОГОНЯЮЩИЕ ----------------

def cancel_drips(app, uid):
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith(f"drip_{uid}_"):
            job.schedule_removal()


def schedule_drip(app, uid, tag, hours):
    cancel_drips(app, uid)
    app.job_queue.run_once(
        drip_fire, when=hours * 3600,
        name=f"drip_{uid}_{tag}",
        data={"uid": uid, "tag": tag},
    )


async def drip_fire(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    uid = data["uid"]
    tag = data["tag"]
    rec = u(uid)

    expected_step = {
        "after_v1":    "v1",
        "after_v3":    "v3",
        "after_offer": "offer",
        "after_lead":  "qualified",
    }.get(tag)
    if rec.get("step") != expected_step:
        return

    bot = context.bot
    try:
        if tag == "after_v1":
            await bot.send_message(
                uid, TXT["drip_after_v1"],
                reply_markup=kb([(BTN["to_v2"], "go_v2", False)]),
            )
        elif tag == "after_v3":
            await bot.send_message(
                uid, TXT["drip_after_v3"],
                reply_markup=kb([(BTN["to_fork"], "go_fork", False)]),
            )
        elif tag == "after_offer":
            # текст + 3 кнопки: разбор / лид-магнит / личка
            await bot.send_message(
                uid, TXT["drip_after_offer"],
                reply_markup=kb([
                    (BTN["to_lead"], "go_lead", False),
                    (BTN["lm_grab"], "lm_want", False),
                    (BTN["contact"], CALL_LINK, True),
                ]),
            )
        elif tag == "after_lead":
            await bot.send_message(
                uid, TXT["drip_after_lead"],
                reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
            )
    except Exception as e:
        log.error("drip_fire failed: %s", e)


# ---------------- ШАГИ ВОРОНКИ ----------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cancel_drips(context.application, uid)
    set_step(uid, "start")
    await context.bot.send_message(
        uid, TXT["start"],
        reply_markup=kb([(BTN["start"], "go_intro", False)]),
    )


async def go_intro(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_circle(bot, uid, "circle_intro")
    await bot.send_message(
        uid, TXT["after_circle_intro"],
        reply_markup=kb([(BTN["to_v1"], "go_v1", False)]),
    )
    set_step(uid, "intro")


async def go_v1(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(uid, TXT["before_v1"])
    await send_media_file(bot, uid, "video_1")
    await send_proofs(bot, uid, PROOFS_AFTER_V1, TXT["proofs_v1_caption"])
    await bot.send_message(
        uid, TXT["after_v1"],
        reply_markup=kb([(BTN["to_v2"], "go_v2", False)]),
    )
    set_step(uid, "v1")
    schedule_drip(context.application, uid, "after_v1", DRIP_HOURS["after_v1"])


async def go_v2(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await bot.send_message(uid, TXT["bridge_v2"])
    await send_media_file(bot, uid, "video_2")
    await send_proofs(bot, uid, PROOFS_AFTER_V2, TXT["proofs_v2_caption"])
    await bot.send_message(
        uid, TXT["after_v2"],
        reply_markup=kb([(BTN["to_v3"], "go_v3", False)]),
    )
    set_step(uid, "v2")


async def go_v3(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(uid, TXT["bridge_v3"])
    await send_media_file(bot, uid, "video_3")
    await bot.send_message(
        uid, TXT["after_v3"],
        reply_markup=kb([(BTN["to_fork"], "go_fork", False)]),
    )
    set_step(uid, "v3")
    schedule_drip(context.application, uid, "after_v3", DRIP_HOURS["after_v3"])


async def go_fork(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_circle(bot, uid, "circle_fork")
    await bot.send_message(
        uid, TXT["after_fork_circle"],
        reply_markup=kb([(BTN["to_offer"], "go_offer", False)]),
    )
    set_step(uid, "fork")


async def go_offer(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await bot.send_message(uid, TXT["offer_text"])
    await bot.send_message(uid, TXT["offer_price_and_call"])
    await bot.send_message(uid, TXT["offer_gift"])

    # Кнопка «Что входит»: Mini App если есть URL, иначе текстовый показ.
    if WEBAPP_URL:
        programs_btn = (BTN["programs"], webapp_url_full(), "webapp")
    else:
        programs_btn = (BTN["programs"], "go_programs", False)

    await bot.send_message(
        uid, TXT["offer_risk"],
        reply_markup=kb([
            programs_btn,
            (BTN["to_lead"], "go_lead", False),
        ]),
    )
    set_step(uid, "offer")
    schedule_drip(context.application, uid, "after_offer",
                  DRIP_HOURS["after_offer"])


async def go_programs(update, context):
    """Текстовый показ программ — fallback, если Mini App не настроен,
    либо по команде /programs когда WEBAPP_URL пуст."""
    uid = update.effective_user.id
    bot = context.bot
    # если Mini App настроен — лучше открыть его
    if WEBAPP_URL:
        await bot.send_message(
            uid, "Открываю программы и результаты:",
            reply_markup=kb([
                (BTN["programs"], webapp_url_full(), "webapp"),
                (BTN["to_lead"], "go_lead", False),
            ]),
        )
        return
    # иначе — тарифы текстом + старый показ результатов фото
    await bot.send_message(uid, TXT["programs_text"])
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await bot.send_message(
        uid, TXT["back_to_offer"],
        reply_markup=kb([
            (BTN["site"], SITE_LINK, True),
            (BTN["to_lead"], "go_lead", False),
        ]),
    )


async def go_students(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await bot.send_message(
        uid, TXT["back_to_offer"],
        reply_markup=kb([
            (BTN["site"],    SITE_LINK, True),
            (BTN["to_lead"], "go_lead", False),
        ]),
    )


async def go_lead(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    set_step(uid, "lead")
    await bot.send_message(
        uid, TXT["q1"],
        reply_markup=kb([(o, f"a1_{i}", False)
                         for i, o in enumerate(TXT["q1_opts"])]),
    )


async def answer(update, context, qnum, idx):
    uid = update.effective_user.id
    bot = context.bot
    rec = u(uid)
    opts = TXT[f"q{qnum}_opts"]
    rec["answers"][f"q{qnum}"] = opts[idx]
    save_state(STATE)

    if qnum == 1:
        await bot.send_message(
            uid, TXT["q2"],
            reply_markup=kb([(o, f"a2_{i}", False)
                             for i, o in enumerate(TXT["q2_opts"])]),
        )
        return
    if qnum == 2:
        await bot.send_message(
            uid, TXT["q3"],
            reply_markup=kb([(o, f"a3_{i}", False)
                             for i, o in enumerate(TXT["q3_opts"])]),
        )
        return

    # qnum == 3 — финал квиза
    a = rec["answers"]
    is_cold = (a.get("q1") == "Пока не готов") or (a.get("q3") == "просто изучаю")
    user = update.effective_user
    rec["full_name"] = user.full_name
    rec["username"] = user.username or ""

    temperature = "cold"
    if is_cold:
        # холодному — лид-магнит вместо приглашения на разбор
        set_step(uid, "qualified_cold")
        rec["temperature"] = "cold"
        save_state(STATE)
        await show_lead_magnet_offer(bot, uid, intro=TXT["cold_finish"])
    else:
        # тёплый/горячий — персональная скидка + бонус личный созвон
        temperature = lead_temperature(a)
        set_step(uid, "qualified")
        rec["temperature"] = temperature
        save_state(STATE)
        await show_promo(context, uid, user, temperature)
        schedule_drip(context.application, uid, "after_lead",
                      DRIP_HOURS["after_lead"])

    # уведомление тебе в любом случае
    if ADMIN_ID:
        uname = f"@{user.username}" if user.username else "(без username)"
        tag = {"cold": "❄️ ХОЛОДНЫЙ (изучает)",
               "warm": "🔥 ТЁПЛЫЙ — выдана скидка",
               "hot":  "🔥🔥 ГОРЯЧИЙ — выдана скидка"}[temperature]
        promo_line = ""
        if temperature != "cold":
            dl = rec.get("promo", {}).get("deadline")
            if dl:
                promo_line = (f"\nСкидка действует до: "
                              f"{datetime.fromtimestamp(dl):%d.%m %H:%M} "
                              f"(осталось {fmt_left(dl)})")
        try:
            await bot.send_message(
                ADMIN_ID,
                f"{tag}\n"
                f"Имя: {user.full_name}\n"
                f"Username: {uname}\n"
                f"ID: {user.id}\n"
                f"Чат: tg://user?id={user.id}\n\n"
                f"Бюджет: {a.get('q1','-')}\n"
                f"Время: {a.get('q2','-')}\n"
                f"Старт: {a.get('q3','-')}"
                f"{promo_line}",
            )
        except Exception as e:
            log.error("notify admin failed: %s", e)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    routes = {
        "go_intro":    go_intro,
        "go_v1":       go_v1,
        "go_v2":       go_v2,
        "go_v3":       go_v3,
        "go_fork":     go_fork,
        "go_offer":    go_offer,
        "go_programs": go_programs,
        "go_students": go_students,
        "go_lead":     go_lead,
        "lm_want":     lm_want,
        "lm_skip":     lm_skip,
        "lm_check":    lm_check,
    }
    if d in routes:
        await routes[d](update, context)
        return
    if d.startswith("a1_"):
        await answer(update, context, 1, int(d.split("_")[1]))
    elif d.startswith("a2_"):
        await answer(update, context, 2, int(d.split("_")[1]))
    elif d.startswith("a3_"):
        await answer(update, context, 3, int(d.split("_")[1]))
    elif d.startswith("mk_"):
        # mk_{lead_id}_{status} — только админ
        if update.effective_user.id != ADMIN_ID:
            return
        _, lead_id, status = d.split("_", 2)
        rec = STATE.get(lead_id)
        if rec:
            rec["outcome"] = status
            save_state(STATE)
            names = {"paid": "✅ оплатил", "booked": "📅 записан",
                     "noshow": "🚫 не пришёл", "lost": "❌ отказ"}
            await q.edit_message_text(
                f"{q.message.text}\n\n➡️ Статус обновлён: "
                f"{names.get(status, status)}")


# ---------------- АДМИН-КОМАНДЫ ----------------

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Режим получения file_id включён.\n"
        "Пришли мне сюда видео, кружок, фото или PDF — отвечу его file_id."
    )


async def grab_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    m = update.message
    out = None
    if m.video_note:
        out = (f"КРУЖОК (video_note, {m.video_note.duration} сек)\n"
               f"file_id:\n{m.video_note.file_id}")
    elif m.video:
        out = (f"ВИДЕО ({m.video.duration} сек)\n"
               f"file_id:\n{m.video.file_id}\n\nkind: \"video\"")
    elif m.photo:
        out = f"ФОТО\nfile_id:\n{m.photo[-1].file_id}"
    elif m.document:
        mt = m.document.mime_type or ""
        extra = ""
        if "pdf" in mt:
            extra = ("\n\nЭто PDF — можешь использовать как GUIDE_FILE_ID "
                     "(env), чтобы не хранить файл.")
        else:
            extra = ("\n\nЕсли это видео — пришли через «прикрепить → Видео», "
                     "чтобы играло inline.")
        out = (f"ДОКУМЕНТ ({mt})\nfile_id:\n{m.document.file_id}{extra}")
    if out:
        await m.reply_text(out)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    counts = {}
    guide_count = 0
    temp = {"hot": 0, "warm": 0, "cold": 0}
    promo_issued = promo_active = 0
    outcomes = {}
    now = time.time()
    for rec in STATE.values():
        s = rec.get("step", "start")
        counts[s] = counts.get(s, 0) + 1
        if rec.get("got_guide"):
            guide_count += 1
        t = rec.get("temperature")
        if t in temp:
            temp[t] += 1
        promo = rec.get("promo")
        if promo:
            promo_issued += 1
            if promo.get("deadline", 0) > now:
                promo_active += 1
        oc = rec.get("outcome")
        if oc:
            outcomes[oc] = outcomes.get(oc, 0) + 1
    order = ["start", "intro", "v1", "v2", "v3", "fork",
             "offer", "lead", "qualified", "qualified_cold"]
    lines = ["📊 Воронка (кто на каком шаге сейчас):"]
    for s in order:
        lines.append(f"{s}: {counts.get(s, 0)}")
    lines.append(f"\n🌡 Тёплых: {temp['warm']} · Горячих: {temp['hot']} · "
                 f"Холодных: {temp['cold']}")
    lines.append(f"🔥 Промо выдано: {promo_issued} (активно сейчас: {promo_active})")
    lines.append(f"🎁 Забрали гайд: {guide_count}")
    if outcomes:
        oc_str = " · ".join(f"{k}: {v}" for k, v in outcomes.items())
        lines.append(f"📌 Статусы: {oc_str}")
    lines.append(f"\nВсего людей: {len(STATE)}")
    lines.append("\n/report — выгрузить всех в файл (Excel)")
    lines.append("/lead ID — карточка лида + смена статуса")
    await update.message.reply_text("\n".join(lines))


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выгрузка всех лидов в CSV (открывается в Excel)."""
    if update.effective_user.id != ADMIN_ID:
        return
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["telegram_id", "username", "имя", "температура", "шаг",
                "бюджет", "время_в_день", "когда_старт", "забрал_гайд",
                "промо_выдано", "промо_дедлайн", "статус", "вошёл",
                "последнее_действие"])
    for uid, rec in STATE.items():
        a = rec.get("answers", {})
        promo = rec.get("promo") or {}
        dl = promo.get("deadline")
        dl_str = datetime.fromtimestamp(dl).strftime("%Y-%m-%d %H:%M") if dl else ""
        w.writerow([
            uid, rec.get("username", ""), rec.get("full_name", ""),
            rec.get("temperature", ""), rec.get("step", ""),
            a.get("q1", ""), a.get("q2", ""), a.get("q3", ""),
            "да" if rec.get("got_guide") else "",
            "да" if promo else "", dl_str,
            rec.get("outcome", ""),
            rec.get("joined", ""), rec.get("step_at", ""),
        ])
    data = buf.getvalue().encode("utf-8-sig")  # BOM — чтобы Excel не ломал кириллицу
    import io as _io
    bio = _io.BytesIO(data)
    bio.name = f"leads_{datetime.now():%Y%m%d_%H%M}.csv"
    await context.bot.send_document(
        update.effective_user.id, bio,
        caption=f"Отчёт по {len(STATE)} лидам. Открывается в Excel.")


async def cmd_lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Карточка одного лида + кнопки смены статуса."""
    if update.effective_user.id != ADMIN_ID:
        return
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        await update.message.reply_text("Использование: /lead ID\n"
                                        "ID берётся из уведомления о заявке.")
        return
    lead_id = parts[1].strip()
    rec = STATE.get(lead_id)
    if not rec:
        await update.message.reply_text("Лид с таким ID не найден.")
        return
    a = rec.get("answers", {})
    promo = rec.get("promo") or {}
    dl = promo.get("deadline")
    dl_str = (f"{datetime.fromtimestamp(dl):%d.%m %H:%M} "
              f"({fmt_left(dl)})") if dl else "—"
    uname = f"@{rec['username']}" if rec.get("username") else "—"
    txt = (
        f"👤 {rec.get('full_name','—')}  {uname}\n"
        f"ID: {lead_id}\n"
        f"Чат: tg://user?id={lead_id}\n\n"
        f"Температура: {rec.get('temperature','—')}\n"
        f"Шаг: {rec.get('step','—')}\n"
        f"Бюджет: {a.get('q1','—')} · Время: {a.get('q2','—')} · "
        f"Старт: {a.get('q3','—')}\n"
        f"Гайд забрал: {'да' if rec.get('got_guide') else 'нет'}\n"
        f"Промо: {'выдано, до '+dl_str if promo else 'нет'}\n"
        f"Статус: {rec.get('outcome','не задан')}\n\n"
        f"Отметить статус:"
    )
    await update.message.reply_text(txt, reply_markup=kb([
        [("✅ Оплатил", f"mk_{lead_id}_paid", False),
         ("📅 Записан", f"mk_{lead_id}_booked", False)],
        [("🚫 Не пришёл", f"mk_{lead_id}_noshow", False),
         ("❌ Отказ", f"mk_{lead_id}_lost", False)],
    ]))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = str(update.effective_user.id)
    cancel_drips(context.application, update.effective_user.id)
    if uid in STATE:
        del STATE[uid]
        save_state(STATE)
    await update.message.reply_text(
        "Готово. Напиши /start — воронка пойдёт заново."
    )


async def cmd_programs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть витрину программ в любой момент."""
    await go_programs(update, context)


def main():
    if not BOT_TOKEN:
        print("ОШИБКА: переменная окружения BOT_TOKEN не задана.")
        print("Локально:  BOT_TOKEN=твой_токен python bot.py")
        print("Railway:   добавь BOT_TOKEN в Variables")
        return

    if CHANNEL_USERNAME == "@ВПИШИ_КАНАЛ":
        log.warning("CHANNEL_USERNAME не задан — лид-магнит не сможет "
                    "проверять подписку. Задай переменную CHANNEL_USERNAME.")

    if not WEBAPP_URL:
        log.warning("WEBAPP_URL не задан — кнопка «Что входит» покажет "
                    "программы текстом. Для Mini App см. MINI_APP.md.")

    if not PROMO_SECRET:
        log.warning("PROMO_SECRET не задан — промо-скидки выдаваться НЕ будут "
                    "(тёплым/горячим отдаётся контакт). Задай PROMO_SECRET.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("programs", cmd_programs))
    app.add_handler(CommandHandler("id",    cmd_id))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("lead", cmd_lead))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.VIDEO_NOTE | filters.PHOTO
        | filters.Document.ALL,
        grab_file_id,
    ))

    log.info("Бот запущен. ADMIN_ID=%s, канал=%s, DATA=%s",
             ADMIN_ID, CHANNEL_USERNAME, STATE_FILE)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
