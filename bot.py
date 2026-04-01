import os
import json
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CURSE_API_KEY = os.getenv("CURSEFORGE_API_KEY")
HEADERS = {"x-api-key": CURSE_API_KEY}

MODS_FILE = "mods.json"
VERSIONS_FILE = "versions.json"

def load_mods():
    with open(MODS_FILE, "r") as f:
        return json.load(f)

def save_versions(data):
    with open(VERSIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_versions():
    try:
        with open(VERSIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def get_latest_file_version(project_id):
    url = f"https://api.curseforge.com/v1/mods/{project_id}/files"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()
    if "data" in data and data["data"]:
        data["data"].sort(key=lambda x: x["fileDate"], reverse=True)
        latest = data["data"][0]
        return latest["fileName"]
    return None

def main_menu():
    mods = load_mods()
    keyboard = [[InlineKeyboardButton(name, callback_data=f"mod|{name}")] for name in mods]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите мод:", reply_markup=main_menu()
    )

async def mod_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, mod_name = query.data.split("|")
    context.user_data["current_mod"] = mod_name
    await query.edit_message_text(f"Введите вашу установленную версию для {mod_name}:")

async def save_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    version = update.message.text.strip()
    mod_name = context.user_data.get("current_mod")
    if not mod_name:
        await update.message.reply_text("Выберите мод через меню.")
        return
    installed = context.user_data.get("installed_versions", {})
    installed[mod_name] = version
    context.user_data["installed_versions"] = installed
    await update.message.reply_text(f"Версия «{version}» для {mod_name} сохранена!")

async def check_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mods = load_mods()
    versions = load_versions()
    installed = context.user_data.get("installed_versions", {})
    messages = []
    buttons = []
    for mod_name, data in mods.items():
        project_id = data.get("curse_project_id")
        latest_file_name = get_latest_file_version(project_id)
        if not latest_file_name:
            continue

        old_versions = versions.get(mod_name, [])
        if not old_versions or old_versions[-1] != latest_file_name:
            old_versions.append(latest_file_name)
            if len(old_versions) > 2:
                old_versions = old_versions[-2:]
            versions[mod_name] = old_versions
            save_versions(versions)

        last = old_versions[-1]
        prev = old_versions[-2] if len(old_versions) > 1 else "—"
        installed_ver = installed.get(mod_name, "—")

        if installed_ver != last:
            messages.append(
                f"{mod_name}:\n"
                f"Предпоследняя: {prev}\n"
                f"Последняя: {last}\n"
                f"Установлено: {installed_ver}"
            )
            buttons.append([InlineKeyboardButton(f"⬇ Скачать {mod_name}", url=data["download_url"])])
    if not messages:
        await query.edit_message_text("Все моды обновлены!")
    else:
        reply_text = "\n\n".join(messages)
        keyboard = buttons + [[InlineKeyboardButton("⬅ Назад", callback_data="menu")]]
        await query.edit_message_text(reply_text, reply_markup=InlineKeyboardMarkup(keyboard))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(mod_select, pattern="mod\\|"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_version))
app.add_handler(CallbackQueryHandler(check_updates, pattern="check"))
app.run_polling()
