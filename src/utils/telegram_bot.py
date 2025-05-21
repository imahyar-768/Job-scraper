from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class JobTelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        self.chat_ids = set()
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        self.chat_ids.add(update.effective_chat.id)
        await update.message.reply_text(
            'Welcome to Job Scraper Bot! 🤖\n'
            'You will receive notifications about new job postings.\n'
            'Use /help to see available commands.'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        await update.message.reply_text(
            'Available commands:\n'
            '/start - Start receiving job notifications\n'
            '/help - Show this help message'
        )

    async def send_job_notification(self, job_data: dict) -> None:
        """Send a job notification to all registered users."""
        if not self.chat_ids:
            logger.warning("No chat IDs registered to send notifications to")
            return

        message = self._format_job_message(job_data)
        
        for chat_id in self.chat_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Failed to send message to chat {chat_id}: {e}")

    def _format_job_message(self, job_data: dict) -> str:
        """Format job data into a readable message."""
        message = (
            f"🔍 <b>New Job Found!</b>\n\n"
            f"📋 <b>Title:</b> {job_data['title']}\n"
            f"🏢 <b>Company:</b> {job_data['company']}\n"
            f"📍 <b>Location:</b> {job_data['location']}\n"
        )

        if job_data.get('metadata'):
            metadata = job_data['metadata']
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            if metadata.get('employment_type'):
                message += f"💼 <b>Employment Type:</b> {metadata['employment_type']}\n"
            if metadata.get('experience'):
                message += f"⭐ <b>Experience:</b> {metadata['experience']}\n"
            if metadata.get('salary'):
                message += f"💰 <b>Salary:</b> {metadata['salary']}\n"
            if metadata.get('tech_stack'):
                tech_stack = metadata['tech_stack']
                if isinstance(tech_stack, dict):
                    for category, techs in tech_stack.items():
                        if techs:
                            message += f"🔧 <b>{category.title()}:</b> {', '.join(techs)}\n"
                elif isinstance(tech_stack, list):
                    message += f"🔧 <b>Tech Stack:</b> {', '.join(tech_stack)}\n"

        message += f"\n🔗 <b>Apply here:</b> {job_data['url']}"
        return message

    async def start_bot(self):
        """Start the Telegram bot."""
        await self.application.initialize()
        await self.application.start()
        logger.info("Telegram bot started successfully")

    async def stop_bot(self):
        """Stop the Telegram bot."""
        await self.application.stop()
        logger.info("Telegram bot stopped")
