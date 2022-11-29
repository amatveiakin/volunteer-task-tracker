from functools import partial
import logging
from typing import TypeAlias

from telegram import Update, User, Chat, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from volunteer_common import DB, Task, TaskStatus


logger = logging.getLogger(__name__)

class Action:
    CANCEL = "CANCEL"
    SELECT = "SELECT"
    CREATE = "CREATE"

def action_select(kind: str) -> str:
    return "/".join([Action.SELECT, kind])

class NewTaskState:
    def __init__(self):
        self.kind: str|None = None
        self.text: str|None = None

NewTaskStateMap: TypeAlias = dict[int, NewTaskState]

NEW_TASK_INPUT_TEXT = {}
NEW_TASK_CONFIRMATION_TEXT = {}
NEW_TASK_CREATED_TEXT = {}

NEW_TASK_KIND_SELECTION_TEXT = """<b>Create new task</b>\n
Choose the type of the task."""
CANCELLED_TEXT = "Cancelled."

NEW_TASK_INPUT_TEXT[Task.SHELTER] = """<b>⛺️ Looking for shelter</b>\n
Enter you request below. Make sure to include #LocationHashtag."""
NEW_TASK_CONFIRMATION_TEXT[Task.SHELTER] = """<b>⛺️ You are about to submit the following shelter request:</b>"""
NEW_TASK_CREATED_TEXT[Task.SHELTER] = """<b>⛺️ Shelter request created:</b>"""

NEW_TASK_INPUT_TEXT[Task.TRANSPORT] = """<b>🚗 Looking for transport</b>\n
Enter you request below. Make sure to include #LocationHashtag for the source and destination locations."""
NEW_TASK_CONFIRMATION_TEXT[Task.TRANSPORT] = """<b>🚗 You are about to submit the following transport request:</b>"""
NEW_TASK_CREATED_TEXT[Task.TRANSPORT] = """<b>🚗 Transport request created:</b>"""

# # TODO: Add info wiki links
# NEW_TASK_INPUT_TEXT[Task.QUESTION] = """<b>❔ Ask a question</b>\n
# Make sure to <i>check the wiki first!</i>
# If you cannot find an answer elsewhere, please enter the question below"""
# NEW_TASK_CONFIRMATION_TEXT[Task.QUESTION] = """You are about to submit the following question:"""

# TODO: Privacy policy
NEW_TASK_CONFIRMATION_TEMPLATE = """{header}\n
{task}\n
Your telegram account ({user}) will be displayed publicly. Community members will use it to reach you.
Please make sure to mark this task as “Done” when your question is answered."""
# TODO: Tell the user how to get task status
NEW_TASK_CREATED_TEMPLATE = """{header}\n
{task}"""

CANCEL_BUTTON = "❌ Cancel"
CREATE_TASK_BUTTON = "❇️ Create task"
NEW_SHELTER_BUTTON = "⛺️ Shelter"
NEW_TRANSPORT_BUTTON = "🚗 Transport"
NEW_VOLUNTEER_BUTTON = "🙋 Volunteer"
NEW_QUESTION_BUTTON = "❔ Question"
NEW_OTHER_BUTTON = "Other"

NEW_TASK_MARKUP = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(NEW_SHELTER_BUTTON, callback_data=action_select(Task.SHELTER)),
        InlineKeyboardButton(NEW_TRANSPORT_BUTTON, callback_data=action_select(Task.TRANSPORT)),
    ],
    # TODO: Implement these task types
    # [
    #     InlineKeyboardButton(NEW_VOLUNTEER_BUTTON, callback_data=action_select(Task.VOLUNTEER)),
    #     InlineKeyboardButton(NEW_QUESTION_BUTTON, callback_data=action_select(Task.QUESTION)),
    #     InlineKeyboardButton(NEW_OTHER_BUTTON, callback_data=action_select(Task.OTHER)),
    # ],
    [
        InlineKeyboardButton(CANCEL_BUTTON, callback_data=Action.CANCEL),
    ],
])

# TODO: Add "Back" button
NEW_TASK_INPUT_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(CANCEL_BUTTON, callback_data=Action.CANCEL),
]])

def new_task_confirmation_markup(task_kind, task_text):
    # TODO: Add "Edit" button
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(CANCEL_BUTTON, callback_data=Action.CANCEL),
        InlineKeyboardButton(CREATE_TASK_BUTTON, callback_data=Action.CREATE),
    ]])


def new_task(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        update.message.from_user.id,
        NEW_TASK_KIND_SELECTION_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=NEW_TASK_MARKUP,
    )

