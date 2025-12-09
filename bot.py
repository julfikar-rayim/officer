import telebot
from telebot.types import Message

TOKEN = "YOUR_TOKEN"
bot = telebot.TeleBot(TOKEN)

# Store group
current_group = None

# Allowed links
allowed_links = set()

# Warning counter
user_warns = {}

# Admin inbox ID (will be stored after admin sends /start in bot inbox)
bot_admin_id = None


# ---------------------------
# ADMIN CHECK
# ---------------------------
def is_admin(user_id, chat_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------------------
# SET GROUP (command)
# ---------------------------
@bot.message_handler(commands=['setgroup'])
def set_group(message):
    global current_group
    if not is_admin(message.from_user.id, message.chat.id):
        return
    
    try:
        gid = int(message.text.split()[1])
        current_group = gid
        bot.reply_to(message, f"✔ Bot is now active only in group: `{gid}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Usage: /setgroup <group_id>")


# ---------------------------
# REGISTER ADMIN FOR BOT INBOX
# ---------------------------
@bot.message_handler(commands=['start'])
def register_admin(message):
    global bot_admin_id
    if message.chat.type == "private":
        bot_admin_id = message.from_user.id
        bot.reply_to(message, "✔ You are now registered as bot admin.")
        

# ---------------------------
# ADD ALLOWED LINK
# ---------------------------
@bot.message_handler(commands=['addlink'])
def add_link(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return

    try:
        link = message.text.split()[1]
        allowed_links.add(link)
        bot.reply_to(message, f"✔ Allowed link added:\n{link}")
    except:
        bot.reply_to(message, "Usage: /addlink <url>")


# ---------------------------
# REMOVE LINK
# ---------------------------
@bot.message_handler(commands=['removelink'])
def remove_link(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return

    try:
        link = message.text.split()[1]
        allowed_links.discard(link)
        bot.reply_to(message, f"✔ Removed allowed link:\n{link}")
    except:
        bot.reply_to(message, "Usage: /removelink <url>")


# ---------------------------
# SHOW ALLOWED LINKS
# ---------------------------
@bot.message_handler(commands=['allowedlinks'])
def show_links(message):
    if not allowed_links:
        bot.reply_to(message, "No allowed links.")
    else:
        txt = "\n".join(list(allowed_links))
        bot.reply_to(message, f"Allowed links:\n{txt}")


# ---------------------------
# USER ID FROM USERNAME
# ---------------------------
@bot.message_handler(commands=['id'])
def get_id(message):
    try:
        username = message.text.split()[1].replace("@", "")
        user = bot.get_chat(username)
        bot.reply_to(message, f"User ID: `{user.id}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Could not find username.")


# ---------------------------
# BAN / UNBAN / KICK
# ---------------------------
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    try:
        target = message.text.split()[1]
        bot.ban_chat_member(message.chat.id, target)
        bot.reply_to(message, f"✔ Banned: {target}")
    except:
        bot.reply_to(message, "Usage: /ban <id or @username>")


@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.from_user.id, message.chat.id): 
        return
    try:
        target = message.text.split()[1]
        bot.unban_chat_member(message.chat.id, target)
        bot.reply_to(message, f"✔ Unbanned: {target}")
    except:
        bot.reply_to(message, "Usage: /unban <id or @username>")


@bot.message_handler(commands=['kick'])
def kick(message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    try:
        target = message.text.split()[1]
        bot.ban_chat_member(message.chat.id, target)
        bot.unban_chat_member(message.chat.id, target)
        bot.reply_to(message, f"✔ Kicked: {target}")
    except:
        bot.reply_to(message, "Usage: /kick <id or @username>")


# ---------------------------
# AUTO WARN SYSTEM
# ---------------------------
def warn_user(chat_id, user_id):
    if user_id not in user_warns:
        user_warns[user_id] = 0
    user_warns[user_id] += 1

    warns = user_warns[user_id]

    bot.send_message(chat_id, f"⚠ Warning {warns}/3")

    if warns >= 3:
        bot.ban_chat_member(chat_id, user_id)
        bot.send_message(chat_id, "🚫 User has been banned for repeated violations.")
        user_warns[user_id] = 0  # reset


# ---------------------------
# AUTO MODERATION
# ---------------------------
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'forward'])
def auto_moderation(message):

    # BOT INBOX HANDLING
    if message.chat.type == "private":

        if message.from_user.id != bot_admin_id:
            if bot_admin_id:
                bot.forward_message(bot_admin_id, message.chat.id, message.message_id)
            return
        
        return  # admin sending → no restrictions


    # GROUP FILTERING
    if current_group and message.chat.id != current_group:
        return

    user_id = message.from_user.id

    if is_admin(user_id, message.chat.id):
        return

    # FORWARDED MESSAGE CHECK
    if message.forward_from or message.forward_from_chat:
        bot.delete_message(message.chat.id, message.message_id)
        warn_user(message.chat.id, user_id)
        return

    # TEXT LIMIT (20 words)
    if message.content_type == "text":
        words = message.text.split()
        if len(words) > 20:
            bot.delete_message(message.chat.id, message.message_id)
            warn_user(message.chat.id, user_id)
            return

        # Link detection
        if "http://" in message.text or "https://" in message.text or "t.me/" in message.text:
            for link in allowed_links:
                if link in message.text:
                    return

            bot.delete_message(message.chat.id, message.message_id)
            warn_user(message.chat.id, user_id)
            return

    # PHOTO
    if message.content_type == "photo":
        bot.delete_message(message.chat.id, message.message_id)
        warn_user(message.chat.id, user_id)

    # VIDEO
    if message.content_type == "video":
        bot.delete_message(message.chat.id, message.message_id)
        warn_user(message.chat.id, user_id)


print("Bot Running...")
bot.polling(none_stop=True)
