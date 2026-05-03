import asyncio
import re
import time
import os
from aiohttp import web, ClientSession

USER_TOKEN = "An_Sx6HQ9HDiAOhWPgGMZkqz2Ppli7byIjmw4zyF4n57Wdr9_9VGU5MHKy21H1hZtb2TQLeefVDKSHSUhQEHgDTgHQllTFaF8BJ-FqhdehJYKdm_wzzysGz-YTMv-xBUDlu4Sz_bzxZaQn1ZMFebgI4W8oiYQe_3Aqrs4QNoKNkVN966Up_GnyCU8in49xsbpURbWthBp9qioEwkE1-SbJVrxbXHJhhM0Xo7QYH1c7TfPIrJkdFB2FJAb_7NyuCx1qmNV_RLJrwSyyo4bhTOlavHDs8E_VAQ3vFhR0v2QBSIjL3dhxhxORPszPk3GGEj16z4O99KoCg516J6l5qvZrqxBBu5omrp346X02odAE3TSXXIWino62q_7kVVJG2eXZ7NX8zsvvE5HWoqHNGwJOj4JsrnxUTthGRaB-k5-kSDDpO9pn6tbRQFlhzlq_nZTt6QQd1iUcE5LR71oePczx7unlAnn2zu2T6QZLmaDnwmKHcdxkf6KL4zC16dTTDXroAcUsh8iBGYeFLxNoWgtmKy71sNLju_bKhFmXQDoEkLIXq4TfdoRcj0HV6F1vZ95XHqwYG1tJgsOioyv-7MrrpZNB_0M1El0BoPlSQIotrRtjLzOU9YlfIoIgLIFmhjWuQaFyrgO-LDYE6A4ssiU0ZedEjdYaCM_RAK7RONxmgrbbHaIcpgs1Flyu58BvvWg5PQ26k"
API_BASE = "https://platform-api.max.ru"
MY_SURNAMES = "Щекетов\nОкуньков"
DELAY = 1
COOLDOWN = 1800
TARGET_CHAT_ID = -74285624063472

last_training_time = 0
_marker = None

def is_training(text: str) -> bool:
    triggers = ["Внимание", "▶️", "Место проведения", "Лед:", "ОФП:", "Направленность"]
    hits = sum(1 for t in triggers if t.lower() in text.lower())
    has_date = bool(re.search(r'\d{2}\.\d{2}\.\d{2,4}', text))
    return hits >= 3 and has_date

# ---------- Health endpoint for Alwaysdata ----------
async def health(request):
    return web.Response(text="OK")

async def run_http_server():
    port = int(os.getenv("PORT", 8101))
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/{tail:.*}", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "::", port)
    await site.start()
    print(f"Health server on [::]:{port}")

# ---------- Long-poll worker ----------
async def long_poll_worker():
    global _marker, last_training_time
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    async with ClientSession() as session:
        while True:
            try:
                params = {
                    "limit": 10,
                    "types": ["message_created"]
                }
                if _marker:
                    params["marker"] = _marker

                async with session.get(f"{API_BASE}/updates", headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _marker = data.get("marker", _marker)
                        for upd in data.get("updates", []):
                            if upd.get("update_type") != "message_created":
                                continue
                            msg = upd.get("message", {})
                            chat_id = msg.get("recipient", {}).get("chat_id")
                            if str(chat_id) != str(TARGET_CHAT_ID):
                                continue
                            text = msg.get("body", {}).get("text", "")
                            if not text:
                                continue
                            print(f"💬 {text[:80]}")

                            if is_training(text):
                                now = time.time()
                                if now - last_training_time < COOLDOWN:
                                    print("🔁 Cooldown, skip")
                                    continue
                                print(f"🎯 Training detected, waiting {DELAY}s...")
                                await asyncio.sleep(DELAY)

                                # Send message
                                send_payload = {
                                    "chat_id": int(TARGET_CHAT_ID),
                                    "text": MY_SURNAMES
                                }
                                async with session.post(
                                    f"{API_BASE}/messages",
                                    headers=headers,
                                    json=send_payload
                                ) as send_resp:
                                    if send_resp.status == 200:
                                        print("✅ Sent!")
                                        last_training_time = now
                                    else:
                                        print(f"Send error: {send_resp.status}")
                    else:
                        print(f"Poll error {resp.status}")
            except Exception as e:
                print(f"Poll exception: {e}")
                await asyncio.sleep(5)
            await asyncio.sleep(1)   # interval between polls

# ---------- Main startup ----------
async def main():
    print("Starting HTTP server...")
    await run_http_server()

    print("Starting long-poll worker...")
    await long_poll_worker()

if __name__ == "__main__":
    asyncio.run(main())