import os
import json
import re
import requests
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CODE = "SIMSADMIN123"
admins = set()

MODS_FILE = "mods.json"
VERSIONS_FILE = "versions.json"

# ===== Работа с файлами =====
def load_mods():
    with open(MODS_FILE, "r") as f:
        return json.load(f)

def save_mods(data):
    with open(MODS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_versions():
    try:
        with open(VERSIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_versions(data):
    with open(VERSIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===== Получение версии с сайта =====
def get_version(url, selector=None):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        if selector:
            el = soup.select_one(selector)
            if el:
                match = re.search(r'\d+(\.\d+)+', el.text)
                if match:
                    return match.group(0)
        return "Ошибка"
    except:
        return "Ошибка"

# ===== Меню =====
def main_menu():
    mods = load_mods()
    keyboard = [[InlineKeyboardButton(mod, callback_data=f"mod|{mod}")] for mod in mods]
    keyboard.append([InlineKeyboardButton("🔑 Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="menu")]])

def admin_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить мод", callback_data="add_mod")],
        [InlineKeyboardButton("📦 Список модов", callback_data="list_mods")],
        [InlineKeyboardButton("✏ Редактировать мод", callback_data="edit_mod")],
        [InlineKeyboardButton("⬅ Назад", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== Команды =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот отслеживания обновлений модов Sims 4.\n\nВыберите мод ниже или нажмите Админ панель:",
        reply_markup=main_menu()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Главное меню:", reply_markup=main_menu())

# ===== Обновление пользовательской версии =====
async def mod_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, mod_name = query.data.split("|")
    context.user_data["current_mod"] = mod_name
    await query.message.reply_text(f"Введите установленную версию для {mod_name}:")

async def save_installed_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_mod" in context.user_data:
        mod_name = context.user_data["current_mod"]
        version = update.message.text.strip()
        installed = context.user_data.get("installed_versions", {})
        installed[mod_name] = version
        context.user_data["installed_versions"] = installed
        context.user_data.pop("current_mod")
        await update.message.reply_text(f"✅ Версия для {mod_name} сохранена!")
    else:
        await update.message.reply_text("Введите команду через меню.")

# ===== Проверка обновлений =====
async def check_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mods = load_mods()
    versions = load_versions()
    messages = []
    buttons = []

    installed_versions = context.user_data.get("installed_versions", {})

    for mod, data in mods.items():
        last_versions = versions.get(mod, ["—"])
        prev = last_versions[-2] if len(last_versions) > 1 else "—"
        last = last_versions[-1] if last_versions else "—"

        real_version = get_version(data["url"], data.get("version_selector"))
        if real_version != "Ошибка" and real_version != last:
            if len(last_versions) == 2:
                last_versions = [last_versions[-1], real_version]
            else:
                last_versions.append(real_version)
            versions[mod] = last_versions
            save_versions(versions)
            last = real_version
            prev = last_versions[-2] if len(last_versions) > 1 else "—"

        installed = installed_versions.get(mod, "—")
        if installed != last:
            messages.append(f"🆕 {mod} обновление!\nПредпоследняя: {prev}\nПоследняя: {last}\nУстановлено: {installed}")
            buttons.append([InlineKeyboardButton(f"⬇ Скачать {mod}", url=data["url"])])
            buttons.append([InlineKeyboardButton(f"✅ Обновил {mod}", callback_data=f"updated|{mod}")])

    if not messages:
        await query.edit_message_text("✅ Все моды обновлены", reply_markup=back_button())
    else:
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="menu")])
        await query.edit_message_text("\n\n".join(messages), reply_markup=InlineKeyboardMarkup(buttons))

# ===== Callback «Обновил» =====
async def updated_mod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, mod_name = query.data.split("|")
    context.user_data["current_mod"] = mod_name
    await query.message.reply_text(f"Введите новую версию для {mod_name}:")

# ===== Админ-панель =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Введите кодовое слово:")
    context.user_data["awaiting_code"] = True

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Админ-код
    if context.user_data.get("awaiting_code"):
        if text == ADMIN_CODE:
            admins.add(user_id)
            await update.message.reply_text("✅ Доступ администратора открыт", reply_markup=admin_menu())
        else:
            await update.message.reply_text("❌ Неверный код")
        context.user_data["awaiting_code"] = False
        return

    # Сохраняем пользовательскую версию мода
    await save_installed_version(update, context)

# ===== Основной запуск =====
app = ApplicationBuilder().token(TOKEN).build()

# Команды и кнопки
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu, pattern="menu"))
app.add_handler(CallbackQueryHandler(mod_button, pattern="mod\\|"))
app.add_handler(CallbackQueryHandler(check_updates, pattern="check"))
app.add_handler(CallbackQueryHandler(updated_mod_callback, pattern="updated\\|"))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Бот запущен")
app.run_polling()
