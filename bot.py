import telebot
import os
from telebot.types import Message
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
BOT_OWNER = int(os.getenv("BOT_OWNER"))
bot = telebot.TeleBot(TOKEN)

current_group = None
allowed_links = set()
user_warns = {}

# -------------------------
# OWNER CHECK
# -------------------------
def is_owner(uid):
    return uid == BOT_OWNER

# -------------------------
# ADMIN CHECK (group admin)
# -------------------------
def is_admin(user_id, chat_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# -------------------------
# /setgroup (OWNER ONLY)
# -------------------------
@bot.message_handler(commands=['setgroup'])
def set_group(message):
    global current_group
    if not is_owner(message.from_user.id):
        return

    try:
        gid = int(message.text.split()[1])
        current_group = gid
        bot.reply_to(message, f"✔ Bot will work only in group: `{gid}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Usage: /setgroup <group_id>")


# -------------------------
# /addlink
# -------------------------
@bot.message_handler(commands=['addlink'])
def add_link(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    
    try:
        link = message.text.split()[1]
        allowed_links.add(link)
        bot.reply_to(message, "✔ Link added to allowed list.")
    except:
        bot.reply_to(message, "Usage: /addlink <url>")


# -------------------------
# /removelink
# -------------------------
@bot.message_handler(commands=['removelink'])
def remove_link(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return

    try:
        link = message.text.split()[1]
        allowed_links.discard(link)
        bot.reply_to(message, "✔ Link removed.")
    except:
        bot.reply_to(message, "Usage: /removelink <url>")


# -------------------------
# /allowedlinks
# -------------------------
@bot.message_handler(commands=['allowedlinks'])
def show_links(message):
    if not allowed_links:
        bot.reply_to(message, "No allowed links saved.")
    else:
        txt = "\n".join(list(allowed_links))
        bot.reply_to(message, f"Allowed Links:\n{txt}")


# -------------------------
# /id
# -------------------------
@bot.message_handler(commands=['id'])
def get_uid(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    try:
        username = message.text.split()[1].replace("@", "")
        user = bot.get_chat(username)
        bot.reply_to(message, f"User ID: `{user.id}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Username not found.")


# -------------------------
# BAN / UNBAN / KICK
# -------------------------
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    
    try:
        target = message.text.split()[1]
        bot.ban_chat_member(message.chat.id, target)
        bot.reply_to(message, "✔ User banned.")
    except:
        bot.reply_to(message, "Usage: /ban <id or @username>")


@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    
    try:
        target = message.text.split()[1]
        bot.unban_chat_member(message.chat.id, target)
        bot.reply_to(message, "✔ User unbanned.")
    except:
        bot.reply_to(message, "Usage: /unban <id>")


@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    
    try:
        target = message.text.split()[1]
        bot.ban_chat_member(message.chat.id, target)
        bot.unban_chat_member(message.chat.id, target)
        bot.reply_to(message, "✔ User kicked.")
    except:
        bot.reply_to(message, "Usage: /kick <id>")


# -------------------------
# WARN SYSTEM
# -------------------------
def warn_user(chat_id, user_id):
    if user_id not in user_warns:
        user_warns[user_id] = 0
    
    user_warns[user_id] += 1
    w = user_warns[user_id]

    bot.send_message(chat_id, f"⚠ Warning {w}/3")

    if w >= 3:
        bot.ban_chat_member(chat_id, user_id)
        bot.send_message(chat_id, "🚫 User banned (3 warnings)")
        user_warns[user_id] = 0


# -------------------------
# PRIVATE CHAT → OWNER ONLY
# -------------------------
@bot.message_handler(func=lambda m: m.chat.type == "private")
def inbox(message):

    # If message from owner → allow
    if is_owner(message.from_user.id):
        bot.reply_to(message, "✔ Owner recognized. Inbox active.")
        return

    # Otherwise forward to owner silently
    bot.forward_message(BOT_OWNER, message.chat.id, message.message_id)


# -------------------------
# AUTO MODERATION
# -------------------------
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def moderation(message):

    # group lock
    if current_group and message.chat.id != current_group:
        return

    # admin ignore
    if is_admin(message.from_user.id, message.chat.id):
        return

    uid = message.from_user.id

    # forwarded message
    if message.forward_from or message.forward_from_chat:
        bot.delete_message(message.chat.id, message.message_id)
        warn_user(message.chat.id, uid)
        return

    # text limit 20 words
    if message.content_type == "text":
        if len(message.text.split()) > 20:
            bot.delete_message(message.chat.id, message.message_id)
            warn_user(message.chat.id, uid)
            return

        # link detection
        if "http://" in message.text or "https://" in message.text or "t.me/" in message.text:
            for x in allowed_links:
                if x in message.text:
                    return

            bot.delete_message(message.chat.id, message.message_id)
            warn_user(message.chat.id, uid)
            return

    # photo/video/document delete
    if message.content_type in ["photo", "video", "document"]:
        bot.delete_message(message.chat.id, message.message_id)
        warn_user(message.chat.id, uid)


print("Bot running...")
bot.polling(none_stop=True)
