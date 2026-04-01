import os
import json
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
def get_version(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        return soup.title.text.strip()
    except:
        return "Ошибка"

# ===== Меню =====
def main_menu():
    keyboard = [
        [InlineKeyboardButton("🔎 Проверить обновления", callback_data="check")],
        [InlineKeyboardButton("📦 Список модов", callback_data="mods")],
        [InlineKeyboardButton("🔑 Админ панель", callback_data="admin")]
    ]
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
        "Бот отслеживания обновлений модов Sims 4\n\n"
        "Сначала укажите версии модов, которые установлены у вас.",
        reply_markup=main_menu()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Главное меню", reply_markup=main_menu())

# ===== Список модов с кнопкой «Обновил» =====
async def mods_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mods = load_mods()
    versions = load_versions()
    text = "📦 Отслеживаемые моды:\n\n"
    keyboard = []
    for mod in mods:
        last_versions = versions.get(mod, ["—"])
        prev = last_versions[-2] if len(last_versions) > 1 else "—"
        last = last_versions[-1] if last_versions else "—"
        installed = context.user_data.get("installed_versions", {}).get(mod, "—")
        text += f"• {mod} | Предпоследняя: {prev}, Последняя: {last}, Установлено: {installed}\n"
        keyboard.append([InlineKeyboardButton(f"✅ Обновил {mod}", callback_data=f"updated|{mod}")])
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Проверка обновлений для пользователя =====
def check_updates_for_user(user_data):
    mods = load_mods()
    versions = load_versions()
    messages = []
    buttons = []

    installed_versions = user_data.get("installed_versions", {})

    for mod, data in mods.items():
        last_versions = versions.get(mod, ["—"])
        last = last_versions[-1] if last_versions else "—"
        prev = last_versions[-2] if len(last_versions) > 1 else "—"
        installed = installed_versions.get(mod, "—")

        # Получаем реальную версию с сайта
        new_version = get_version(data["url"])
        if last != new_version:
            if len(last_versions) == 2:
                last_versions = [last_versions[-1], new_version]
            else:
                last_versions.append(new_version)
            versions[mod] = last_versions
            save_versions(versions)
            last = new_version

        if installed != last:
            messages.append(
                f"🆕 Обновление для {mod}!\n"
                f"Предпоследняя: {prev}\nПоследняя: {last}\nУстановлено: {installed}"
            )
            buttons.append([InlineKeyboardButton(f"⬇ Скачать {mod}", url=data["url"])])

    if not messages:
        return "✅ Все моды обновлены", None
    return "\n\n".join(messages), buttons

async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text, buttons = check_updates_for_user(context.user_data)
    if buttons:
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(text, reply_markup=back_button())

# ===== Админ-панель =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Введите кодовое слово:")
    context.user_data["awaiting_code"] = True

# ===== Обработка сообщений =====
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Кодовое слово для админов
    if context.user_data.get("awaiting_code"):
        if text == ADMIN_CODE:
            admins.add(user_id)
            await update.message.reply_text("✅ Доступ администратора открыт", reply_markup=admin_menu())
        else:
            await update.message.reply_text("❌ Неверный код")
        context.user_data["awaiting_code"] = False
        return

    # Ввод установленных версий для модов
    if context.user_data.get("awaiting_installed_mod"):
        mod_name = context.user_data.get("new_mod_name_for_user")
        installed_versions = context.user_data.get("installed_versions", {})
        installed_versions[mod_name] = text
        context.user_data["installed_versions"] = installed_versions
        context.user_data["awaiting_installed_mod"] = False
        await update.message.reply_text(f"✅ Версия для '{mod_name}' сохранена!")
        return

    # Добавление нового модa админом
    if context.user_data.get("awaiting_mod_name"):
        context.user_data["new_mod_name"] = text
        context.user_data["awaiting_mod_name"] = False
        context.user_data["awaiting_mod_link"] = True
        await update.message.reply_text("Введите ссылку на мод:")
        return

    if context.user_data.get("awaiting_mod_link"):
        name = context.user_data.get("new_mod_name")
        link = text
        mods = load_mods()
        mods[name] = {"url": link}
        save_mods(mods)
        context.user_data["awaiting_mod_link"] = False
        await update.message.reply_text(f"✅ Мод '{name}' добавлен!", reply_markup=admin_menu())
        return

# ===== Callback кнопки добавления модов =====
async def add_mod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if user_id not in admins:
        await query.answer("Нет доступа", show_alert=True)
        return
    context.user_data["awaiting_mod_name"] = True
    await query.message.reply_text("Введите название мода:")

# ===== Callback кнопки «Обновил» =====
async def updated_mod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, mod_name = query.data.split("|")
    context.user_data["new_mod_name_for_user"] = mod_name
    context.user_data["awaiting_installed_mod"] = True
    await query.message.reply_text(f"Введите вашу установленную версию для {mod_name}:")

# ===== Callback список модов =====
async def list_mods_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await mods_list(update, context)

# ===== Основной запуск =====
app = ApplicationBuilder().token(TOKEN).build()

# Команды и кнопки
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu, pattern="menu"))
app.add_handler(CallbackQueryHandler(check_button, pattern="check"))
app.add_handler(CallbackQueryHandler(mods_list, pattern="mods"))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
app.add_handler(CallbackQueryHandler(add_mod_callback, pattern="add_mod"))
app.add_handler(CallbackQueryHandler(list_mods_callback, pattern="list_mods"))
app.add_handler(CallbackQueryHandler(updated_mod_callback, pattern="updated\\|"))

# Обработка текстовых сообщений
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Бот запущен")
app.run_polling()
