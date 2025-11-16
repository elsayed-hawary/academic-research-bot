import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
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
    },
    "ru": {
        "welcome": "Добро пожаловать! 👋 Пожалуйста, выберите язык интерфейса:",
        "research_title": "🔍 Введите название исследования:",
        "research_description": "📝 Введите описание исследования:",
        "page_count": "📄 Введите количество страниц:",
        "research_language": "🌐 Выберите язык исследования:",
        "generating": "📝 Генерация исследования...",
        "completed": "✅ Исследование успешно завершено!"
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
    """إنشاء محتوى البحث بدون الذكاء الاصطناعي"""
    if language == 'ar':
        return f"""
        المقدمة:
        يمثل موضوع "{title}" أهمية بالغة في المجال الأكاديمي. {description}
        
        الإطار النظري:
        يستند هذا البحث إلى مجموعة من النظريات والأطر المفاهيمية الراسخة في الأدبيات الأكاديمية.
        
        المنهجية:
        اعتمد البحث على المنهج الوصفي التحليلي، مع استخدام أدوات جمع البيانات المناسبة.
        
        النتائج:
        توصل البحث إلى مجموعة من النتائج المهمة التي تساهم في إثراء المعرفة حول الموضوع.
        
        الخاتمة والتوصيات:
        ختم البحث بمجموعة من التوصيات العملية التي يمكن تطبيقها في هذا المجال.
        """
    elif language == 'ru':
        return f"""
        Введение:
        Тема "{title}" представляет большую важность в академической сфере. {description}
        
        Теоретическая основа:
        Это исследование основано на ряде теорий и концептуальных框架, устоявшихся в академической литературе.
        
        Методология:
        Исследование использовало описательно-аналитический метод с применением соответствующих инструментов сбора данных.
        
        Результаты:
        Исследование пришло к ряду важных выводов, которые обогащают знания по теме.
        
        Заключение и рекомендации:
        Исследование завершается рядом практических рекомендаций, которые могут быть применены в этой области.
        """
    else:
        return f"""
        Introduction:
        The topic of "{title}" is of great importance in the academic field. {description}
        
        Theoretical Framework:
        This research is based on a set of well-established theories and conceptual frameworks in academic literature.
        
        Methodology:
        The research adopted the descriptive analytical approach, using appropriate data collection tools.
        
        Results:
        The research reached a set of important results that contribute to enriching knowledge about the topic.
        
        Conclusion and Recommendations:
        The research concluded with a set of practical recommendations that can be applied in this field.
        """

def create_word_document(content, title, language):
    """إنشاء مستند Word"""
    doc = Document()
    
    # إضافة العنوان الرئيسي
    doc.add_heading(title, 0)
    
    # إضافة تاريخ الإنشاء
    doc.add_paragraph(f"تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph()
    
    # معالجة المحتوى
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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
            InlineKeyboardButton("English 🇺🇸", callback_data="lang_en"),
            InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome! 👋 Please choose interface language:\n\n"
        "مرحباً! 👋 يرجى اختيار لغة الواجهة:\n\n"
        "Добро пожаловать! 👋 Пожалуйста, выберите язык интерфейса:",
        reply_markup=reply_markup
    )

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    language = query.data.split("_")[1]
    context.user_data['language'] = language
    context.user_data['step'] = 'research_title'
    
    user_id = query.from_user.id
    save_user_language(user_id, language)
    
    texts = TEXTS[language]
    await query.edit_message_text(text=texts['research_title'])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    language = user_data.get('language', 'en')
    texts = TEXTS[language]
    step = user_data.get('step', 'research_title')
    
    if step == 'research_title':
        user_data['research_title'] = update.message.text
        user_data['step'] = 'research_description'
        await update.message.reply_text(texts['research_description'])
        
    elif step == 'research_description':
        user_data['research_description'] = update.message.text
        user_data['step'] = 'page_count'
        await update.message.reply_text(texts['page_count'])
        
    elif step == 'page_count':
        try:
            pages = int(update.message.text)
            if pages <= 0:
                raise ValueError
            user_data['page_count'] = pages
            user_data['step'] = 'research_language'
            
            keyboard = [
                [InlineKeyboardButton("العربية", callback_data="research_lang_ar")],
                [InlineKeyboardButton("English", callback_data="research_lang_en")],
                [InlineKeyboardButton("Русский", callback_data="research_lang_ru")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(texts['research_language'], reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال عدد صحيح موجب")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_data = context.user_data
    language = user_data.get('language', 'en')
    texts = TEXTS[language]
    
    if query.data.startswith("research_lang_"):
        research_lang = query.data.split("_")[2]
        user_data['research_language'] = research_lang
        
        keyboard = [
            [InlineKeyboardButton("📝 إنشاء البحث", callback_data="generate_research")],
            [InlineKeyboardButton("🔄 إعادة البدء", callback_data="restart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="✅ تم إدخال جميع البيانات!\n\n"
                 "العنوان: {}\n"
                 "الصفحات: {}\n"
                 "لغة البحث: {}\n\n"
                 "جاهز لتوليد البحث 📝".format(
                     user_data.get('research_title', 'N/A'),
                     user_data.get('page_count', 'N/A'),
                     research_lang
                 ),
            reply_markup=reply_markup
        )
    
    elif query.data == "generate_research":
        await generate_research(query, context)
    
    elif query.data == "restart":
        await start_from_beginning(query, context)

async def generate_research(query, context):
    user_data = context.user_data
    language = user_data.get('language', 'en')
    texts = TEXTS[language]
    
    await query.edit_message_text(texts['generating'])
    
    # إنشاء المحتوى
    content = generate_research_content(
        user_data.get('research_title', 'بحث أكاديمي'),
        user_data.get('research_description', 'وصف البحث'),
        user_data.get('research_language', 'ar'),
        user_data.get('page_count', 5)
    )
    
    # إنشاء ملف Word
    filename = create_word_document(
        content,
        user_data.get('research_title', 'بحث أكاديمي'),
        user_data.get('research_language', 'ar')
    )
    
    # إرسال الملف
    with open(filename, 'rb') as file:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file,
            caption=texts['completed'] + "\n\n" + user_data.get('research_title', 'بحث أكاديمي')
        )
    
    # تنظيف الملف
    import os
    os.remove(filename)
    
    # عرض خيار البدء من جديد
    keyboard = [[InlineKeyboardButton("🔄 إنشاء بحث جديد", callback_data="restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🎉 تم الانتهاء بنجاح! هل تريد إنشاء بحث جديد؟",
        reply_markup=reply_markup
    )

async def start_from_beginning(query, context):
    context.user_data.clear()
    keyboard = [
        [
            InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
            InlineKeyboardButton("English 🇺🇸", callback_data="lang_en"),
            InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر لغة الواجهة / Choose interface language / Выберите язык интерфейса:",
        reply_markup=reply_markup
    )

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 البوت يعمل الآن على Render!")
        print("✅ Bot started successfully!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()