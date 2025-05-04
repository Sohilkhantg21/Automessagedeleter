import asyncio
import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

app = Client("AutoDeleterBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

SETTINGS_FILE = "delete_settings.json"
USERS_FILE = "users.json"

# Init files
for file in [SETTINGS_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if "settings" in file else [], f)

def get_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

def add_user(user_id):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        return True
    return False

@app.on_message(filters.private & filters.incoming)
async def on_private(_, message: Message):
    is_new = add_user(message.from_user.id)
    if is_new:
        await app.send_message(ADMIN_ID, f"New user joined: [{message.from_user.first_name}](tg://user?id={message.from_user.id})")

    await message.reply("Welcome to Auto Delete Bot!\nAdd me to a group and use /setdelete to start deleting messages on a timer.")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(_, message: Message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast it to all users.")
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    sent, failed = 0, 0
    for user in users:
        try:
            await app.send_message(user, message.reply_to_message.text)
            sent += 1
        except:
            failed += 1
    await message.reply(f"Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}")

@app.on_message(filters.command("setdelete") & filters.group)
async def set_delete_timer(_, message: Message):
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        return await message.reply("Only admins can use this command.")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("5s", callback_data="del_5"),
         InlineKeyboardButton("10s", callback_data="del_10"),
         InlineKeyboardButton("30s", callback_data="del_30")],
        [InlineKeyboardButton("1m", callback_data="del_60"),
         InlineKeyboardButton("5m", callback_data="del_300"),
         InlineKeyboardButton("10m", callback_data="del_600")],
        [InlineKeyboardButton("Turn Off", callback_data="del_off")]
    ])
    await message.reply("Choose a delete timer:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("del_"))
async def callback_timer(_, query):
    chat_id = query.message.chat.id
    timer = query.data.split("_")[1]
    settings = get_settings()

    if timer == "off":
        settings.pop(str(chat_id), None)
        await query.message.edit("Auto-delete disabled.")
    else:
        settings[str(chat_id)] = int(timer)
        await query.message.edit(f"Auto-delete set to {timer} seconds.")

    save_settings(settings)

@app.on_message(filters.group & ~filters.service)
async def auto_delete(_, message: Message):
    settings = get_settings()
    timer = settings.get(str(message.chat.id))
    if timer:
        await asyncio.sleep(timer)
        try:
            await message.delete()
        except:
            pass

print("Bot started.")
app.run()
