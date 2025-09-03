import json
import os
import requests
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Call appropriate API
def fetch_metadata(data_list, mode):
    endpoints = {
        "wallet": "https://graph.cast.k3l.io/metadata/handles",
        "username": "https://graph.cast.k3l.io/metadata/addresses/handles",
        "fid": "https://graph.cast.k3l.io/metadata/addresses/fids"
    }

    url = endpoints.get(mode)
    if not url:
        return {"error": "Invalid data type."}

    headers = {'Content-Type': 'application/json'}
    data = json.dumps(data_list)

    print(f"\n🔗 POST to: {url}")
    print(f"📤 Payload:\n{data}\n")

    try:
        response = requests.post(url, headers=headers, data=data)
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response Preview: {response.text[:300]}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"error": "Exception during API call", "detail": str(e)}

def fmt_pre(text: str) -> str:
    # Gửi dưới dạng HTML để copy dễ, tránh cần escape MarkdownV2
    # Lưu ý: Không chèn chuỗi '</code>' trong text
    safe = text.replace("</code>", "</c0de>")  # đề phòng hiếm gặp
    return f"<pre><code>{safe}</code></pre>"

# Handle Telegram messages
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
            usernames.append(text.lower())  # chuyển username sang chữ thường
        else:
            wallets.append(text.lower())    # chuyển wallet sang chữ thường

    # --- Handle FID ---
    if fids:
        if len(fids) > 1:
            await update.message.reply_text("⚠️ Please query **only 1 FID at a time**.")
        else:
            fid = fids[0]
            await update.message.reply_text(f"🔍 Looking up FID: {fid}", parse_mode='Markdown')
            result = fetch_metadata([fid], "fid")

            first_entry = result.get("result", [{}])[0]
            fname = first_entry.get("fname", "N/A")
            username = first_entry.get("username", "N/A")

            all_addresses = {entry.get("address") for entry in result.get("result", []) if entry.get("address")}
            addresses_text = "\n".join(f"`{addr}`" for addr in all_addresses) if all_addresses else "None found"

            await update.message.reply_text(
                f"📬 FID `{fid}` details:\n"
                f"- fname: `{fname}`\n"
                f"- username: `{username}`\n"
                f"- addresses:\n{addresses_text}",
                parse_mode='Markdown'
            )

    # --- Handle Username ---
    if usernames:
        if len(usernames) > 1:
            await update.message.reply_text("⚠️ Please query **only 1 ENS username at a time**.")
        else:
            username = usernames[0]
            await update.message.reply_text(f"🔍 Looking up username: {username}", parse_mode='Markdown')
            result = fetch_metadata([username], "username")

            first_entry = result.get("result", [{}])[0]
            fname = first_entry.get("fname", "N/A")
            fid = first_entry.get("fid", "N/A")

            all_addresses = {entry.get("address") for entry in result.get("result", []) if entry.get("address")}
            addresses_text = "\n".join(f"`{addr}`" for addr in all_addresses) if all_addresses else "None found"

            await update.message.reply_text(
                f"📬 Username `{username}` details:\n"
                f"- fname: `{fname}`\n"
                f"- fid: `{fid}`\n"
                f"- addresses:\n{addresses_text}",
                parse_mode='Markdown'
            )

    # --- Handle Wallets (UPDATED: luôn format từng dòng + URL username) ---
    if wallets:
        await update.message.reply_text(f"🔍 Looking up {len(wallets)} wallet address(es)...", parse_mode='Markdown')
        result_wallet = fetch_metadata(wallets, "wallet")

        try:
            entries = result_wallet.get("result", [])
            if isinstance(entries, list):
                # Dedupe bằng (address, fid, username, fname)
                seen = set()
                blocks = []
                for item in entries:
                    address = item.get("address", "N/A")
                    fname = item.get("fname", "N/A")
                    username_raw = item.get("username", "")
                    fid_val = item.get("fid", "N/A")

                    # username -> URL
                    username_display = f"https://farcaster.xyz/{username_raw}" if username_raw else "N/A"

                    key = (address, str(fid_val), username_display, fname)
                    if key in seen:
                        continue
                    seen.add(key)

                    block = (
                        f"address: {address}\n"
                        f"fname: {fname}\n"
                        f"username: {username_display}\n"
                        f"fid: {fid_val}"
                    )
                    blocks.append(block)

                # Nếu không có block (kết quả rỗng thật sự)
                if not blocks:
                    await update.message.reply_text("📬 Wallet result: (no records found)")
                else:
                    formatted = "\n\n".join(blocks)

                    # Nếu quá dài, đính kèm file TXT (vẫn là dạng dòng-dễ-copy)
                    if len(formatted) > 3500:
                        buffer = BytesIO()
                        buffer.write(formatted.encode("utf-8"))
                        buffer.seek(0)
                        await update.message.reply_document(
                            document=buffer,
                            filename="wallet_result.txt",
                            caption="📬 Wallet result (attached file)"
                        )
                    else:
                        # Gửi dạng <pre><code> để copy mượt, không dính escape Markdown
                        await update.message.reply_text(
                            f"📬 Wallet result:\n{fmt_pre(formatted)}",
                            parse_mode="HTML"
                        )
            else:
                # result_wallet["result"] không phải list -> fallback JSON
                result_text = json.dumps(result_wallet, indent=2, ensure_ascii=False)
                if len(result_text) > 3500:
                    buffer = BytesIO()
                    buffer.write(result_text.encode("utf-8"))
                    buffer.seek(0)
                    await update.message.reply_document(
                        document=buffer,
                        filename="wallet_result.json",
                        caption="📬 Wallet result (attached file)"
                    )
                else:
                    await update.message.reply_text(
                        f"📬 Wallet result:\n{fmt_pre(result_text)}",
                        parse_mode="HTML"
                    )

        except Exception as e:
            # Fallback an toàn: trả JSON (đề phòng lỗi format hiếm gặp)
            try:
                result_text = json.dumps(result_wallet, indent=2, ensure_ascii=False)
                if len(result_text) > 3500:
                    buffer = BytesIO()
                    buffer.write(result_text.encode("utf-8"))
                    buffer.seek(0)
                    await update.message.reply_document(
                        document=buffer,
                        filename="wallet_result.json",
                        caption="📬 Wallet result (attached file)"
                    )
                else:
                    await update.message.reply_text(
                        f"📬 Wallet result:\n{fmt_pre(result_text)}",
                        parse_mode="HTML"
                    )
            except Exception as e2:
                await update.message.reply_text(f"⚠️ Error while parsing wallet response.\n{str(e)}\n{str(e2)}")

    if not fids and not usernames and not wallets:
        await update.message.reply_text("⚠️ No valid input detected.")

# Run bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("🤖 Bot is running!")
    app.run_polling()