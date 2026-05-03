import asyncio
import re
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymax import MaxClient, Message

PHONE = "+79537462323"
MY_SURNAMES = "Щекетов\nОкуньков"
DELAY = 0          # Не используется, но оставим для совместимости
COOLDOWN = 900     # 15 минут
TARGET_CHAT_ID = -72523834161885

last_training_time = 0

def is_training(text):
    triggers = ["Внимание", "▶️", "Место проведения", "Лед:", "ОФП:", "Направленность"]
    hits = sum(1 for t in triggers if t.lower() in text.lower())
    has_date = bool(re.search(r'\d{2}\.\d{2}\.\d{2,4}', text))
    return hits >= 3 and has_date

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.getenv("PORT", 8101))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"HTTP health server on 0.0.0.0:{port}")
    server.serve_forever()

async def main():
    global last_training_time

    threading.Thread(target=run_http_server, daemon=True).start()
    await asyncio.sleep(0.5)

    client = MaxClient(phone=PHONE, work_dir="session")

    @client.on_start
    async def on_start():
        print("Клиент запущен. Ваш ID:", client.me.id)
        print(f"Мониторим чат id={TARGET_CHAT_ID}")

    @client.on_message()
    async def on_message(msg: Message):
        global last_training_time

        chat_id = msg.chat_id
        if chat_id != TARGET_CHAT_ID:
            return

        text = msg.text
        if not text:
            return

        if is_training(text):
            now = time.time()
            if now - last_training_time < COOLDOWN:
                # Полная тишина — ни логов, ни записи
                return

            print(f"💬 {text[:80]}")
            print(f"🎯 Тренировка! Отправляю...")
            await client.send_message(chat_id=TARGET_CHAT_ID, text=MY_SURNAMES)
            print("✅ Записан!")
            last_training_time = now

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())