def on_button_tap(
        update: Update, context: CallbackContext,
        db: DB, new_task_states: NewTaskStateMap) -> None:
    data = update.callback_query.data
    update.callback_query.answer()  # stop the client-side loading animation
    user = update.effective_user  # TODO: Can the user be `None`?
    chat = update.effective_chat  # TODO: Can the chat be `None`?
    assert(isinstance(user, User))
    assert(isinstance(chat, Chat))

    match data.split("/"):
        case [Action.CANCEL]:
            new_task_states.pop(user.id, None)
            context.bot.send_message(
                chat.id,
                CANCELLED_TEXT,
                ParseMode.HTML,
            )
        case [Action.SELECT, task_kind]:
            new_task_states[user.id] = NewTaskState()
            new_task_states[user.id].kind = task_kind
            update.callback_query.message.edit_text(
                NEW_TASK_INPUT_TEXT[task_kind],
                ParseMode.HTML,
                reply_markup=NEW_TASK_INPUT_MARKUP,
            )
        case [Action.CREATE]:
            task_kind = new_task_states[user.id].kind
            task_text = new_task_states[user.id].text
            # Write operations should be serialized by the user to avoid data corruption.
            # (from https://docs.python.org/3/library/sqlite3.html#sqlite3.connect)
            with db.lock:
                # Always use placeholders instead of string formatting to bind Python values
                # to SQL statements, to avoid SQL injection attacks.
                # (from https://docs.python.org/3/library/sqlite3.html#tutorial)
                db.cur.execute(
                    "INSERT INTO tasks(kind, text, status, creator_id) VALUES(?, ?, ?, ?)",
                    (task_kind, task_text, TaskStatus.UNASSIGNED, user.id)
                )
            new_task_states.pop(user.id, None)
            message_text = NEW_TASK_CREATED_TEMPLATE.format(
                header=NEW_TASK_CREATED_TEXT[task_kind],
                task=task_text,
            )
            context.bot.send_message(
                chat.id,
                message_text,
                ParseMode.HTML,
            )

def on_message(
        update: Update, context: CallbackContext,
        new_task_states: NewTaskStateMap) -> None:
    user = update.message.from_user
    task_kind = new_task_states[user.id].kind
    if task_kind is None:
        # TODO: Do something about unexpected messages
        return
    task_text = update.message.text  # TODO: Escape (or validate) HTML
    new_task_states[user.id].text = task_text
    # TODO: Test that non-username mentions work
    user_mention = f"@{user.username}" or f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    message_text = NEW_TASK_CONFIRMATION_TEMPLATE.format(
        header=NEW_TASK_CONFIRMATION_TEXT[task_kind],
        user=user_mention,
        task=task_text,
    )
    context.bot.send_message(
        update.message.chat_id,
        message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=new_task_confirmation_markup(task_kind, task_text),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    db = DB()
    # TODO: Make hashtags searchable
    # TODO: Full status change history (instead of assigned_ts / closed_ts)
    db.cur.execute("""CREATE TABLE IF NOT EXISTS tasks(
        kind TEXT,
        text TEXT,
        status TEXT,
        creator_id INTEGER,
        assignee_id INTEGER,
        created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_ts TIMESTAMP,
        closed_ts TIMESTAMP
    )""")

    # The kind of the task this user is currently creating.
    # TODO:
    #   - save to persistent storage,
    #   - or find a way to extract this info from chat (akin to callback_data),
    #   - or at least add a way to monitor the dict, so that we can only restart the bot when it's empty.
    #   - consider https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data
    #     plus https://github.com/python-telegram-bot/python-telegram-bot/wiki/Making-your-bot-persistent
    new_task_states: NewTaskStateMap = {}

    with open('volunteer_request_bot.key') as f:
        token = f.read().strip()
    updater = Updater(token)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    # TODO: Support "/help" command as per https://core.telegram.org/bots/features#global-commands
    dispatcher.add_handler(CommandHandler("newtask", new_task))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(
        partial(on_button_tap, db=db, new_task_states=new_task_states)))

    # Register handler for text input (except commands)
    dispatcher.add_handler(MessageHandler(~Filters.command,
        partial(on_message, new_task_states=new_task_states)))

    # TODO: Smoother solution:
    #   - A "New task" button
    #   - Permanent "New task" dialog
    #   - Separate command for each task type
    dispatcher.bot.set_my_commands([
        BotCommand("newtask", "Create new task")
    ])

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
