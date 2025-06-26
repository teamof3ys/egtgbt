import argparse
import asyncio
import json
import os
import sqlite3
from target_bot_code import generate_and_run_bot, escape_markdown, validate_config, validate_block_schema, init_db

def is_valid_text(text):
    """Validate text to ensure it contains only safe characters."""
    if not text:
        return False
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,:;@#$%^&" +
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    )
    invalid_chars = set(text) - allowed_chars
    if invalid_chars:
        print(f"Ошибка: найдены недопустимые символы в тексте: {invalid_chars}")
        return False
    return len(text.strip()) > 0

async def create_business_card(bot_name, bot_token, welcome_text, phone, email, website, help_text):
    if not is_valid_text(bot_name) or not is_valid_text(welcome_text) or not is_valid_text(help_text) or \
       (phone and not is_valid_text(phone)) or (email and not is_valid_text(email)) or (website and not is_valid_text(website)):
        print("Ошибка: один или несколько введенных текстов содержат недопустимые символы. Используйте буквы, цифры, пробелы и знаки препинания (кроме !, _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ?).")
        return
    config = {"bot_name": escape_markdown(bot_name), "handlers": []}
    contact_text = f"*{escape_markdown(welcome_text)}*\n\n📋 *Контактная информация:*\n"
    if website:
        contact_text += f"🌐 *Website:* {escape_markdown(website)}\n"
    if email:
        contact_text += f"📧 *Email:* {escape_markdown(email)}\n"
    if phone:
        contact_text += f"📞 *Phone:* {escape_markdown(phone)}\n"
    if not any([website, email, phone]):
        contact_text += "ℹ️ Контактная информация не указана.\n"

    handlers = [
        {"command": "/start", "text": contact_text},
        {"command": "/help", "text": escape_markdown(help_text)},
        {"command": "/create_bot", "text": "Начать создание нового бота."},
        {"command": "/list_bots", "text": "Показать список ваших ботов."},
        {"command": "/delete_bot", "text": "Удалить бота."},
        {
            "command": "/menu",
            "text": "Выберите действие:",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "Создать бота", "callback_data": "menu_create_bot", "response": "Начнем создание бота!"},
                        {"text": "Список ботов", "callback_data": "menu_list_bots", "response": "Показываю ваши боты."}
                    ],
                    [
                        {"text": "Удалить бота", "callback_data": "menu_delete_bot", "response": "Выберите бота для удаления."}
                    ]
                ]
            }
        }
    ]
    config["handlers"] = handlers

    is_valid, error = validate_config(config)
    if not is_valid:
        print(f"Ошибка в конфигурации: {error}")
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        print(f"Ошибка в схеме: {error}")
        return

    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)",
        (1, config['bot_name'], json.dumps(config), bot_token)  # user_id=1 как пример
    )
    config_id = c.lastrowid
    conn.commit()
    conn.close()

    await generate_and_run_bot(config, bot_token, config_id)
    print(f"Бот '{config['bot_name']}' успешно создан и запущен! ID: {config_id}")

async def create_faq(bot_name, bot_token, faqs):
    if not is_valid_text(bot_name):
        print("Ошибка: имя бота содержит недопустимые символы. Используйте буквы, цифры, пробелы и знаки препинания (кроме !, _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ?).")
        return
    config = {"bot_name": escape_markdown(bot_name), "handlers": []}
    faq_text = "Часто задаваемые вопросы:\nВыберите интересующий вопрос\\."
    keyboard_buttons = []

    faqs = [
        {"question": escape_markdown(faq["question"]), "answer": escape_markdown(faq["answer"])}
        for faq in faqs
    ]

    for i, faq in enumerate(faqs, 1):
        callback_data = f"faq_{i}"
        keyboard_buttons.append([
            {
                "text": faq["question"],
                "callback_data": callback_data,
                "response": faq["answer"]
            }
        ])

    handlers = [
        {"command": "/start", "text": "Добро пожаловать в бот FAQ! Используйте /faq для просмотра вопросов."},
        {"command": "/faq", "text": faq_text, "reply_markup": {"inline_keyboard": keyboard_buttons}}
    ]
    config["handlers"] = handlers

    is_valid, error = validate_config(config)
    if not is_valid:
        print(f"Ошибка в конфигурации: {error}")
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        print(f"Ошибка в схеме: {error}")
        return

    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)",
        (1, config['bot_name'], json.dumps(config), bot_token)  # user_id=1 как пример
    )
    config_id = c.lastrowid
    conn.commit()
    conn.close()

    await generate_and_run_bot(config, bot_token, config_id)
    print(f"Бот '{config['bot_name']}' успешно создан и запущен! ID: {config_id}")

