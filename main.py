import asyncio
import re
import time
import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymax import MaxClient, Message

PHONE = "+79537462323"
MY_SURNAMES = "Щекетов\nОкуньков"
DELAY = 1
COOLDOWN = 1800
TARGET_CHAT_ID = -74285624063472
OWNER_USER_ID = 125743856

last_training_time = 0
last_message_id = None
last_surnames = MY_SURNAMES
edit_waiting = False

def is_training(text):
    triggers = ["Внимание", "▶️", "Место проведения", "Лед:", "ОФП:", "Направленность"]
    hits = sum(1 for t in triggers if t.lower() in text.lower())
    has_date = bool(re.search(r'\d{2}\.\d{2}\.\d{2,4}', text))
    return hits >= 3 and has_date

def control_keyboard():
    return json.dumps({
        "keyboard": [
            [{"text": "✏️ Редактировать запись"}],
            [{"text": "🗑 Удалить запись"}],
            [{"text": "📊 Статус"}]
        ],
        "resize_keyboard": True
    })

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
    global last_training_time, last_message_id, last_surnames, edit_waiting

    threading.Thread(target=run_http_server, daemon=True).start()
    await asyncio.sleep(0.5)

    client = MaxClient(phone=PHONE, work_dir="session")

    @client.on_start
    async def on_start():
        print("Клиент запущен. Ваш ID:", client.me.id)
        print(f"Мониторим чат id={TARGET_CHAT_ID}")

    @client.on_message()
    async def on_message(msg: Message):
        global last_training_time, last_message_id, last_surnames, edit_waiting

        text = msg.text
        if not text:
            return

        chat_id = msg.chat_id
        is_private = chat_id > 0

        print(f"💬 chat={chat_id} private={is_private} text={text[:80]}")

        # === ЛИЧКА ===
        if is_private and chat_id == OWNER_USER_ID:
            # Ждём новый текст после /edit
            if edit_waiting:
                edit_waiting = False
                new_text = text.strip()
                if new_text == "-":
                    if last_message_id:
                        await client.delete_message(message_id=last_message_id)
                    await client.send_message(chat_id=OWNER_USER_ID, text="✅ Запись удалена")
                    last_message_id = None
                    last_training_time = 0
                    last_surnames = MY_SURNAMES
                    return
                if last_message_id:
                    await client.edit_message(message_id=last_message_id, text=new_text)
                last_surnames = new_text
                await client.send_message(chat_id=OWNER_USER_ID, text=f"✅ Изменено:\n{new_text}")
                return

            if text == "/edit":
                if last_message_id:
                    await client.send_message(
                        chat_id=OWNER_USER_ID,
                        text=f"📝 Текущая запись:\n{last_surnames}\n\nВведите новый текст (или «-» для удаления):"
                    )
                    edit_waiting = True
                else:
                    await client.send_message(chat_id=OWNER_USER_ID, text="❌ Нет активной записи")
                return

            if text == "/delete":
                if last_message_id:
                    await client.delete_message(message_id=last_message_id)
                    await client.send_message(chat_id=OWNER_USER_ID, text="✅ Запись удалена")
                    last_message_id = None
                    last_training_time = 0
                    last_surnames = MY_SURNAMES
                else:
                    await client.send_message(chat_id=OWNER_USER_ID, text="❌ Нечего удалять")
                return

            if text == "/status":
                if last_message_id:
                    await client.send_message(
                        chat_id=OWNER_USER_ID,
                        text=f"✅ Активная запись:\n{last_surnames}\nmsg_id: {last_message_id}"
                    )
                else:
                    await client.send_message(chat_id=OWNER_USER_ID, text="❌ Нет активной записи")
                return

            if text == "/start":
                await client.send_message(
                    chat_id=OWNER_USER_ID,
                    text="Команды:\n/edit — изменить запись\n/delete — удалить запись\n/status — статус"
                )
                return

        # === ГРУППОВОЙ ЧАТ ===
        if chat_id == TARGET_CHAT_ID:
            if is_training(text):
                now = time.time()
                if now - last_training_time < COOLDOWN:
                    print("🔁 Кулдаун")
                    return
                print(f"🎯 Тренировка! Жду {DELAY} сек...")
                await asyncio.sleep(DELAY)
                last_surnames = MY_SURNAMES
                resp = await client.send_message(chat_id=TARGET_CHAT_ID, text=MY_SURNAMES)
                if resp:
                    last_message_id = resp.message_id
                    last_training_time = now
                    print(f"✅ Записан! msg_id={last_message_id}")
                    await client.send_message(
                        chat_id=OWNER_USER_ID,
                        text=f"📝 Запись:\n{MY_SURNAMES}"
                    )

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())