import telebot
import re
import os
from datetime import datetime, timedelta
# Получаем токен из переменной окружения (безопасно)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_TOKEN", "YOUR_FALLBACK_TOKEN"))
def parse_segment(segment):
    pattern = r"(\d+)\s+(\w{2})\s+(\w)\s+(\d{2}\w{3})\s+(\d)\s+(\w{6})\s+\w{2}\d\s+(\d{4})\s+(\d{4})"
    match = re.search(pattern, segment.replace("\n", " ").strip())
    if not match:
        return None
    flight_num = match.group(2) + " " + match.group(1)
    date_str = match.group(4)
    from_city = match.group(6)[:3]
    to_city = match.group(6)[3:]
    departure = match.group(7)
    arrival = match.group(8)
    dep_time = datetime.strptime(departure, "%H%M")
    arr_time = datetime.strptime(arrival, "%H%M")
    if arr_time < dep_time:
        arr_time += timedelta(days=1)
    duration = arr_time - dep_time
    duration_str = f"{duration.seconds // 3600} ч {(duration.seconds // 60) % 60} мин"
    return {
        "flight": flight_num,
        "date": date_str,
        "from": from_city,
        "to": to_city,
        "departure": dep_time.strftime("%H:%M"),
        "arrival": arr_time.strftime("%H:%M"),
        "duration": duration_str,
        "airline": match.group(2)
    }
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.replace("\n", " ")
    segments = re.findall(r"\d+\s+\w{2}\s+\w\s+\d{2}\w{3}\s+\d\s+\w{6}\s+\w{2}\d\s+\d{4}\s+\d{4}", text)
    responses = []
    for idx, segment in enumerate(segments):
        parsed = parse_segment(segment)
        if parsed:
    response = f"Вариант {idx + 1} - {parsed['to']}\n"
    response += f"Туда: {parsed['date']}, {parsed['departure']} – {parsed['arrival']}, "
    response += f"{parsed['from']} → {parsed['to']}, {parsed['flight']}, {parsed['airline']}. "
    response += f"В пути {parsed['duration']}\n"
    response += "⬅️ Обратно: (указать вручную)\n\n"
    response += "Цена: ________ тенге\n"
    response += "Багаж: Включён / Только ручная кладь\n"
    response += "Возврат билета: Штраф ___ USD / Без штрафа\n"
    response += "Замена даты: Штраф ___ USD / Без штрафа\n"
    response += "Примечание: __________________________\n"
    responses.append(response)
