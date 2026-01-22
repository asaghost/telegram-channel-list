import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found in environment variables!")
    logger.error("Please set BOT_TOKEN in Railway Variables")
    exit(1)

logger.info(f"✅ BOT_TOKEN found: {BOT_TOKEN[:10]}...")
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@Channlist')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@Channlist')
logger.info(f"✅ Channel: {CHANNEL_USERNAME}")

# Categories
CATEGORIES = ['تعليم', 'تقنية', 'أخبار', 'رياضة', 'ترفيه', 'كتب', 'ربح', 'ألعاب', 'طبخ', 'صحة', 'سفر', 'تصميم']

# Database setup
def init_db():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY, user_id INTEGER, link TEXT UNIQUE, 
                  name TEXT, description TEXT, category TEXT, subscribers INTEGER)''')
    conn.commit()
    conn.close()

def add_channel_db(user_id, link, name, desc, category, subs):
    try:
        conn = sqlite3.connect('channels.db')
        c = conn.cursor()
        c.execute('INSERT INTO channels (user_id, link, name, description, category, subscribers) VALUES (?,?,?,?,?,?)',
                  (user_id, link, name, desc, category, subs))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_channels_by_cat(category):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT * FROM channels WHERE category=? ORDER BY id DESC LIMIT 20', (category,))
    channels = c.fetchall()
    conn.close()
    return channels

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("🔔 اشترك بالقناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        await update.message.reply_text(
            f"⚠️ يجب الاشتراك في قناتنا أولاً!\n\n📢 {CHANNEL_USERNAME}\n\nثم اضغط /start",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("🔍 استعراض القنوات", callback_data="browse")],
        [InlineKeyboardButton("➕ إضافة قناتي", callback_data="add")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    await update.message.reply_text(
        f"مرحباً {update.effective_user.first_name}! 🌟\n\n"
        "أكبر دليل لقنوات التليجرام!\n"
        "ماذا تريد أن تفعل؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "browse":
        keyboard = []
        for cat in CATEGORIES:
            keyboard.append([InlineKeyboardButton(f"📂 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
        await query.edit_message_text("اختر التصنيف:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        channels = get_channels_by_cat(category)
        
        if not channels:
            await query.edit_message_text(f"لا توجد قنوات في {category} حالياً\nكن أول من يضيف!")
            return
        
        msg = f"📋 قنوات {category}:\n\n"
        for ch in channels[:10]:
            msg += f"📢 {ch[3]}\n📝 {ch[4][:50]}...\n🔗 {ch[2]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="browse")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)
    
    elif query.data == "add":
        await query.edit_message_text(
            "➕ لإضافة قناتك:\n\n"
            "أرسل المعلومات بهذا الشكل:\n"
            "/add رابط_القناة | اسم_القناة | الوصف | التصنيف | عدد_المشتركين\n\n"
            "مثال:\n"
            "/add @mychannel | قناتي | وصف القناة | تقنية | 1000"
        )
    
    elif query.data == "help":
        await query.edit_message_text(
            "❓ المساعدة\n\n"
            "🔍 استعراض القنوات: تصفح حسب التصنيف\n"
            "➕ إضافة قناة: أضف قناتك للدليل\n\n"
            f"📢 قناتنا: {CHANNEL_USERNAME}"
        )
    
    elif query.data == "back":
        await start(update, context)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text("⚠️ يجب الاشتراك في القناة أولاً!")
        return
    
    try:
        text = update.message.text.replace('/add ', '')
        parts = [p.strip() for p in text.split('|')]
        
        if len(parts) != 5:
            await update.message.reply_text("❌ صيغة خاطئة! استخدم:\n/add رابط | اسم | وصف | تصنيف | عدد")
            return
        
        link, name, desc, cat, subs = parts
        subs = int(subs)
        
        if cat not in CATEGORIES:
            await update.message.reply_text(f"❌ التصنيف غير صحيح! اختر من: {', '.join(CATEGORIES)}")
            return
        
        if add_channel_db(user_id, link, name, desc, cat, subs):
            await update.message.reply_text(f"✅ تم إضافة القناة بنجاح!\n\n📢 {name}\n📂 {cat}")
        else:
            await update.message.reply_text("❌ القناة موجودة مسبقاً!")
    
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}\n\nاستخدم: /add رابط | اسم | وصف | تصنيف | عدد")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
