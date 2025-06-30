import os, re, logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from airportsdata import load           # база аэропортов IATA → данные
from dateutil import parser as dtparse  # умный разбор дат

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN", "PASTE_YOUR_TOKEN_HERE")
print(f"Loaded token: {API_TOKEN}")
bot = Bot(API_TOKEN)
dp  = Dispatcher(bot)

# ───────────────────────────────────────────────────────────────
#  Справочник авиакомпаний (код → рус, англ). Добавь при желании.
# ───────────────────────────────────────────────────────────────
AIRLINES = {
    "LH": ("Lufthansa",          "Lufthansa"),
    "KC": ("Эйр Астана",         "Air Astana"),
    "CZ": ("China Southern",     "China Southern Airlines"),
    "CA": ("Air China",          "Air China"),
    # … дополняй по мере надобности …
}

#  База аэропортов: code → {"city":"Almaty", "name":"Almaty Airport", …}
AIRPORTS = load("IATA")         # подгружается 1 раз при старте

# ───────────────────────────────────────────────────────────────
WELCOME = (
    "👋 Привет! Я AgentHelpBot.\n"
    "Этот бот создан для помощи авиат-агентам в расшифровке GDS-сегментов, "
    "маршрутов, дат, кодов и других данных.\n\n"
    "Бот пока работает абсолютно бесплатно и доступен 24/7.\n\n"
    "Просто пришлите мне текст бронирования — и я всё объясню на человеческом 😊"
)

SEG_RE = re.compile(
    r"^\s*\d+\s+"           # порядковый номер
    r"(?P<flight_num>\w{2})\s*"          # код авиакомпании
    r"(?P<number>\d+)\s+"                # номер рейса
    r"(?P<class>\w)\s+"                  # класс брони
    r"(?P<date>\d{2}[A-Z]{3})\s+"        # дата (24AUG)
    r"(?P<dow>\d)\s+"                    # день недели
    r"(?P<rout>[A-Z]{6})\s+"             # ALAFRA
    r".*?\s(?P<dep>\d{4})\s+(?P<arr>\d{4})",  # время вылета / прилёта
    re.I
)

def fmt_airport(code: str) -> str:
    data = AIRPORTS.get(code)
    if not data:
        return code.upper()
    city = data["city"]
    return f"{city} ({code.upper()})"

def fmt_airline(code: str) -> str:
    ru, en = AIRLINES.get(code.upper(), (code.upper(), code.upper()))
    return ru

def calc_duration(dep: str, arr: str) -> str:
    t1 = datetime.strptime(dep, "%H%M")
    t2 = datetime.strptime(arr, "%H%M")
    if t2 < t1:
        t2 += timedelta(days=1)
    dur = t2 - t1
    h, m = divmod(dur.seconds // 60, 60)
    return f"{h} ч {m:02d} мин"

def parse_block(block: str):
    """Вернёт список dict'ов по одному на сегмент."""
    segs = []
    for line in block.splitlines():
        m = SEG_RE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        date = dtparse.parse(gd["date"]).date()
        segs.append({
            "airline":   gd["flight_num"].upper(),
            "flight":    f"{gd['flight_num'].upper()} {gd['number']}",
            "date":      date,
            "from":      gd["rout"][:3],
            "to":        gd["rout"][3:],
            "dep":       gd["dep"],
            "arr":       gd["arr"],
            "duration":  calc_duration(gd["dep"], gd["arr"]),
        })
    return segs

def build_reply(variant_id: int, segs: list) -> str:
    if not segs:
        return ""
    first = segs[0]
    title_city = fmt_airport(segs[-1]["to"])
    lines = [f"Вариант №{variant_id} — {title_city}"]
    for s in segs:
        date_str = s["date"].strftime("%d %b").lower()
        line = (
            f"{date_str}, {s['dep'][:2]}:{s['dep'][2:]} – {s['arr'][:2]}:{s['arr'][2:]}, "
            f"{fmt_airport(s['from'])} — {fmt_airport(s['to'])}, {s['flight']}, "
            f"{fmt_airline(s['airline'])}. {s['duration']}"
        )
        lines.append(line)
    lines.append(
        "Цена: _____\n"
        "Штраф: за возврат билета: _____\n"
        "Штраф: за замену даты: _____\n"
        "Примечание: __________\n"
    )
    return "\n".join(lines)

# ───────────────────────────────────────────────────────────────
@dp.message_handler(commands=["start"])
async def send_welcome(msg: types.Message):
    await msg.answer(WELCOME, parse_mode="Markdown")

@dp.message_handler()
async def handle(msg: types.Message):
    text = msg.text.strip()
    # делим варианты по пустой строке ИЛИ смене порядкового номера «1 », «2 »…
    blocks = re.split(r"\n\s*\n", text)
    replies = []
    for idx, blk in enumerate(blocks, 1):
        segs = parse_block(blk)
        if segs:
            replies.append(build_reply(idx, segs))
    if replies:
        await msg.answer("\n\n".join(replies), parse_mode="Markdown")
    else:
        await msg.reply("Не смог понять сегменты 😕\n"
                        "Пришли мне стандартные строки бронирования.")

# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)

