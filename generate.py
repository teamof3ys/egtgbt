import os
import json
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import sqlite3

logger = logging.getLogger(__name__)

def escape_python_string(text):
    if not text:
        return '""'
    return repr(text)[1:-1].replace('\"', '\\\"')

def generate(config, output_file, config_id):
    script_lines = [
        "import sqlite3",
        "import logging",
        "import os",
        "import sys",
        "from aiogram import Bot, Dispatcher",
        "from aiogram.enums import ParseMode",
        "from aiogram.filters import Command",
        "from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery",
        "from aiogram.fsm.storage.memory import MemoryStorage",
        "from aiogram.client.default import DefaultBotProperties",
        "from dotenv import load_dotenv",
        "",
        "logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)",
        "logger = logging.getLogger(__name__)",
        "",
        "load_dotenv()",
        "BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')",
        "",
        "def init_db():",
        "    conn = sqlite3.connect('bot_users.db')",
        "    c = conn.cursor()",
        "    c.execute('''",
        "        CREATE TABLE IF NOT EXISTS polls (",
        "            poll_id INTEGER PRIMARY KEY AUTOINCREMENT,",
        "            config_id INTEGER,",
        "            question TEXT,",
        "            options TEXT,",
        "            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,",
        "            FOREIGN KEY (config_id) REFERENCES bot_configs (config_id)",
        "        )",
        "    ''')",
        "    c.execute('''",
        "        CREATE TABLE IF NOT EXISTS poll_responses (",
        "            response_id INTEGER PRIMARY KEY AUTOINCREMENT,",
        "            user_id INTEGER,",
        "            poll_id INTEGER,",
        "            config_id INTEGER,",
        "            option_text TEXT,",
        "            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,",
        "            FOREIGN KEY (config_id) REFERENCES bot_configs (config_id),",
        "            FOREIGN KEY (poll_id) REFERENCES polls (poll_id)",
        "        )",
        "    ''')",
        "    conn.commit()",
        "    conn.close()",
        "",
        "def save_poll_response(user_id, poll_id, config_id, option_text):",
        "    conn = sqlite3.connect('bot_users.db')",
        "    c = conn.cursor()",
        "    c.execute('INSERT INTO poll_responses (user_id, poll_id, config_id, option_text) VALUES (?, ?, ?, ?)',",
        "              (user_id, poll_id, config_id, option_text))",
        "    conn.commit()",
        "    conn.close()",
        "",
        "dp = Dispatcher(storage=MemoryStorage())",
        "bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))",
        "",
    ]

    for handler in config.get('handlers', []):
        command = handler.get('command')
        callback_query = handler.get('callback_query')
        text = handler.get('text')
        reply_markup = handler.get('reply_markup')
        save_response = handler.get('save_response')

        escaped_text = f'"{escape_python_string(text)}"'

        if command:
            script_lines.append(f"@dp.message(Command('{command[1:]}'))")
            script_lines.append(f"async def command_{command[1:]}_handler(message: Message) -> None:")
            if reply_markup:
                keyboard_buttons = []
                for row in reply_markup.get('inline_keyboard', []):
                    row_buttons = []
                    for button in row:
                        button_text = escape_python_string(button['text'])
                        callback_data = escape_python_string(button['callback_data'])
                        row_buttons.append(f'{{ "text": "{button_text}", "callback_data": "{callback_data}" }}')
                    keyboard_buttons.append(f"[{', '.join(row_buttons)}]")
                keyboard = f"InlineKeyboardMarkup(inline_keyboard=[{', '.join(keyboard_buttons)}])"
                script_lines.append(f"    keyboard = {keyboard}")
                script_lines.append(f"    await message.answer({escaped_text}, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)")
            else:
                script_lines.append(f"    await message.answer({escaped_text}, parse_mode=ParseMode.MARKDOWN_V2)")
            script_lines.append("")

        elif callback_query:
            if reply_markup:
                keyboard_buttons = []
                for row in reply_markup.get('inline_keyboard', []):
                    row_buttons = []
                    for button in row:
                        button_text = escape_python_string(button['text'])
                        callback_data = escape_python_string(button['callback_data'])
                        row_buttons.append(f'{{ "text": "{button_text}", "callback_data": "{callback_data}" }}')
                    keyboard_buttons.append(f"[{', '.join(row_buttons)}]")
                keyboard = f"InlineKeyboardMarkup(inline_keyboard=[{', '.join(keyboard_buttons)}])"

                script_lines.append(f"@dp.callback_query(lambda c: c.data == '{callback_query}')")
                script_lines.append(f"async def callback_{callback_query}_handler(callback: CallbackQuery) -> None:")
                script_lines.append(f"    keyboard = {keyboard}")
                script_lines.append(f"    await callback.message.answer({escaped_text}, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)")
                if save_response:
                    poll_id = save_response.get('poll_id')
                    option_text = escape_python_string(save_response.get('option_text'))
                    thank_you_text = escape_python_string(save_response.get('thank_you_text'))
                    script_lines.append(f"    save_poll_response(callback.from_user.id, {poll_id}, {config_id}, '{option_text}')")
                    script_lines.append(f"    await callback.message.answer('{thank_you_text}', parse_mode=ParseMode.MARKDOWN_V2)")
                script_lines.append("    await callback.answer()")
                script_lines.append("")
            elif save_response:
                poll_id = save_response.get('poll_id')
                option_text = escape_python_string(save_response.get('option_text'))
                thank_you_text = escape_python_string(save_response.get('thank_you_text'))
                script_lines.append(f"@dp.callback_query(lambda c: c.data == '{callback_query}')")
                script_lines.append(f"async def callback_{callback_query}_handler(callback: CallbackQuery) -> None:")
                script_lines.append(f"    await callback.message.answer({escaped_text}, parse_mode=ParseMode.MARKDOWN_V2)")
                script_lines.append(f"    save_poll_response(callback.from_user.id, {poll_id}, {config_id}, '{option_text}')")
                script_lines.append(f"    await callback.message.answer('{thank_you_text}', parse_mode=ParseMode.MARKDOWN_V2)")
                script_lines.append("    await callback.answer()")
                script_lines.append("")
            else:
                script_lines.append(f"@dp.callback_query(lambda c: c.data == '{callback_query}')")
                script_lines.append(f"async def callback_{callback_query}_handler(callback: CallbackQuery) -> None:")
                script_lines.append(f"    await callback.message.answer({escaped_text}, parse_mode=ParseMode.MARKDOWN_V2)")
                script_lines.append("    await callback.answer()")
                script_lines.append("")

    script_lines.append("async def main():")
    script_lines.append("    init_db()")
    script_lines.append("    await dp.start_polling(bot)")
    script_lines.append("")
    script_lines.append("if __name__ == '__main__':")
    script_lines.append("    import asyncio")
    script_lines.append("    import sys")
    script_lines.append("    asyncio.run(main())")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(script_lines))
    logger.info(f"Successfully generated bot script at {output_file}")