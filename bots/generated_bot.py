import asyncio
import logging
import sys
import sqlite3
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from utils.utils_validation import validate_config
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

def init_db():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_configs (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            config_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

dp = Dispatcher()
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

@dp.message(Command("start"))
async def start_handler(message: Message) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="🌐 Мой сайт", url="https://example.com"),
            InlineKeyboardButton(text="📧 Контакты", callback_data="contact_info"),
        ],
        [
            InlineKeyboardButton(text="📞 Позвонить", url="tel:+1234567890"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    @dp.callback_query(lambda c: c.data == "contact_info")
    async def callback_contact_info_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Свяжитесь со мной:\\n📧 Email: user@example.com\\n📞 Телефон: +1234567890")
        await callback.answer()
    await message.answer("Привет! Я бот-визитка.\\n\\nЗдесь вы можете найти всю необходимую информацию обо мне и связаться со мной.", reply_markup=keyboard)

@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer("Просто нажмите /start, чтобы увидеть визитку.")

@dp.message(Command("faq"))
async def faq_handler(message: Message) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Что вы делаете?", callback_data="faq_what_do_you_do"),
            InlineKeyboardButton(text="Как связаться?", callback_data="faq_contact"),
        ],
        [
            InlineKeyboardButton(text="Где вы находитесь?", callback_data="faq_location"),
            InlineKeyboardButton(text="Вопрос 2", callback_data="faq_q2"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    @dp.callback_query(lambda c: c.data == "faq_what_do_you_do")
    async def callback_faq_what_do_you_do_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Мы создаем крутые Telegram-боты!")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "faq_contact")
    async def callback_faq_contact_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Напишите на почту user@example.com или позвоните +1234567890.")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "faq_location")
    async def callback_faq_location_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Наш офис находится в центре города.")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "faq_q2")
    async def callback_faq_q2_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Ответ на вопрос 2")
        await callback.answer()
    await message.answer("Часто задаваемые вопросы:\\nВыберите интересующий вопрос.", reply_markup=keyboard)

@dp.message(Command("create_bot"))
async def create_bot_handler(message: Message) -> None:
    await message.answer("Начать создание нового бота.")

@dp.message(Command("list_bots"))
async def list_bots_handler(message: Message) -> None:
    await message.answer("Показать список ваших ботов.")

@dp.message(Command("edit_bot"))
async def edit_bot_handler(message: Message) -> None:
    await message.answer("Редактировать существующего бота.")

@dp.message(Command("delete_bot"))
async def delete_bot_handler(message: Message) -> None:
    await message.answer("Удалить бота.")

@dp.message(Command("menu"))
async def menu_handler(message: Message) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Создать бота", callback_data="menu_create_bot"),
            InlineKeyboardButton(text="Список ботов", callback_data="menu_list_bots"),
        ],
        [
            InlineKeyboardButton(text="Редактировать бота", callback_data="menu_edit_bot"),
            InlineKeyboardButton(text="Удалить бота", callback_data="menu_delete_bot"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    @dp.callback_query(lambda c: c.data == "menu_create_bot")
    async def callback_menu_create_bot_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Начнем создание бота!")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "menu_list_bots")
    async def callback_menu_list_bots_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Показываю ваши боты.")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "menu_edit_bot")
    async def callback_menu_edit_bot_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Выберите бота для редактирования.")
        await callback.answer()
    @dp.callback_query(lambda c: c.data == "menu_delete_bot")
    async def callback_menu_delete_bot_handler(callback: CallbackQuery) -> None:
        await callback.message.answer("Выберите бота для удаления.")
        await callback.answer()
    await message.answer("Выберите действие:", reply_markup=keyboard)

async def main() -> None:
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())