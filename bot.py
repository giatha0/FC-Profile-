import json
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Gửi POST request theo loại dữ liệu
def fetch_metadata(data_list, mode):
    endpoints = {
        "wallet": "https://graph.cast.k3l.io/metadata/handles",
        "username": "https://graph.cast.k3l.io/metadata/addresses/handles",
        "fid": "https://graph.cast.k3l.io/metadata/addresses/fids"
    }

    url = endpoints.get(mode)
    if not url:
        return {"error": "Loại dữ liệu không hợp lệ"}

    headers = {'Content-Type': 'application/json'}
    data = json.dumps(data_list)

    print(f"\n🔗 POST tới: {url}")
    print(f"📤 Payload:\n{data}\n")

    try:
        response = requests.post(url, headers=headers, data=data)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response content: {response.text[:300]}")
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Lỗi API: {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"error": "Exception khi gọi API", "detail": str(e)}

# Xử lý tin nhắn
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    lines = message.splitlines()

    fids = []
    usernames = []
    wallets = []

    for line in lines:
        text = line.strip()
        if not text:
            continue

        if text.isdigit() and len(text) <= 10:
            fids.append(int(text))  # quan trọng: giữ FID là số nguyên
        elif len(text) <= 20:
            usernames.append(text)
        else:
            wallets.append(text)

    responses = []

    if wallets:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(wallets)} địa chỉ ví...", parse_mode='Markdown')
        result_wallet = fetch_metadata(wallets, "wallet")
        responses.append(("📬 Kết quả địa chỉ ví:", result_wallet))

    if usernames:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(usernames)} ENS username...", parse_mode='Markdown')
        result_user = fetch_metadata(usernames, "username")
        responses.append(("📬 Kết quả username:", result_user))

    if fids:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(fids)} FID...", parse_mode='Markdown')
        result_fid = fetch_metadata(fids, "fid")
        responses.append(("📬 Kết quả FID:", result_fid))

    for label, result in responses:
        try:
            result_text = json.dumps(result, indent=2, ensure_ascii=False)
            await update.message.reply_text(f"{label}\n```json\n{result_text}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"{label}\n⚠️ Gặp lỗi khi xử lý kết quả.\n{str(e)}")

    if not fids and not usernames and not wallets:
        await update.message.reply_text("⚠️ Không phát hiện dữ liệu hợp lệ.")

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()