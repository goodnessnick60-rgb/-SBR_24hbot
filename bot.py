import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN found in environment variables")
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")

# Free summarization API (no key required)
SUMMARY_API = "https://text.pollinations.ai/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    welcome_text = (
        "📝 *Text Summarizer Bot*\n\n"
        "I can summarize long texts, articles, or messages for you!\n\n"
        "*How to use:*\n"
        "1️⃣ Reply to any message with `/summarize`\n"
        "2️⃣ Or send `/summarize` followed by text\n"
        "3️⃣ Or just forward me any message\n\n"
        "*Examples:*\n"
        "• `/summarize` (reply to a message)\n"
        "• `/summarize Your long text here...`\n"
        "• Forward a message to me\n\n"
        "Made with ❤️ - No API keys required!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "🆘 *Help Guide*\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - This help guide\n"
        "/summarize - Summarize text\n"
        "/about - About this bot\n\n"
        "*Tips:*\n"
        "• Reply to a message with /summarize\n"
        "• Send long texts directly\n"
        "• Works with URLs too (tries to extract text)"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send about information."""
    about_text = (
        "ℹ️ *About This Bot*\n\n"
        "This bot uses free AI to summarize text.\n\n"
        "• No API keys required\n"
        "• Free to use\n"
        "• Runs on Railway\n\n"
        "Source code available on GitHub."
    )
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def summarize_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summarize text from command or reply."""
    # Check if user replied to a message
    if update.message.reply_to_message:
        text_to_summarize = update.message.reply_to_message.text or update.message.reply_to_message.caption
    elif context.args:
        # Get text from command arguments
        text_to_summarize = ' '.join(context.args)
    else:
        await update.message.reply_text(
            "Please reply to a message with /summarize or send text after the command.\n\n"
            "Example: `/summarize Your long text here...`",
            parse_mode='Markdown'
        )
        return

    if not text_to_summarize:
        await update.message.reply_text("I couldn't find any text to summarize.")
        return

    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Limit text length for API
    if len(text_to_summarize) > 3000:
        text_to_summarize = text_to_summarize[:3000]
        await update.message.reply_text("⚠️ Text was truncated to 3000 characters for processing.")

    try:
        # Clean the text for URL encoding
        prompt = f"Summarize this text concisely in 2-3 sentences: {text_to_summarize}"
        encoded_prompt = requests.utils.quote(prompt)
        
        response = requests.get(
            f"{SUMMARY_API}{encoded_prompt}",
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        if response.status_code == 200:
            summary = response.text.strip()
            
            # If summary is too long, split it
            if len(summary) > 4096:
                for i in range(0, len(summary), 4096):
                    await update.message.reply_text(summary[i:i+4096])
            else:
                await update.message.reply_text(f"📝 *Summary:*\n\n{summary}", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "⚠️ Sorry, the summarization service is currently unavailable. Please try again later."
            )
            
    except requests.exceptions.Timeout:
        await update.message.reply_text("⏰ The request timed out. Please try again with shorter text.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ An error occurred while summarizing. Please try again."
        )

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages automatically."""
    if update.message.forward_date:
        text = update.message.text or update.message.caption
        if text and len(text) > 100:  # Only summarize longer texts
            await update.message.reply_text("📝 *Summarizing your forwarded message...*", parse_mode='Markdown')
            # Create a fake command context to reuse summarize function
            context.args = [text]
            await summarize_text(update, context)

def main():
    """Start the bot."""
    # Create application
    app = Application.builder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("summarize", summarize_text))
    
    # Handle forwarded messages
    app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT & ~filters.COMMAND, handle_forward))

    # Start polling
    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
