"""
WB/OZON GPT Bot — Telegram-бот на long polling.
Запуск на Render как Background Worker ИЛИ локально.

Нужные переменные окружения:
- OPENAI_API_KEY      — ключ OpenAI (формат sk-...)
- TELEGRAM_BOT_TOKEN  — токен бота из BotFather

Команды бота:
  /start   — приветствие и подсказки
  /analyze — режим Анализ конкурентов и оптимизация карточек
  /review  — режим Ответы на отзывы (3 стиля)
  /faq     — режим Ответы на вопросы покупателей (кратко)
  /help    — краткая справка

Зависимости (requirements.txt):
  python-telegram-bot==21.4
  openai
  python-dotenv
"""

import os
import logging
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- ЛОГИ ----------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("wb-ozon-bot")

# ---------- КЛЮЧИ/НАСТРОЙКИ ----------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not OPENAI_API_KEY:
    log.warning("Не задан OPENAI_API_KEY — проверь переменные окружения!")
if not TELEGRAM_TOKEN:
    log.warning("Не задан TELEGRAM_BOT_TOKEN — проверь переменные окружения!")

# Инициализируем OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- ПЕРСОНА АССИСТЕНТА И РЕЖИМЫ ----------
SYSTEM_BASE = (
    "Ты — помощник продавца на Wildberries и Ozon: анализ конкурентов, "
    "оптимизация карточек (SEO/заголовок/описание/фото/УТП/характеристики), "
    "ответы на отзывы и вопросы покупателей. "
    "Отвечай структурировано и по делу. Формат по умолчанию: "
    "📊 Анализ / ✅ Выводы / 💡 Рекомендации."
)

MODES = {
    "analyze": "Режим: АНАЛИЗ КОНКУРЕНТОВ. "
               "Подсказка: пришли данные так:\n\n"
               "Конкуренты:\n"
               "- Заголовки: ...\n"
               "- Описания: ...\n"
               "- Цены: ...\n"
               "- Отзывы: ...\n\n"
               "Моя карточка:\n"
               "- Заголовок: ...\n"
               "- Описание: ...\n"
               "- Цена: ...\n"
               "- Фото/характеристики: ...\n",
    "review":  "Режим: ОТВЕТЫ НА ОТЗЫВЫ. "
               "Подсказка: пришли текст отзыва так:\n\n"
               "Отзыв: \"Доставка долгая, качество среднее\"",
    "faq":     "Режим: ОТВЕТЫ НА ВОПРОСЫ. "
               "Подсказка: пришли вопрос покупателя так:\n\n"
               "Вопрос: \"Подойдёт ли эта футболка для спорта?\""
}

# Храним режимы на пользователя
user_modes: dict[int, str] = {}

def split_message(text: str, chunk_size: int = 3200) -> List[str]:
    if not text:
        return [""]
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def build_instructions(user_id: int) -> str:
    mode = user_modes.get(user_id, "analyze")
    return f"{SYSTEM_BASE}\n{MODES[mode]}"

# ---------- ХЭНДЛЕРЫ ----------
HELP_TEXT = (
    "Команды:\n"
    "/analyze — анализ конкурентов и оптимизация карточек\n"
    "/review — ответы на отзывы (3 стиля)\n"
    "/faq — ответы на вопросы покупателей (кратко)\n\n"
    "Примеры:\n"
    "• /analyze → вставь данные о конкурентах и своей карточке.\n"
    "• /review → вставь текст отзыва.\n"
    "• /faq → вставь вопрос покупателя.\n"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_user.id] = "analyze"
    text = (
        "Привет! Я GPT-ассистент для продавцов WB/OZON.\n\n"
        + HELP_TEXT +
        "\nСейчас включён режим: /analyze."
    )
    await update.message.reply_text(text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    user_modes[update.effective_user.id] = mode
    names = {"analyze": "АНАЛИЗ", "review": "ОТЗЫВЫ", "faq": "ВОПРОСЫ"}
    await update.message.reply_text(
        f"Готово! Режим: {names[mode]}.\n\n{MODES[mode]}"
    )

async def mode_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_mode(update, context, "analyze")

async def mode_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_mode(update, context, "review")

async def mode_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_mode(update, context, "faq")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    user_id = update.effective_user.id
    prompt = msg.text.strip()
    instructions = build_instructions(user_id)

    log.info("Запрос от %s | режим=%s | %s",
             user_id, user_modes.get(user_id, "analyze"),
             prompt[:160].replace("\n", " "))

    try:
        resp = client.responses.create(
            model="gpt-4o-mini",
            instructions=instructions,
            input=prompt
        )
        answer = resp.output_text or "Нет текста ответа."
    except Exception as e:
        log.exception("Ошибка OpenAI: %s", e)
        answer = f"Упс, ошибка запроса: {e}"

    for part in split_message(answer):
        await msg.reply_text(part)

# ---------- ЗАПУСК ----------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("analyze", mode_analyze))
    app.add_handler(CommandHandler("review", mode_review))
    app.add_handler(CommandHandler("faq", mode_faq))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Бот запущен (long polling).")
    app.run_polling()

if __name__ == "__main__":
    main()
