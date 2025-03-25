import json
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Gọi API tương ứng
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

    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Lỗi API: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# Phân loại & xử lý dữ liệu
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
            fids.append(int(text))  # chuyển sang số
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

    # Gửi kết quả từng phần
    for label, result in responses:
        result_text = json.dumps(result, indent=2, ensure_ascii=False)
        await update.message.reply_text(f"{label}\n```json\n{result_text}\n```", parse_mode='Markdown')

    if not fids and not usernames and not wallets:
        await update.message.reply_text("⚠️ Không phát hiện dữ liệu hợp lệ.")

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()