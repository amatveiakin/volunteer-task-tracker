from functools import partial
import logging
from typing import TypeAlias

from telegram import Update, User, Chat, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from volunteer_common import DB, Task, TaskStatus


logger = logging.getLogger(__name__)


def all_tasks(update: Update, context: CallbackContext, db: DB) -> None:
    # TODO: ...
    pass

def on_button_tap(update: Update, context: CallbackContext, db: DB) -> None:
    # TODO: Remove unless this bot has buttons
    pass

def on_message(update: Update, context: CallbackContext) -> None:
    # TODO: Do something about unexpected messages
    pass


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    db = DB()
    # TODO: DB schema for keeping track of messages corresponding to tasks.
    db.cur.execute("""CREATE TABLE IF NOT EXISTS messages(
        chat_id INTEGER,
        message_id INTEGER
    )""")

    with open('volunteer_task_bot.key') as f:
        token = f.read().strip()
    updater = Updater(token)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    # TODO: Support "/help" command as per https://core.telegram.org/bots/features#global-commands
    # TODO: Update tasks automatically
    dispatcher.add_handler(CommandHandler("alltasks", partial(all_tasks, db=db)))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(partial(on_button_tap, db=db)))

    # Register handler for text input (except commands)
    dispatcher.add_handler(MessageHandler(~Filters.command, on_message))

    dispatcher.bot.set_my_commands([
        BotCommand("alltasks", "View all tasks")
    ])

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
