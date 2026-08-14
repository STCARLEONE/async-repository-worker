from __future__ import annotations

import asyncio
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .database import Database

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hello! I'm a search bot for GitHub repositories.\n\n"
        "Just send me a keyword and I'll search for repositories.\n"
        "Example: `python`\n\n"
        "You can also use filters like:\n"
        "`python language:python stars:>1000`"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Please enter a search term.")
        return

    await update.message.reply_text(f"🔍 Searching for: {query} ...")

    db = Database()
    await db.connect()

    try:
        results = await db.search(query, limit=10)

        if not results:
            await update.message.reply_text(f"❌ No results found for: {query}")
            return

        response = f"📦 **Results for '{query}':**\n\n"

        for idx, repo in enumerate(results, 1):
            response += (
                f"{idx}. [{repo['full_name']}](https://github.com/{repo['full_name']})\n"
                f"   ⭐ {repo['stars']} | 🍴 {repo['forks']}\n"
            )
            if repo.get("language"):
                response += f"   📝 {repo['language']}\n"
            if repo.get("description"):
                desc = repo["description"][:100]
                response += f"   📄 {desc}...\n"
            response += "\n"

        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e!s}")

    finally:
        await db.close()


async def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("🤖 Bot is running...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
