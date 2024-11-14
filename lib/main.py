import logging
from dotenv import load_dotenv
from os import getenv

load_dotenv()

from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, File
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

from converter import Converter, ConversionPairs

from shutil import rmtree


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

CONVERSION_PAIR, FILE = range(2)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Press menu -> file_conversion to start using this bot")



async def file_conversion_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    available_conversion_pairs: list[list[InlineKeyboardButton]] = []
    
    for pair in ConversionPairs:
        text = pair.name
        text = text.replace("_to_", " -> ")
        available_conversion_pairs.append(
            [InlineKeyboardButton(text=text, callback_data=pair.name)]
        )
        
    await update.message.reply_text(
        "Choose available conversion pairs",
        reply_markup=InlineKeyboardMarkup(available_conversion_pairs)
    )
    
    return CONVERSION_PAIR


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
        
    conversion_pair = ConversionPairs[query.data]
    
    context.user_data[CONVERSION_PAIR] = conversion_pair.value
    
    await query.edit_message_text(f"Send file with extension '{conversion_pair.value[0]}'")
    
    return FILE
    
    
async def handle_convert_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = await context.bot.get_file(update.message.document)
    
    loading_message = await update.message.reply_text("Loading ⏳")
    
    res = await convert_file(update, context, file)
    
    await context.bot.deleteMessage(loading_message.chat_id, loading_message.id)
    await update.message.delete()
    
    return res
    

async def handle_convert_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.effective_attachment[-1].get_file()
    
    loading_message = await update.message.reply_text("Loading ⏳")
    
    res = await convert_file(update, context, file)
    
    await context.bot.deleteMessage(loading_message.chat_id, loading_message.id)
    await update.message.delete()
    
    return res
    
async def convert_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file: File):
    if not isinstance(file, File):
        await update.message.reply_text("Expected file")
        return ConversationHandler.END
    
    conversion_pair = context.user_data.get(CONVERSION_PAIR, None)
    if not conversion_pair:
        await update.message.reply_text("Something went wrong, stopping conversation")
        return ConversationHandler.END
    
    converter = Converter(conversion_pair)
    
    verified, extension = converter.verify_signature(file)
    
    if not verified:
        await update.message.reply_text(f"Wrong file extension. Expected '{converter.in_t}', got '{extension}'")
        return ConversationHandler.END
    
    inp_file_path, out_file_path = await converter.convert(file)
    
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(chat_id, "Converted file:")
    await context.bot.send_document(chat_id, open(out_file_path, "rb"))
    
    try:
        rmtree(inp_file_path.parent)
    except Exception as e:
        logger.error(e)
    
    return ConversationHandler.END
    
    

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    token = getenv("BOT_TOKEN")
    application = Application.builder().token(token).build()
    
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    
    file_conversion_handler = ConversationHandler(
        entry_points=[CommandHandler("file_conversion", file_conversion_start)],
        states={
            CONVERSION_PAIR: [CallbackQueryHandler(button)],
            FILE: [
                MessageHandler(filters.Document.ALL, handle_convert_file),
                MessageHandler(filters.PHOTO, handle_convert_photo)
                ]
        },
        fallbacks=[]
    )
    
    application.add_handler(file_conversion_handler)
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()