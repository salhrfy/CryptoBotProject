import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

# تفعيل تسجيل الأخطاء لرؤية المشاكل بوضوح
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- الإعدادات الرئيسية ---
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    CRYPTOCOMPARE_API_KEY = os.environ["CRYPTOCOMPARE_API_KEY"]
except KeyError:
    logger.error("خطأ فادح: لم يتم العثور على BOT_TOKEN أو CRYPTOCOMPARE_API_KEY في متغيرات البيئة!")
    exit() # إيقاف البوت فوراً إذا كانت المفاتيح غير موجودة

# --- تعريف حالات المحادثة ---
STATE_GET_PRICE = 1
STATE_GET_CONVERT_FROM = 2
STATE_GET_CONVERT_TO = 3
STATE_GET_CONVERT_AMOUNT = 4

# ====================================================================
# 1. دوال جلب البيانات (المنطق الخلفي)
# ====================================================================

def get_api_data(url: str) -> dict | None:
    """دالة موحدة لجلب البيانات من أي API مع معالجة الأخطاء."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # يثير خطأ في حالة 4xx أو 5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في طلب الـ API لـ {url}: {e}")
        return None

def get_top_10_coins() -> str:
    url = f"https://min-api.cryptocompare.com/data/top/totalvolfull?limit=10&tsym=USD&api_key={CRYPTOCOMPARE_API_KEY}"
    data = get_api_data(url)
    if not data or 'Data' not in data:
        return "عذراً، لم أتمكن من جلب أشهر العملات حالياً."
    
    message = "🔝 **أشهر 10 عملات رقمية حسب حجم التداول:**\n\n"
    for i, coin in enumerate(data['Data']):
        info = coin.get('CoinInfo', {})
        raw = coin.get('RAW', {}).get('USD', {})
        price = raw.get('PRICE', 0)
        change_pct = raw.get('CHANGEPCT24HOUR', 0)
        emoji = "📈" if change_pct >= 0 else "📉"
        message += (
            f"{i+1}. **{info.get('FullName', 'N/A')} ({info.get('Name', 'N/A')})**\n"
            f"   - السعر: ${price:,.2f}\n"
            f"   - التغيير (24 ساعة): {change_pct:.2f}% {emoji}\n\n"
        )
    return message

def get_fear_and_greed_index() -> str:
    url = "https://api.alternative.me/fng/?limit=1"
    data = get_api_data(url)
    if not data or 'data' not in data:
        return "عذراً، لم أتمكن من جلب مؤشر الخوف والطمع."
        
    value = int(data['data'][0]['value'])
    classification = data['data'][0]['value_classification']
    emoji = "😨" if value < 30 else "🤔" if value < 70 else "🤑"
    return (
        f"📊 **مؤشر الخوف والطمع الحالي:**\n\n"
        f"**{value} - {classification} {emoji}**\n\n"
        "هذا المؤشر يساعد في قياس معنويات السوق."
    )

def get_crypto_news() -> str:
    url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=AR&api_key={CRYPTOCOMPARE_API_KEY}"
    data = get_api_data(url)
    if not data or 'Data' not in data:
        return "عذراً، لم أتمكن من جلب آخر الأخبار."

    message = "📰 **آخر 5 أخبار في عالم العملات الرقمية:**\n"
    for item in data['Data'][:5]:
        message += f"\n- [{item['title']}]({item['url']})"
    return message

def get_single_price(coin_id: str) -> str:
    url = f"https://min-api.cryptocompare.com/data/price?fsym={coin_id.upper()}&tsyms=USD&api_key={CRYPTOCOMPARE_API_KEY}"
    data = get_api_data(url)
    if not data or 'USD' not in data:
        return f"لم أتمكن من العثور على سعر العملة '{coin_id}'. يرجى التأكد من الرمز (مثال: BTC)."
    return f"سعر **{coin_id.upper()}** الحالي هو: **${data['USD']:,.2f}**"

# ====================================================================
# 2. دوال واجهة المستخدم (الأوامر والأزرار)
# ====================================================================

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """إنشاء وعرض لوحة المفاتيح الرئيسية."""
    keyboard = [
        [InlineKeyboardButton("📈 عرض السعر", callback_data='price')],
        [InlineKeyboardButton("🔝 أشهر 10 عملات", callback_data='top10')],
        [InlineKeyboardButton("📊 مؤشر الخوف والطمع", callback_data='fng')],
        [InlineKeyboardButton("📰 آخر الأخبار", callback_data='news')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دالة البدء الرئيسية عند إرسال /start."""
    user = update.effective_user
    welcome_message = (
        f"أهلاً بك يا {user.mention_html()} في بوت مرصد العملات الرقمية! 🤖\n\n"
        "اختر أحد الخيارات من القائمة أدناه للبدء."
    )
    if update.message:
        await update.message.reply_html(welcome_message, reply_markup=get_main_menu_keyboard())

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دالة العودة إلى القائمة الرئيسية."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="القائمة الرئيسية. اختر أحد الخيارات.",
        reply_markup=get_main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأزرار البسيطة (الأخبار، أشهر العملات، الخوف والطمع)."""
    query = update.callback_query
    await query.answer()
    
    actions = {
        'top10': get_top_10_coins,
        'fng': get_fear_and_greed_index,
        'news': get_crypto_news,
    }
    
    if query.data in actions:
        message_text = actions[query.data]()
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu')]]),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

# --- محادثة عرض السعر ---
async def price_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ محادثة طلب السعر."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="الرجاء إرسال رمز العملة التي تريد معرفة سعرها (مثال: BTC).")
    return STATE_GET_PRICE

async def price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يستقبل رمز العملة ويعرض السعر."""
    coin_id = update.message.text
    result_message = get_single_price(coin_id)
    await update.message.reply_text(
        result_message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main_menu_repost')]]),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يلغي المحادثة الحالية."""
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def main_menu_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعيد نشر القائمة الرئيسية كرسالة جديدة بعد انتهاء محادثة."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("القائمة الرئيسية. اختر أحد الخيارات.", reply_markup=get_main_menu_keyboard())


# ====================================================================
# 3. الدالة الرئيسية (نقطة انطلاق البوت)
# ====================================================================
def main() -> None:
    """الدالة الرئيسية التي تقوم بتشغيل البوت."""
    logger.info("البوت قيد التشغيل...")
    
    application = Application.builder().token(BOT_TOKEN).build()

    # --- إضافة معالجات الأوامر والأزرار ---
    
    # 1. معالج المحادثة لطلب السعر
    price_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(price_start, pattern='^price$')],
        states={
            STATE_GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_input)]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )

    # 2. إضافة جميع المعالجات إلى التطبيق
    application.add_handler(CommandHandler("start", start))
    application.add_handler(price_conversation)
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(top10|fng|news)$'))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(main_menu_repost, pattern='^main_menu_repost$'))

    # 3. تشغيل البوت
    application.run_polling()

if __name__ == "__main__":
    main()


