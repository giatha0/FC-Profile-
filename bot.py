import json
import os
import requests
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Gọi API theo loại
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
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Nội dung: {response.text[:300]}")
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
            fids.append(int(text))
        elif len(text) <= 20:
            usernames.append(text)
        else:
            wallets.append(text)

    # --- XỬ LÝ FID ---
    if fids:
        if len(fids) > 1:
            await update.message.reply_text("⚠️ Chỉ hỗ trợ tra cứu **1 FID mỗi lần**. Vui lòng gửi từng FID riêng lẻ.")
        else:
            fid = fids[0]
            await update.message.reply_text(f"🔍 Đang tra cứu FID: {fid}", parse_mode='Markdown')
            result = fetch_metadata([fid], "fid")
            first_entry = result.get("result", [{}])[0]
            fname = first_entry.get("fname", "Không có")
            username = first_entry.get("username", "Không có")

            await update.message.reply_text(
                f"📬 Kết quả FID `{fid}`:\n"
                f"- fname: `{fname}`\n"
                f"- username: `{username}`",
                parse_mode='Markdown'
            )

    # --- XỬ LÝ USERNAME ---
    if usernames:
        if len(usernames) > 1:
            await update.message.reply_text("⚠️ Chỉ hỗ trợ tra cứu **1 username ENS mỗi lần**. Vui lòng gửi riêng từng username.")
        else:
            username = usernames[0]
            await update.message.reply_text(f"🔍 Đang tra cứu username: {username}", parse_mode='Markdown')
            result = fetch_metadata([username], "username")

            first_entry = result.get("result", [{}])[0]
            fname = first_entry.get("fname", "Không có")
            fid = first_entry.get("fid", "Không có")

            all_addresses = {entry.get("address") for entry in result.get("result", []) if entry.get("address")}
            addresses_text = "\n".join(f"`{addr}`" for addr in all_addresses) if all_addresses else "Không có"

            await update.message.reply_text(
                f"📬 Kết quả `{username}`:\n"
                f"- fname: `{fname}`\n"
                f"- fid: `{fid}`\n"
                f"- addresses:\n{addresses_text}",
                parse_mode='Markdown'
            )


    # --- XỬ LÝ ĐỊA CHỈ VÍ ---
    if wallets:
        await update.message.reply_text(f"🔍 Đang tra cứu {len(wallets)} địa chỉ ví...", parse_mode='Markdown')
        result_wallet = fetch_metadata(wallets, "wallet")
        try:
            result_text = json.dumps(result_wallet, indent=2, ensure_ascii=False)
            if len(result_text) > 3500:
                buffer = BytesIO()
                buffer.write(result_text.encode("utf-8"))
                buffer.seek(0)
                await update.message.reply_document(
                    document=buffer,
                    filename="wallet_result.json",
                    caption="📬 Kết quả ví (đính kèm file)"
                )
            else:
                await update.message.reply_text(f"📬 Kết quả ví:\n```json\n{result_text}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"⚠️ Lỗi khi xử lý JSON ví.\n{str(e)}")

    if not fids and not usernames and not wallets:
        await update.message.reply_text("⚠️ Không phát hiện dữ liệu hợp lệ.")

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot đã khởi động!")
    app.run_polling()