#!/usr/bin/env python3

import os
import json
import random
import logging
from functools import wraps
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# ----- CONFIG -----
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # set this env var before running
OWNER_ID = int(os.environ.get("OWNER_ID")) if os.environ.get("OWNER_ID") else None
QUOTES_FILE = "quotes.json"

# ----- LOGGING -----
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----- HELPERS -----
def load_quotes():
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in quotes file.")
        return []

def save_quotes(quotes):
    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)

def owner_only(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *a, **kw):
        user = update.effective_user
        if OWNER_ID is None:
            update.message.reply_text("Owner not configured on the bot. Contact the admin.")
            return
        if user and user.id == OWNER_ID:
            return func(update, context, *a, **kw)
        update.message.reply_text("❌ You are not authorized to use this command.")
    return wrapped

# ----- COMMANDS -----
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "⚡ Welcome to the Simple Quote Bot!\n\n"
        "Use /help to see available commands."
    )

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/quote - get a random quote\n"
        "/quote <author> - get a random quote by author (case-insensitive, partial match)\n"
        "/listauthors - list authors available\n"
        "/addquote \"quote text\" - author  (owner only)\n\n"
        "Example: /quote Lao Tzu\n"
        "Example add: /addquote \"Dream big and dare to fail\" - Norman Vaughan"
    )

def _find_by_author(author_query, quotes):
    q = author_query.lower()
    matches = [item for item in quotes if q in item.get("author","").lower()]
    return matches

def quote_cmd(update: Update, context: CallbackContext):
    args = context.args
    quotes = load_quotes()
    if not quotes:
        update.message.reply_text("No quotes available yet.")
        return

    if not args:
        chosen = random.choice(quotes)
        update.message.reply_text(f"“{chosen['text']}”\n\n— *{chosen['author']}*", parse_mode=ParseMode.MARKDOWN)
        return

    # author search
    author_query = " ".join(args).strip()
    matches = _find_by_author(author_query, quotes)
    if not matches:
        update.message.reply_text(f"No quotes found for author matching: {author_query}")
        return
    chosen = random.choice(matches)
    update.message.reply_text(f"“{chosen['text']}”\n\n— *{chosen['author']}*", parse_mode=ParseMode.MARKDOWN)

def list_authors(update: Update, context: CallbackContext):
    quotes = load_quotes()
    authors = sorted({q.get("author","Unknown") for q in quotes})
    if not authors:
        update.message.reply_text("No authors found in the database.")
        return
    text = "Authors available:\n\n" + "\n".join(f"- {a}" for a in authors)
    update.message.reply_text(text)

@owner_only
def add_quote(update: Update, context: CallbackContext):
    # expected format: /addquote "quote text" - author name
    full = update.message.text
    try:
        # remove the command part
        payload = full.partition(" ")[2].strip()
        if not payload:
            raise ValueError("No payload")
        # naive parse: split by last ' - ' occurrence
        if " - " not in payload:
            raise ValueError("Use: /addquote \"quote text\" - author")
        quote_part, sep, author = payload.rpartition(" - ")
        quote_part = quote_part.strip().strip('"').strip("'")
        author = author.strip()
        if not quote_part or not author:
            raise ValueError("Invalid parts")
    except Exception as e:
        update.message.reply_text("Invalid format. Use:\n/addquote \"quote text\" - author")
        return

    quotes = load_quotes()
    quotes.append({"text": quote_part, "author": author})
    save_quotes(quotes)
    update.message.reply_text("✅ Quote added successfully.")

def error_handler(update: Update, context: CallbackContext):
    logger.exception("Exception while handling update: %s", context.error)
    try:
        update.message.reply_text("An error occurred. Try again later.")
    except Exception:
        pass

# ----- MAIN -----
def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set. Set env var and restart.")
        return

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("quote", quote_cmd, pass_args=True))
    dp.add_handler(CommandHandler("listauthors", list_authors))
    dp.add_handler(CommandHandler("addquote", add_quote))

    dp.add_error_handler(error_handler)

    logger.info("Starting Simple Quote Bot...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
