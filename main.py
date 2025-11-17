import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
from docx import Document
from datetime import datetime

# 🔑 مفاتيح API من متغيرات البيئة
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8142771350:AAHG7ZNBsi61XmmMIEspCKnEgfX3gqczhSo')

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# النصوص متعددة اللغات
TEXTS = {
    "ar": {
        "welcome": "مرحباً! 👋 يرجى اختيار لغة الواجهة:",
        "research_title": "🔍 أدخل عنوان البحث:",
        "research_description": "📝 أدخل وصف البحث:",
        "page_count": "📄 أدخل عدد الصفحات:",
        "research_language": "🌐 اختر لغة البحث:",
        "generating": "📝 جاري إنشاء البحث...",
        "completed": "✅ تم الانتهاء من البحث بنجاح!"
    },
    "en": {
        "welcome": "Welcome! 👋 Please choose interface language:",
        "research_title": "🔍 Enter research title:",
        "research_description": "📝 Enter research description:",
        "page_count": "📄 Enter number of pages:",
        "research_language": "🌐 Choose research language:",
        "generating": "📝 Generating research...",
        "completed": "✅ Research completed successfully!"
    }
}

# قاعدة البيانات
def init_database():
    conn = sqlite3.connect('research_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_database()

def save_user_language(user_id, language):
    conn = sqlite3.connect('research_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, language) 
        VALUES (?, ?)
    ''', (user_id, language))
    conn.commit()
    conn.close()

# إنشاء محتوى البحث
def generate_research_content(title, description, language, pages):
    """إنشاء محتوى البحث"""
    if language == 'ar':
        return f"""
        المقدمة:
        يمثل موضوع "{title}" أهمية بالغة في المجال الأكاديمي. {description}
        
        الإطار النظري:
        يستند هذا البحث إلى مجموعة من النظريات والأطر المفاهيمية الراسخة.
        
        المنهجية:
        اعتمد البحث على المنهج الوصفي التحليلي.
        
        النتائج:
        توصل البحث إلى مجموعة من النتائج المهمة.
        
        الخاتمة والتوصيات:
        ختم البحث بمجموعة من التوصيات العملية.
        """
    else:
        return f"""
        Introduction:
        The topic of "{title}" is of great importance in the academic field. {description}
        
        Theoretical Framework:
        This research is based on a set of well-established theories.
        
        Methodology:
        The research adopted the descriptive analytical approach.
        
        Results:
        The research reached a set of important results.
        
        Conclusion and Recommendations:
        The research concluded with practical recommendations.
        """

def create_word_document(content, title, language):
    """إنشاء مستند Word"""
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph()
    
    sections = content.split('\n\n')
    for section in sections:
        if section.strip():
            if ':' in section:
                section_title, section_content = section.split(':', 1)
                doc.add_heading(section_title.strip(), level=1)
                doc.add_paragraph(section_content.strip())
            else:
                doc.add_paragraph(section.strip())
            doc.add_paragraph()
    
    filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc.save(filename)
    return filename

# معالجات البوت
def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
            InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Welcome! 👋 Please choose interface language:",
        reply_markup=reply_markup
    )

def language_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    language = query.data.split("_")[1]
    context.user_data['language'] = language
    context.user_data['step'] = 'research_title'
    
    user_id = query.from_user.id
    save_user_language(user_id, language)
    
    texts = TEXTS[language]
    query.edit_message_text(text=texts['research_title'])

def handle_message(update: Update, context: CallbackContext):
    user_data = context.user_data
    language = user_data.get('language', 'en')
    texts = TEXTS[language]
    step = user_data.get('step', 'research_title')
    
    if step == 'research_title':
        user_data['research_title'] = update.message.text
        user_data['step'] = 'research_description'
        update.message.reply_text(texts['research_description'])
        
    elif step == 'research_description':
        user_data['research_description'] = update.message.text
        user_data['step'] = 'page_count'
        update.message.reply_text(texts['page_count'])
        
    elif step == 'page_count':
        try:
            pages = int(update.message.text)
            if pages <= 0:
                raise ValueError
            user_data['page_count'] = pages
            
            # إنشاء البحث مباشرة بعد إدخال عدد الصفحات
            generate_research(update, context)
            
        except ValueError:
            update.message.reply_text("❌ Please enter a positive integer")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_data = context.user_data
    language = user_data.get('language', 'en')
    
    if query.data.startswith("research_lang_"):
        research_lang = query.data.split("_")[2]
        user_data['research_language'] = research_lang
        generate_research(query, context)
    
    elif query.data == "restart":
        start_from_beginning(query, context)

def generate_research(update, context):
    if hasattr(update, 'message'):
        # إذا كان من رسالة
        user_data = context.user_data
        message = update.message
    else:
        # إذا كان من callback query
        user_data = context.user_data
        message = update
    
    language = user_data.get('language', 'en')
    texts = TEXTS[language]
    
    if hasattr(update, 'edit_message_text'):
        update.edit_message_text(texts['generating'])
    else:
        message.reply_text(texts['generating'])
    
    # إنشاء المحتوى
    content = generate_research_content(
        user_data.get('research_title', 'Academic Research'),
        user_data.get('research_description', 'Research description'),
        user_data.get('research_language', 'en'),
        user_data.get('page_count', 5)
    )
    
    # إنشاء ملف Word
    filename = create_word_document(
        content,
        user_data.get('research_title', 'Academic Research'),
        user_data.get('research_language', 'en')
    )
    
    # إرسال الملف
    with open(filename, 'rb') as file:
        if hasattr(update, 'message'):
            update.message.reply_document(
                document=file,
                caption=texts['completed']
            )
        else:
            context.bot.send_document(
                chat_id=update.message.chat_id if hasattr(update, 'message') else update.effective_chat.id,
                document=file,
                caption=texts['completed']
            )
    
    # تنظيف الملف
    import os
    os.remove(filename)
    
    # عرض خيار البدء من جديد
    keyboard = [[InlineKeyboardButton("🔄 Create New Research", callback_data="restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message'):
        update.message.reply_text(
            "🎉 Completed! Want to create new research?",
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🎉 Completed! Want to create new research?",
            reply_markup=reply_markup
        )

def start_from_beginning(update, context):
    context.user_data.clear()
    keyboard = [
        [
            InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
            InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'edit_message_text'):
        update.edit_message_text(
            "Choose interface language:",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "Choose interface language:",
            reply_markup=reply_markup
        )

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        # استخدام Updater بدلاً من Application
        updater = Updater(BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # إضافة المعالجات
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CallbackQueryHandler(button_handler))
        dispatcher.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
        dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 Bot started successfully!")
        print("✅ Bot is running!")
        
        # بدء البوت
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()