# ── aviahelp_bot.py ──────────────────────────────────────────────────────────
import os
import re
import logging
from datetime import datetime, timedelta

import telebot                       # pip install pyTelegramBotAPI
from airportsdata import airports     # pip install airportsdata

# ─────────────────────────  НАСТРОЙКИ  ───────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_FALLBACK_TOKEN")
BOT    = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# airports() возвращает dict: {'ALA': {...}, 'FRA': {...}, ...}
AIRPORTS = airports()                # кэшируется в памяти

# Мини-словарик авиакомпаний.  Если нет в списке – вернём сам код.
AIRLINES = {
    "LH": "Lufthansa",
    "KC": "Air Astana",
    "SU": "Aeroflot",
    "TK": "Turkish Airlines",
    "HY": "Uzbekistan Airways",
    # …добавляйте по мере надобности
}
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)

WELCOME_RU = (
    "👋 Привет! Я *AgentHelpBot*.\n"
    "Этот бот создан для помощи авиа-агентам в расшифровке GDS-сегментов: "
    "маршрутов, дат, кодов и других данных.\n"
    "Сейчас бот работает абсолютно бесплатно и доступен 24/7.\n\n"
    "Просто пришлите мне текст бронирования (можно сразу несколько сегментов) — "
    "и я все разложу «по полочкам» 🙂"
)

WELCOME_EN = (
    "👋 Hello! I’m *AgentHelpBot*.\n"
    "This bot helps travel agents decode GDS segments, routes, dates, airline "
    "codes and more.\n"
    "It’s currently completely free and available 24/7.\n\n"
    "Just send me the booking text (one or many segments) and I’ll explain it "
    "in plain language."
)

# ---------------------------------------------------------------------------#
#  ШАБЛОНЫ РЕГУЛЯРНЫХ ВЫРАЖЕНИЙ                                               #
# ---------------------------------------------------------------------------#
SEGMENT_RE = re.compile(
    r"""
    (?P<index>\d+)\s+                       # порядковый номер
    (?P<airline>[A-Z0-9]{2})\s+             # код авиакомпании
    (?P<flight>\d{1,4})\s+                  # номер рейса
    (?P<class>[A-Z])\s+                     # класс бронирования
    (?P<dep_date>\d{2}[A-Z]{3})\s+\d+\s+    # дата вылета + день недели
    (?P<route>[A-Z]{6})\s+                 # 6-симв. код аэропорты (ALA*FRA*)
    \S+\s+                                 # статус (DK1 / HK2 …) — пропускаем
    (?P<dep_time>\d{4})\s+                 # время вылета
    (?P<arr_time>\d{4})                    # время прилёта
    """,
    re.VERBOSE,
)

# ---------------------------------------------------------------------------#
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ                                                    #
# ---------------------------------------------------------------------------#
def lookup_airport(iata: str) -> str:
    """Возвращает 'Город (Аэропорт)' по коду IATA."""
    info = AIRPORTS.get(iata)
    if not info:
        return iata
    city  = info["city"]
    name  = info["name"]
    return f"{city} ({name})"

def lookup_airline(code: str) -> str:
    return AIRLINES.get(code, code)

def parse_segment(text: str) -> dict | None:
    m = SEGMENT_RE.search(text.upper().replace(" ", " "))   # NB: убираем не-break space
    if not m:
        return None

    data = m.groupdict()
    dep_air, arr_air = data["route"][:3], data["route"][3:]
    dep_time = datetime.strptime(data["dep_time"], "%H%M")
    arr_time = datetime.strptime(data["arr_time"], "%H%M")
    if arr_time < dep_time:                # прилёт «на след. день»
        arr_time += timedelta(days=1)
    duration = arr_time - dep_time

    return {
        "variant": data["index"],
        "airline_code": data["airline"],
        "airline":      lookup_airline(data["airline"]),
        "flight":       f'{data["airline"]}{data["flight"]}',
        "dep_date":     data["dep_date"],
        "from_code":    dep_air,
        "from_full":    lookup_airport(dep_air),
        "to_code":      arr_air,
        "to_full":      lookup_airport(arr_air),
        "dep_time":     dep_time.strftime("%H:%M"),
        "arr_time":     arr_time.strftime("%H:%M"),
        "duration":     f"{duration.seconds//3600}ч {(duration.seconds//60)%60:02d}м",
    }

def format_reply(info: dict) -> str:
    """Собирает красивый блок для одного варианта."""
    return (
        f"Вариант {info['variant']}  –  {info['to_code']}\n\n"
        f"Туда: {info['dep_date']}, {info['dep_time']} – {info['arr_time']}, "
        f"{info['from_code']} → {info['to_code']}, {info['flight']}, {info['airline']}.\n"
        f"В пути {info['duration']}\n"
        f"⬅️ Обратно: (указать вручную)\n\n"
        f"Цена: ____ ₸ / $ / €\n"
        f"Класс: Эконом / Бизнес\n"
        f"Багаж: Включён / Только ручная кладь\n"
        f"Возврат билета: Без штрафа / Штраф _ USD\n"
        f"Перенос даты: Без штрафа / Штраф _ USD\n"
        f"Примечание: __________\n"
    )

# ---------------------------------------------------------------------------#
#  ОБРАБОТЧИКИ СООБЩЕНИЙ                                                     #
# ---------------------------------------------------------------------------#
@BOT.message_handler(commands=['start'])
def cmd_start(msg: telebot.types.Message) -> None:
    BOT.send_message(msg.chat.id, f"{WELCOME_RU}\n\n---\n\n{WELCOME_EN}")

@BOT.message_handler(func=lambda m: True)
def handle_text(msg: telebot.types.Message) -> None:
    segments = SEGMENT_RE.findall(msg.text.upper())
    if not segments:
        BOT.reply_to(msg, "❗️ Не удалось найти GDS-сегменты в сообщении.")
        return

    # нужно снова прогнать через re.finditer, чтобы получить полные строки
    replies = []
    for match in SEGMENT_RE.finditer(msg.text.upper()):
        parsed = parse_segment(match.group(0))
        if parsed:
            replies.append(format_reply(parsed))

    BOT.reply_to(msg, "\n\n".join(replies))

# ---------------------------------------------------------------------------#
#  ЗАПУСК ПУЛЛИНГА                                                           #
# ---------------------------------------------------------------------------#
if _name_ == "_main_":
    logging.info("Bot started…")
    BOT.infinity_polling(skip_pending=True)
# ─────────────────────────────────────────────────────────────────────────────
