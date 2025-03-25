import json
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Lấy token bot từ biến môi trường
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Gửi danh sách địa chỉ ví tới API
def fetch_metadata(address_list):
    url = "https://graph.cast.k3l.io/metadata/handles"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(address_list)

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

    # Tách dòng và lọc địa chỉ ví hợp lệ
    lines = message.splitlines()
    wallet_addresses = [line.strip() for line in lines if line.strip().startswith("0x") and len(line.strip()) == 42]

    if not wallet_addresses:
        await update.message.reply_text("⚠️ Không tìm thấy địa chỉ ví hợp lệ (bắt đầu bằng 0x, dài 42 ký tự).")
        return

    await update.message.reply_text(f"🔍 Đang truy vấn {len(wallet_addresses)} địa chỉ...", parse_mode='Markdown')

    result = fetch_metadata(wallet_addresses)
    result_text = json.dumps(result, indent=2, ensure_ascii=False)
    
    # Trả kết quả về group
    await update.message.reply_text(f"📬 Kết quả:\n```json\n{result_text}\n```", parse_mode='Markdown')

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()