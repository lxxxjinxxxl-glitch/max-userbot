import asyncio
import re
import time
from pymax import MaxClient, Message

PHONE = "+79537462323"
MY_SURNAMES = "Щекетов\nОкуньков"
DELAY = 1
COOLDOWN = 1800
TARGET_CHAT_ID = -74285624063472

last_training_time = 0

def is_training(text):
    triggers = ["Внимание", "▶️", "Место проведения", "Лед:", "ОФП:", "Направленность"]
    hits = sum(1 for t in triggers if t.lower() in text.lower())
    has_date = bool(re.search(r'\d{2}\.\d{2}\.\d{2,4}', text))
    return hits >= 3 and has_date

async def main():
    global last_training_time

    client = MaxClient(phone=PHONE, work_dir="session")

    @client.on_start
    async def on_start():
        print("Клиент запущен. Ваш ID:", client.me.id)
        print(f"Мониторим чат id={TARGET_CHAT_ID}")

    @client.on_message()
    async def on_message(msg: Message):
        global last_training_time

        # Фильтруем вручную
        if msg.chat_id != TARGET_CHAT_ID:
            return

        text = msg.text
        if not text:
            return

        print(f"💬 {text[:80]}")

        if is_training(text):
            now = time.time()
            if now - last_training_time < COOLDOWN:
                print("🔁 Кулдаун")
                return

            print(f"🎯 Тренировка! Жду {DELAY} сек...")
            await asyncio.sleep(DELAY)
            await client.send_message(chat_id=TARGET_CHAT_ID, text=MY_SURNAMES)
            print("✅ Записан!")
            last_training_time = now

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())