async def create_poll(bot_name, bot_token, polls):
    if not is_valid_text(bot_name):
        print("Ошибка: имя бота содержит недопустимые символы. Используйте буквы, цифры, пробелы и знаки препинания (кроме !, _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ?).")
        return
    config = {"bot_name": escape_markdown(bot_name), "handlers": []}
    poll_text = "Опросы:\nВыберите интересующий опрос\\."
    keyboard_buttons = []

    polls = [
        {
            "question": escape_markdown(poll['question']),
            "options": [escape_markdown(opt) for opt in poll['options']]
        }
        for poll in polls
    ]

    for i, poll in enumerate(polls, 1):
        callback_data = f"poll_{i}"
        options_text = "\n".join([f"- {opt}" for opt in poll['options']])
        response_text = f"Вопрос: {poll['question']}\nВарианты ответа:\n{options_text}"
        keyboard_buttons.append([
            {
                "text": poll["question"],
                "callback_data": callback_data,
                "response": response_text
            }
        ])

    handlers = [
        {"command": "/start", "text": "Добро пожаловать в бот опросов! Используйте /poll для просмотра опросов."},
        {"command": "/poll", "text": poll_text, "reply_markup": {"inline_keyboard": keyboard_buttons}}
    ]
    config["handlers"] = handlers

    is_valid, error = validate_config(config)
    if not is_valid:
        print(f"Ошибка в конфигурации: {error}")
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        print(f"Ошибка в схеме: {error}")
        return

    conn = sqlite3.connect("bot_users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)",
        (1, config['bot_name'], json.dumps(config), bot_token)  # user_id=1 как пример
    )
    config_id = c.lastrowid
    for poll in polls:
        c.execute(
            "INSERT INTO polls (config_id, question, options) VALUES (?, ?, ?)",
            (config_id, poll["question"], json.dumps(poll["options"]))
        )
    conn.commit()
    conn.close()

    await generate_and_run_bot(config, bot_token, config_id)
    print(f"Бот '{config['bot_name']}' успешно создан и запущен! ID: {config_id}")

def main():
    init_db()
    parser = argparse.ArgumentParser(description="CLI для генерации Telegram-ботов")
    subparsers = parser.add_subparsers(dest="command")

    # Команда для создания бота "Визитка"
    parser_business = subparsers.add_parser("business_card", help="Создать бота-визитку")
    parser_business.add_argument("--name", required=True, help="Имя бота")
    parser_business.add_argument("--token", required=True, help="Токен бота от @BotFather")
    parser_business.add_argument("--welcome", required=True, help="Текст приветствия")
    parser_business.add_argument("--phone", help="Номер телефона")
    parser_business.add_argument("--email", help="Email")
    parser_business.add_argument("--website", help="URL сайта")
    parser_business.add_argument("--help-text", required=True, help="Текст для /help")

    # Команда для создания бота "FAQ"
    parser_faq = subparsers.add_parser("faq", help="Создать бота-FAQ")
    parser_faq.add_argument("--name", required=True, help="Имя бота")
    parser_faq.add_argument("--token", required=True, help="Токен бота от @BotFather")
    parser_faq.add_argument("--faqs", nargs="+", help="Список вопросов и ответов (в формате 'вопрос:ответ')")

    # Команда для создания бота "Опросник"
    parser_poll = subparsers.add_parser("poll", help="Создать бота-опросник")
    parser_poll.add_argument("--name", required=True, help="Имя бота")
    parser_poll.add_argument("--token", required=True, help="Токен бота от @BotFather")
    parser_poll.add_argument("--polls", nargs="+", help="Список опросов в формате 'вопрос:вариант1,вариант2,...'")

    args = parser.parse_args()

    if args.command == "business_card":
        asyncio.run(create_business_card(
            args.name, args.token, args.welcome, args.phone, args.email, args.website, args.help_text
        ))
    elif args.command == "faq":
        faqs = []
        if args.faqs:
            for faq_str in args.faqs:
                if ":" in faq_str:
                    question, answer = faq_str.split(":", 1)
                    if is_valid_text(question) and is_valid_text(answer):
                        faqs.append({"question": question, "answer": answer})
                    else:
                        print("Ошибка: вопрос или ответ содержат недопустимые символы. Используйте буквы, цифры, пробелы и знаки препинания (кроме !, _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ?).")
                        return
        if not faqs:
            print("Ошибка: укажите хотя бы один вопрос и ответ в формате 'вопрос:ответ'.")
            return
        asyncio.run(create_faq(args.name, args.token, faqs))
    elif args.command == "poll":
        polls = []
        if args.polls:
            for poll_str in args.polls:
                if ":" in poll_str:
                    question, options_str = poll_str.split(":", 1)
                    options = options_str.split(",")
                    if len(options) < 2 or len(options) > 4:
                        print("Ошибка: опрос должен содержать от 2 до 4 вариантов ответа.")
                        return
                    if is_valid_text(question) and all(is_valid_text(opt) for opt in options):
                        polls.append({"question": question, "options": options})
                    else:
                        print("Ошибка: вопрос или варианты ответа содержат недопустимые символы. Используйте буквы, цифры, пробелы и знаки препинания (кроме !, _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ?).")
                        return
        if not polls:
            print("Ошибка: укажите хотя бы один опрос в формате 'вопрос:вариант1,вариант2,...'.")
            return
        asyncio.run(create_poll(args.name, args.token, polls))

if __name__ == "__main__":
    main()