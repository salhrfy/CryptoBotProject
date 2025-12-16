
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- إعدادات ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTOCOMPARE_API_KEY = os.environ.get("CRYPTOCOMPARE_API_KEY")

# --- دوال جلب البيانات (تبقى كما هي) ---
def get_top_10_coins():
    url = f"https://min-api.cryptocompare.com/data/top/totalvolfull?limit=10&tsym=USD&api_key={CRYPTOCOMPARE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get('Data', [])
        message = "🔝 **أشهر 10 عملات رقمية حسب حجم التداول:**\n\n"
        for i, coin in enumerate(data):
            info = coin.get('CoinInfo', {})
            raw = coin.get('RAW', {}).get('USD', {})
            price = raw.get('PRICE', 'N/A')
            change_pct = raw.get('CHANGEPCT24HOUR', 0)
            symbol = info.get('Name', 'N/A')
            emoji = "📈" if change_pct >= 0 else "📉"
            message += f"{i+1}. **{info.get('FullName', 'N/A')} ({symbol})**\n"
            message += f"   - السعر: ${price:,.2f}\n"
            message += f"   - التغيير (24 ساعة): {change_pct:.2f}% {emoji}\n\n"
        return message
    except Exception:
        return "حدث خطأ أثناء جلب البيانات."

def get_fear_and_greed_index():
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1")
        response.raise_for_status()
        data = response.json()['data'][0]
        value = int(data['value'])
        classification = data['value_classification']
        emoji = "😨" if value < 30 else "🤔" if value < 70 else "🤑"
        message = f"📊 **مؤشر الخوف والطمع الحالي:**\n\n**{value} - {classification} {emoji}**"
        return message
    except Exception:
        return "حدث خطأ أثناء جلب المؤشر."

# --- دوال واجهة المستخدم ---
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔝 أشهر 10 عملات", callback_data='top10')],
        [InlineKeyboardButton("📊 مؤشر الخوف والطمع", callback_data='fng')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"أهلاً بك يا {user.mention_html()} في بوت العملات الرقمية! 🤖\n\n"
        "البوت قيد التطوير حالياً. هذه هي الميزات المتاحة:"
    )
    # التأكد من أن update.message ليس None
    if update.message:
        await update.message.reply_html(
            welcome_message,
            reply_markup=get_main_menu_keyboard(),
        )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    welcome_message = "القائمة الرئيسية. اختر أحد الخيارات."
    await query.edit_message_text(
        text=welcome_message,
        reply_markup=get_main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message_text = ""
    if query.data == 'top10':
        message_text = get_top_10_coins()
    elif query.data == 'fng':
        message_text = get_fear_and_greed_index()

    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu')]]
    await query.edit_message_text(
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

# --- الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(top10|fng)$'))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern='^main_menu$'))

    print("البوت المبسط قيد التشغيل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
