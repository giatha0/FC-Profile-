import json
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Lấy token bot từ biến môi trường
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Hàm gửi POST request đến API phù hợp
def fetch_metadata(data_list, mode="wallet"):
    if mode == "wallet":
        url = "https://graph.cast.k3l.io/metadata/handles"
    elif mode == "username":
        url = "https://graph.cast.k3l.io/metadata/addresses/handles"
    else:
        return {"error": "Chế độ không hợp lệ"}

    headers = {'Content-Type': 'application/json'}
    data = json.dumps(data_list)

    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Lỗi từ API: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# Hàm xử lý tin nhắn
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    lines = message.splitlines()

    # Phân loại dựa vào độ dài dòng
    wallet_addresses = [line.strip() for line in lines if len(line.strip()) > 20]
    usernames = [line.strip() for line in lines if 0 < len(line.strip()) <= 20]

    responses = []

    if wallet_addresses:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(wallet_addresses)} địa chỉ ví...", parse_mode='Markdown')
        result_wallet = fetch_metadata(wallet_addresses, mode="wallet")
        responses.append(("📬 Kết quả địa chỉ ví:", result_wallet))

    if usernames:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(usernames)} username ENS...", parse_mode='Markdown')
        result_usernames = fetch_metadata(usernames, mode="username")
        responses.append(("📬 Kết quả username:", result_usernames))

    # Trả kết quả
    for label, result in responses:
        result_text = json.dumps(result, indent=2, ensure_ascii=False)
        await update.message.reply_text(f"{label}\n```json\n{result_text}\n```", parse_mode='Markdown')

    if not wallet_addresses and not usernames:
        await update.message.reply_text("⚠️ Không phát hiện dữ liệu hợp lệ.")

# Chạy bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()