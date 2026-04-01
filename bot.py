import requests
import json
from bs4 import BeautifulSoup

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes


import os
TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "versions.json"


mods = {

"XML Injector":{
"url":"https://www.curseforge.com/sims4/mods/xml-injector/files"
},

"Wonderful Whims":{
"url":"https://www.curseforge.com/sims4/mods/wonderfulwhims/files"
},

"MC Command Center":{
"url":"https://deaderpool-mccc.com/downloads.html"
},

"Wicked Whims":{
"url":"https://wicked.cc/mods/admin/wickedwhims/#download"
},

"Basemental Drugs":{
"url":"https://basementalcc.com/adult_mods/basemental-drugs/"
}

}



def load_versions():

    try:
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    except:
        return {}



def save_versions(data):

    with open(DATA_FILE,"w") as f:
        json.dump(data,f,indent=4)



def get_version(url):

    r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"})
    soup=BeautifulSoup(r.text,"lxml")

    return soup.title.text.strip()



def main_menu():

    keyboard=[

        [InlineKeyboardButton("🔎 Проверить обновления",callback_data="check")],

        [InlineKeyboardButton("📦 Список модов",callback_data="mods")],

        [InlineKeyboardButton("⚙ Включить авто-проверку",callback_data="auto")]

    ]

    return InlineKeyboardMarkup(keyboard)



def back_button():

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Назад",callback_data="menu")]
    ])



async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Бот отслеживания обновлений модов Sims 4",
        reply_markup=main_menu()
    )



async def menu(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Главное меню",
        reply_markup=main_menu()
    )



async def mods_list(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    text="📦 Отслеживаемые моды:\n\n"

    for mod in mods:
        text+=f"• {mod}\n"

    await query.edit_message_text(
        text,
        reply_markup=back_button()
    )



def check_updates():

    versions=load_versions()

    messages=[]
    buttons=[]

    updated=False

    for mod,data in mods.items():

        try:

            version=get_version(data["url"])

            old=versions.get(mod)

            if old!=version:

                updated=True

                versions[mod]=version

                messages.append(f"🆕 Новый патч мода {mod}")

                buttons.append([
                    InlineKeyboardButton(
                        f"⬇ Скачать {mod}",
                        url=data["url"]
                    )
                ])

        except:

            messages.append(f"⚠ Ошибка проверки {mod}")

    save_versions(versions)

    if not updated:

        return "✅ Все моды обновлены",None

    return "\n\n".join(messages),buttons



async def check_button(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    text,buttons=check_updates()

    if buttons:

        buttons.append([InlineKeyboardButton("⬅ Назад",callback_data="menu")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    else:

        await query.edit_message_text(
            text,
            reply_markup=back_button()
        )



async def auto_check(update:Update,context:ContextTypes.DEFAULT_TYPE):

    chat_id=update.callback_query.message.chat_id

    context.job_queue.run_repeating(
        auto_task,
        interval=3600,
        first=10,
        chat_id=chat_id
    )

    await update.callback_query.edit_message_text(
        "🔔 Автопроверка включена",
        reply_markup=back_button()
    )



async def auto_task(context:ContextTypes.DEFAULT_TYPE):

    text,buttons=check_updates()

    if "🆕" in text:

        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )



app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))

app.add_handler(CallbackQueryHandler(menu,pattern="menu"))
app.add_handler(CallbackQueryHandler(check_button,pattern="check"))
app.add_handler(CallbackQueryHandler(mods_list,pattern="mods"))
app.add_handler(CallbackQueryHandler(auto_check,pattern="auto"))

print("Бот запущен")

app.run_polling()
