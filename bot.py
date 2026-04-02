
import os
import json
import re
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

MODS_FILE = "mods.json"
VERSIONS_FILE = "versions.json"

def load_mods():
    with open(MODS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_versions():
    if not os.path.exists(VERSIONS_FILE):
        return {}
    with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_versions(data):
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_boosty_version(rss_url, regex):
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return None, None

    post = feed.entries[0]
    title = post.title
    link = post.link

    match = re.search(regex, title, re.IGNORECASE)
    version = match.group(0) if match else title

    return version, link

def main_menu():
    mods = load_mods()
    keyboard = []

    for mod in mods:
        keyboard.append([InlineKeyboardButton(mod, callback_data=f"mod|{mod}")])

    keyboard.append([InlineKeyboardButton("🔎 Проверить обновления", callback_data="check")])

    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите мод или проверьте обновления:",
        reply_markup=main_menu()
    )

async def select_mod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, mod = query.data.split("|")
    context.user_data["current_mod"] = mod

    await query.edit_message_text(
        f"Введите установленную версию для мода:\n{mod}"
    )

async def save_user_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mod = context.user_data.get("current_mod")
    if not mod:
        return

    version = update.message.text.strip()

    if "installed_versions" not in context.user_data:
        context.user_data["installed_versions"] = {}

    context.user_data["installed_versions"][mod] = version

    await update.message.reply_text(
        f"Версия {version} для {mod} сохранена.",
        reply_markup=main_menu()
    )

async def check_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mods = load_mods()
    versions = load_versions()

    installed = context.user_data.get("installed_versions", {})

    messages = []

    for mod, data in mods.items():
        version, link = get_boosty_version(data["rss"], data["regex"])

        if not version:
            continue

        history = versions.get(mod, [])

        if not history or history[-1] != version:
            history.append(version)
            history = history[-2:]
            versions[mod] = history

        last = history[-1]
        prev = history[-2] if len(history) > 1 else "—"

        user_ver = installed.get(mod, "—")

        if user_ver != last:
            messages.append(
                f"🔥 Новый патч!\n"
                f"{mod}\n"
                f"Предыдущая версия: {prev}\n"
                f"Последняя версия: {last}\n"
                f"Установлено у вас: {user_ver}\n"
                f"Скачать: {link}"
            )

    save_versions(versions)

    if not messages:
        await query.edit_message_text("✅ Все моды обновлены!", reply_markup=main_menu())
    else:
        await query.edit_message_text(
            "\n\n".join(messages),
            reply_markup=main_menu()
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(select_mod, pattern="mod\|"))
    app.add_handler(CallbackQueryHandler(check_updates, pattern="check"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_user_version))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
