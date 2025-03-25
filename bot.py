import json
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Lấy token từ biến môi trường
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Hàm gọi API bên ngoài với địa chỉ ví
def fetch_metadata(wallet_address):
    url = "https://graph.cast.k3l.io/metadata/handles"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps([wallet_address])

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

    # Kiểm tra xem có phải địa chỉ ví hợp lệ không
    if message.startswith("0x") and len(message) == 42:
        await update.message.reply_text(f"🔍 Đang tra cứu địa chỉ: `{message}`", parse_mode='Markdown')

        result = fetch_metadata(message)
        result_text = json.dumps(result, indent=2, ensure_ascii=False)
        await update.message.reply_text(f"📬 Kết quả:\n```json\n{result_text}\n```", parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ Vui lòng gửi địa chỉ ví Ethereum bắt đầu bằng `0x`, dài 42 ký tự.", parse_mode='Markdown')

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()