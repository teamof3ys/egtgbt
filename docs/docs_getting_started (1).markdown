# Начало работы

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/telegram-bot-builder.git
   cd telegram-bot-builder
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создайте файл `.env` в корневой директории и добавьте токен бота:
   ```text
   BOT_TOKEN=your_telegram_bot_token
   ```
4. Создайте файл `config_business_card.json` или используйте существующий шаблон.
5. Сгенерируйте бота:
   ```bash
   python generate.py
   ```
6. Запустите бота:
   ```bash
   python generated_bot.py
   ```

## Конфигурация
Создайте файл `config_business_card.json` с конфигурацией бота. Пример:

```json
{
  "bot_name": "MyBot",
  "handlers": [
    {
      "command": "/start",
      "text": "Привет!",
      "reply_markup": {
        "inline_keyboard": [
          [{"text": "Мой сайт", "url": "https://example.com"}]
        ]
      }
    }
  ]
}
```

Поддерживаются шаблоны: **Визитка**, **FAQ**, **Опросник**, **Конструктор блоков**.

Поддерживаемые команды: `/start`, `/help`, `/faq`, `/poll`, `/create_bot`, `/list_bots`, `/edit_bot`, `/delete_bot`, `/menu`.

Используйте JSON для настройки inline-кнопок.

## Использование CLI
Запустите `python cli.py --help` для списка команд. Примеры создания ботов:

### Создание бота-визитки:
```bash
python cli.py business_card --name MyBot --token your_token --welcome "Привет!" --help-text "Используйте /start"
```

### Создание бота-FAQ:
```bash
python cli.py faq --name MyFAQBot --token your_token --faqs "Что вы делаете?:Создаем боты" "Как связаться?:Пишите на user@example.com"
```

### Создание бота-опросника:
```bash
python cli.py poll --name MyPollBot --token your_token --polls "Какой ваш любимый цвет?:Красный,Синий,Зеленый" "Какой ваш любимый сезон?:Лето,Зима"
```

## Тестирование
Запустите тесты:
```bash
pytest
```