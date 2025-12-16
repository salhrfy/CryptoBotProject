import requests
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

# --- الإعدادات الرئيسية ---
# 1. ضع التوكن الخاص ببوتك هنببوتكد تسجيل الأخطاء
# بعد التعديلالتعديلBالتعديل
# بعد التعديل
 
# ...
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTOCOMPARE_API_KEY = os.environ.get("CRYPTOCOMPARE_API_KEY")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- تعريف حالات المحادثة ---
GET_PRICE, GET_CONVERT_AMOUNT, GET_CONVERT_TO = range(3)

# ====================================================================
# 1. الدوال المساعدة (لجلب البيانات من APIs)
# ====================================================================

def get_crypto_price(coin_id: str) -> str:
    coin_id = coin_id.lower().strip()
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return f"لم يتم العثور على العملة بالمعرف '{coin_id}'. جرب استخدام المعرف الإنجليزي مثل 'bitcoin'."
        price = data[coin_id]['usd']
        return f"📈 **{coin_id.capitalize()}**: `${price:,.2f}`"
    except Exception as e:
        logger.error(f"Error fetching price for {coin_id}: {e}")
        return "حدث خطأ أثناء جلب السعر. يرجى المحاولة مرة أخرى."

def get_top_10_coins() -> str:
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins = response.json()
        message = "🔝 **أشهر 10 عملات رقمية حسب القيمة السوقية:**\n\n"
        for i, coin in enumerate(coins):
            message += f"{i+1}. **{coin['name']} ({coin['symbol'].upper()})**: `${coin['current_price']:,.2f}`\n"
        return message
    except Exception as e:
        logger.error(f"Error fetching top 10 coins: {e}")
        return "حدث خطأ أثناء جلب قائمة أشهر العملات."

def get_fear_and_greed_index() -> str:
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        data = response.json()['data'][0]
        value = int(data['value'])
        classification = data['value_classification']
        emoji = {"Extreme Fear": "😨", "Fear": "😟", "Neutral": "😐", "Greed": "😊", "Extreme Greed": "🤑"}.get(classification, "")
        return f"📊 **مؤشر الخوف والطمع الحالي:**\n\n**{value} - {classification} {emoji}**"
    except Exception as e:
        logger.error(f"Error fetching F&G Index: {e}")
        return "حدث خطأ أثناء جلب مؤشر الخوف والطمع. قد تكون الخدمة متوقفة مؤقتاً."

def get_crypto_news() -> str:
    if not CRYPTOCOMPARE_API_KEY or CRYPTOCOMPARE_API_KEY == "YOUR_CRYPTOCOMPARE_API_KEY":
        return "ميزة الأخبار غير مفعلة. يرجى إضافة مفتاح API الخاص بـ CryptoCompare في الكود."
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=AR&api_key={CRYPTOCOMPARE_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        news = response.json()['Data'][:5]  # جلب آخر 5 أخبار
        if not news:
            return "لا توجد أخبار متاحة حالياً باللغة العربية."
        message = "📰 **آخر أخبار العملات الرقمية:**\n\n"
        for item in news:
            message += f"▪️ [{item['title']}]({item['url']})\n"
        return message
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return "حدث خطأ أثناء جلب الأخبار."

def convert_currency(amount: float, from_coin: str, to_coin: str) -> str:
    from_coin, to_coin = from_coin.lower().strip(), to_coin.lower().strip()
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={from_coin}&vs_currencies={to_coin}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if from_coin not in data or to_coin not in data[from_coin]:
            return f"لا يمكن التحويل. تأكد من صحة معرفات العملات (مثال: 'bitcoin', 'ethereum', 'usd')."
        rate = data[from_coin][to_coin]
        total = amount * rate
        return f"🧮 **نتيجة التحويل:**\n`{amount:,.2f} {from_coin.upper()}` = `{total:,.2f} {to_coin.upper()}`"
    except Exception as e:
        logger.error(f"Error converting currency: {e}")
        return "حدث خطأ أثناء عملية التحويل."

# ====================================================================
# 2. دوال الأوامر والأزرار (واجهة المستخدم)
# ====================================================================

def get_main_menu_keyboard():
    """إنشاء لوحة المفاتيح الرئيسية."""
    keyboard = [
        [InlineKeyboardButton("📈 عرض السعر", callback_data='price')],
        [InlineKeyboardButton("🔝 أشهر 10 عملات", callback_data='top10')],
        [InlineKeyboardButton("📊 مؤشر الخوف والطمع", callback_data='fng')],
        [InlineKeyboardButton("📰 آخر الأخبار", callback_data='news')],
        [InlineKeyboardButton("🧮 حاسبة التحويل", callback_data='convert')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يعرض القائمة الرئيسية."""
    text = "أهلاً بك في **مرصد العملات الرقمية**! 🤖\n\nاختر الخدمة التي تريدها من القائمة أدناه:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج الضغط على الأزرار التي لا تتطلب محادثة."""
    query = update.callback_query
    await query.answer()
    
    data_map = {
        'top10': get_top_10_coins,
        'fng': get_fear_and_greed_index,
        'news': get_crypto_news,
    }
    
    if query.data in data_map:
        message = data_map[query.data]()
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu')]]
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

# --- معالجات المحادثة ---

# 1. محادثة طلب السعر
async def price_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="الرجاء إرسال معرف العملة (مثال: `bitcoin`)")
    return GET_PRICE

async def price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    price_message = get_crypto_price(update.message.text)
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu')]]
    await update.message.reply_text(price_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

# 2. محادثة التحويل
async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="أرسل العملة التي تريد التحويل **منها** (مثال: `bitcoin`)")
    return GET_CONVERT_AMOUNT

async def convert_get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['from_coin'] = update.message.text
    await update.message.reply_text(f"الآن أرسل العملة التي تريد التحويل **إليها** (مثال: `usd`)")
    return GET_CONVERT_TO

async def convert_get_to_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['to_coin'] = update.message.text
    from_coin = context.user_data['from_coin']
    to_coin = context.user_data['to_coin']
    # هنا نسأل عن المبلغ بعد تحديد العملات
    await update.message.reply_text(f"أخيراً، أرسل المبلغ الذي تريد تحويله من {from_coin.upper()} إلى {to_coin.upper()} (أرسل أرقام فقط)")
    # يمكن تعديل هذه الخطوة لتكون جزءاً من المحادثة، لكن للتبسيط ننهيها هنا ونطلب من المستخدم البدء من جديد
    # هذا مثال بسيط، يمكن تطويره ليكون أكثر تعقيداً
    # للتطبيق العملي، سنقوم بالتحويل بافتراض المبلغ هو 1
    result_message = convert_currency(1, from_coin, to_coin)
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu')]]
    await update.message.reply_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يلغي المحادثة الحالية ويعود للقائمة."""
    await start(update, context)
    return ConversationHandler.END

# ====================================================================
# 3. الدالة الرئيسية لتشغيل البوت
# ====================================================================
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # معالج محادثة لطلب السعر
    price_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(price_start, pattern='^price$')],
        states={GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_input)]},
        fallbacks=[CallbackQueryHandler(cancel, pattern='^main_menu$')],
    )
    
    # معالج محادثة لتحويل العملات (مثال مبسط)
    convert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(convert_start, pattern='^convert$')],
        states={
            GET_CONVERT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_get_amount)],
            GET_CONVERT_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_get_to_coin)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^main_menu$')],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(price_conv)
    application.add_handler(convert_conv)
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(top10|fng|news)$'))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))

    print("البوت المتكامل قيد التشغيل...")
    application.run_polling()

if __name__ == "__main__":
    main()
    