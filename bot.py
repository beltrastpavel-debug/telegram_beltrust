import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# ===== НАСТРОЙКИ =====
TOKEN = "8644403088:AAESayqpTs14d65GNgZrneVdi8xbvu-Qff4"
SHEET_ID = "1YL-T84gQrHb6DF8LEgrx0pOMwchZ-ThkVDl7mMBVePE"

# ===== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS =====
def get_sheet(sheet_name):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    return sheet.worksheet(sheet_name)

# ===== БОТ =====
bot = telebot.TeleBot(TOKEN)
user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'status': 'main', 'buffer': ''}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("👥 Сотрудники", callback_data="employees"))
    markup.row(telebot.types.InlineKeyboardButton("💸 Расходы", callback_data="expenses"))
    markup.row(telebot.types.InlineKeyboardButton("💰 Продажи", callback_data="sales"))
    bot.send_message(chat_id, "🏠 <b>Главное меню</b>\n\nВыберите раздел:", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data
    
    if data == "employees":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🟢 Активные сотрудники", callback_data="employees_active"))
        markup.row(telebot.types.InlineKeyboardButton("📋 Все сотрудники", callback_data="employees_all"))
        markup.row(telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="menu"))
        bot.edit_message_text("👥 <b>Раздел сотрудников</b>\n\nВыберите действие:", chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    
    elif data == "employees_active":
        try:
            sheet = get_sheet("employees")
            records = sheet.get_all_records()
            markup = telebot.types.InlineKeyboardMarkup()
            for record in records:
                if str(record.get('status', '')).lower() == 'active':
                    name = record.get('name', '')
                    position = record.get('position', '')
                    markup.row(telebot.types.InlineKeyboardButton(f"{name} ({position})", callback_data=f"emp_{record.get('id', '')}"))
            markup.row(telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="employees"))
            bot.edit_message_text("🟢 <b>Активные сотрудники:</b>", chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            bot.send_message(chat_id, f"Ошибка: {e}")
    
    elif data == "employees_all":
        try:
            sheet = get_sheet("employees")
            records = sheet.get_all_records()
            text = "📋 <b>Список всех сотрудников:</b>\n\n"
            for record in records:
                name = record.get('name', '—')
                position = record.get('position', '—')
                status = str(record.get('status', '')).lower()
                icon = "🟢" if status == "active" else "⚪"
                text += f"{icon} <b>{name}</b> — {position}\n"
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="employees"))
            bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            bot.send_message(chat_id, f"Ошибка: {e}")
    
    elif data == "menu":
        start(call.message)
    
    elif data == "expenses":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("💰 Аванс", callback_data="exp_advance"))
        markup.row(telebot.types.InlineKeyboardButton("📦 Закупка", callback_data="exp_purchase"))
        markup.row(telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="menu"))
        bot.edit_message_text("💸 <b>Выберите категорию расхода:</b>", chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    
    elif data == "sales":
        bot.answer_callback_query(call.id, "💰 Раздел Продажи в разработке...")
    
    elif data == "exp_advance":
        user_states[chat_id] = {'status': 'wait_employee', 'buffer': 'advance'}
        markup = telebot.types.InlineKeyboardMarkup()
        try:
            sheet = get_sheet("employees")
            records = sheet.get_all_records()
            for record in records:
                if str(record.get('status', '')).lower() == 'active':
                    name = record.get('name', '')
                    markup.row(telebot.types.InlineKeyboardButton(name, callback_data=f"emp_advance_{record.get('id', '')}"))
            markup.row(telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="expenses"))
            bot.edit_message_text("👤 <b>Кому выдаем аванс?</b>", chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            bot.send_message(chat_id, f"Ошибка: {e}")
    
    elif data.startswith("emp_advance_"):
        emp_id = data.replace("emp_advance_", "")
        user_states[chat_id] = {'status': 'wait_amount', 'buffer': f"Аванс|{emp_id}"}
        bot.edit_message_text("💵 Введите сумму (только цифры):", chat_id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text
    
    if chat_id not in user_states:
        user_states[chat_id] = {'status': 'main', 'buffer': ''}
    
    state = user_states[chat_id]
    
    if state['status'] == 'wait_amount':
        try:
            amount = float(text.replace(',', '.'))
            buffer = state['buffer']
            category = buffer.split('|')[0]
            emp_id = buffer.split('|')[1]
            
            sheet = get_sheet("expenses_log")
            sheet.append_row([str(datetime.now()), category, emp_id, amount, chat_id])
            
            user_states[chat_id] = {'status': 'main', 'buffer': ''}
            bot.send_message(chat_id, f"✅ Расход '{category}' на сумму {amount} записан!")
            start(message)
        except ValueError:
            bot.send_message(chat_id, "⚠️ Введите сумму числом (например: 120 или 500.50)")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
