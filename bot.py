import random
import os
import logging
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import threading
import time

# إعداد التسجيل (Logging) مع مستوى DEBUG
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(),  # إخراج السجلات إلى stdout (لـ Render)
        logging.FileHandler('bot.log')  # حفظ السجلات في ملف (للتحقق المحلي)
    ]
)
logger = logging.getLogger(__name__)

# إعداد Flask
app = Flask(__name__)

@app.route('/')
def home():
    logger.debug("Received request to Flask endpoint")
    return 'Minesweeper Bot is running!'

@app.route('/test-telegram')
def test_telegram():
    logger.debug("Testing Telegram API connectivity")
    try:
        response = requests.get('https://api.telegram.org')
        logger.info(f"Telegram API test: Status {response.status_code}")
        return f"Telegram API test: Status {response.status_code}"
    except Exception as e:
        logger.error(f"Telegram API test failed: {str(e)}", exc_info=True)
        return f"Telegram API test failed: {str(e)}"

@app.route('/debug')
def debug():
    logger.debug("Received request to /debug endpoint")
    token = os.environ.get('BOT_TOKEN', 'Not set')
    status = {
        'token_set': bool(token),
        'token_preview': token[:10] + '...' if token else 'Not set',
        'bot_running': bot_running,
        'last_error': last_bot_error if 'last_bot_error' in globals() else 'None'
    }
    logger.info(f"Debug status: {status}")
    return status

# إعدادات اللعبة
BOARD_SIZE = 8
NUM_MINES = 10
games = {}  # قاموس لتخزين حالة اللعبة
bot_running = False  # متغير لتتبع حالة البوت
last_bot_error = None  # تخزين آخر خطأ

# إنشاء لوحة جديدة
def create_board():
    logger.debug("Creating new Minesweeper board")
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    mines = set()
    while len(mines) < NUM_MINES:
        x, y = random.randint(0, BOARD_SIZE-1), random.randint(0, BOARD_SIZE-1)
        mines.add((x, y))
        board[x][y] = '💣'
    for x, y in mines:
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[nx][ny] != '💣':
                    board[nx][ny] += 1
    display = ['⬜' for _ in range(BOARD_SIZE * BOARD_SIZE)]
    return board, display

# إنشاء لوحة الأزرار
def create_keyboard(game_id, display):
    logger.debug(f"Creating keyboard for game_id: {game_id}")
    keyboard = []
    for i in range(BOARD_SIZE):
        row = []
        for j in range(BOARD_SIZE):
            idx = i * BOARD_SIZE + j
            row.append(InlineKeyboardButton(display[idx], callback_data=f'{game_id}:{i}:{j}'))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# أمر /start
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    logger.info(f"Received /start command from user {user_id}")
    board, display = create_board()
    games[user_id] = {'board': board, 'display': display, 'game_over': False}
    update.message.reply_text('🎮 لعبة Minesweeper! انقر على الأزرار لكشف الخلايا.', reply_markup=create_keyboard(user_id, display))

# معالجة النقر على الأزرار
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    logger.info(f"Button clicked by user {user_id}: {query.data}")
    if user_id not in games or games[user_id]['game_over']:
        query.message.reply_text('ابدأ لعبة جديدة باستخدام /start')
        return

    game_id, x, y = map(int, query.data.split(':'))
    board = games[user_id]['board']
    display = games[user_id]['display']

    idx = x * BOARD_SIZE + y
    if display[idx] != '⬜':
        return

    if board[x][y] == '💣':
        display[idx] = '💥'
        games[user_id]['game_over'] = True
        query.message.edit_reply_markup(reply_markup=create_keyboard(game_id, display))
        query.message.reply_text('💥 انفجر لغم! اللعبة انتهت. ابدأ لعبة جديدة بـ /start')
        return
    else:
        display[idx] = str(board[x][y]) if board[x][y] > 0 else '✅'
        query.message.edit_reply_markup(reply_markup=create_keyboard(game_id, display))
        safe_cells = sum(1 for i in range(BOARD_SIZE) for j in range(BOARD_SIZE) if board[i][j] != '💣')
        opened_cells = sum(1 for cell in display if cell != '⬜')
        if opened_cells == safe_cells:
            games[user_id]['game_over'] = True
            query.message.reply_text('🎉 فزت! كشفت كل الخلايا الآمنة. ابدأ لعبة جديدة بـ /start')

# أمر /help
def help_command(update: Update, context: CallbackContext):
    logger.info("Received /help command")
    update.message.reply_text(
        '🎮 لعبة Minesweeper\n'
        'استخدم /start لبدء لعبة جديدة.\n'
        'انقر على الأزرار لكشف الخلايا.\n'
        '⬜: خلية مغلقة\n'
        '✅: خلية آمنة\n'
        '💣: لغم (تؤدي إلى الخسارة)\n'
        'الأرقام تدل على عدد الألغام المجاورة.'
    )

# الدالة الرئيسية لتشغيل البوت
def main():
    global bot_running, last_bot_error
    logger.debug("Entering main() function")
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN environment variable is not set")
        last_bot_error = "BOT_TOKEN environment variable is not set"
        raise ValueError(last_bot_error)
    logger.info(f"Using bot token: {token[:10]}... (truncated for security)")
    try:
        logger.debug("Initializing Updater")
        updater = Updater(token, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler('start', start))
        dp.add_handler(CommandHandler('help', help_command))
        dp.add_handler(CallbackQueryHandler(button))
        logger.debug("Starting polling")
        updater.start_polling(poll_interval=1.0, timeout=10)
        logger.info("Telegram bot polling started successfully")
        bot_running = True
        updater.idle()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {str(e)}", exc_info=True)
        last_bot_error = str(e)
        bot_running = False
        raise

# تشغيل البوت في خيط منفصل
def run_bot():
    logger.debug("Starting run_bot thread")
    try:
        main()
    except Exception as e:
        logger.error(f"Error in run_bot thread: {str(e)}", exc_info=True)
        global last_bot_error
        last_bot_error = str(e)

if __name__ == '__main__':
    logger.info("Starting Flask server and Telegram bot")
    try:
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        logger.debug("Bot thread started")
        port = int(os.environ.get('PORT', 8000))
        logger.info(f"Starting Flask on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        raise
