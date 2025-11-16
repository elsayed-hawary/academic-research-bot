import os
import logging
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from docx import Document
from groq import Groq
from datetime import datetime
from flask import Flask

# 🔑 مفاتيح API من متغيرات البيئة
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8142771350:AAHG7ZNBsi61XmmMIEspCKnEgfX3gqczhSo')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', 'YOUR_GROQ_API_KEY_HERE')

# 🔧 إعداد الذكاء الاصطناعي
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != 'YOUR_GROQ_API_KEY_HERE' else None

# إعداد Flask للحفاظ على التشغيل
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Academic Research Bot is Running!"

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
        "generating": "🧠 جاري توليد المحتوى باستخدام الذكاء الاصطناعي...",
        "completed": "✅ تم الانتهاء من البحث بنجاح!",
        "choose_export": "📤 اختر صيغة التصدير:"
    },
    "en": {
        "welcome": "Welcome! 👋 Please choose interface language:",
        "research_title": "🔍 Enter research title:",
        "research_description": "📝 Enter research description:",
        "page_count": "📄 Enter number of pages:",
        "research_language": "🌐 Choose research language:",
        "generating": "🧠 Generating content using AI...",
        "completed": "✅ Research completed successfully!",
        "choose_export": "📤 Choose export format:"
    },
    "ru": {
        "welcome": "Добро пожаловать! 👋 Пожалуйста, выберите язык интерфейса:",
        "research_title": "🔍 Введите название исследования:",
        "research_description": "📝 Введите описание исследования:",
        "page_count": "📄 Введите количество страниц:",
        "research_language": "🌐 Выберите язык исследования:",
        "generating": "🧠 Генерация контента с использованием ИИ...",
        "completed": "✅ Исследование успешно завершено!",
        "choose_export": "📤 Выберите формат экспорта:"
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
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

# 🧠 وظيفة الذكاء الاصطناعي
async def generate_ai_content(title, description, language, pages):
    """توليد محتوى باستخدام الذكاء الاصطناعي"""
    
    if not client:
        return generate_fallback_content(title, description, language, pages)
    
    model = "llama3-8b-8192"
    
    if language == 'ar':
        prompt = f"""
        أنت مساعد أكاديمي محترف. أريد منك كتابة بحث أكاديمي باللغة العربية حول الموضوع التالي:
        
        العنوان: {title}
        الوصف: {description}
        عدد الصفحات التقريبي: {pages}
        
        أرجو كتابة بحث أكاديمي متكامل مع:
        - مقدمة
        - إطار نظري
        - منهجية
        - نتائج
        - خاتمة وتوصيات
        
        المحتوى يجب أن يكون احترافياً وأكاديمياً.
        """
    elif language == 'ru':
        prompt = f"""
        Вы профессиональный академический помощник. Мне нужно, чтобы вы написали академическое исследование на русском языке по следующей теме:
        
        Название: {title}
        Описание: {description}
        Примерное количество страниц: {pages}
        
        Пожалуйста, напишите комплексное академическое исследование включающее:
        - Введение
        - Теоретическую основу
        - Методологию
        - Результаты
        - Заключение и рекомендации
        
        Содержание должно быть профессиональным и академическим.
        """
    else:
        prompt = f"""
        You are a professional academic assistant. I want you to write an academic research paper in English on the following topic:
        
        Title: {title}
        Description: {description}
        Approximate pages: {pages}
        
        Please write a comprehensive academic research paper including:
        - Introduction
        - Theoretical Framework
        - Methodology
        - Results
        - Conclusion and Recommendations
        
        The content should be professional and academic.
        """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.7,
            max_tokens=4000
        )
        
        return chat_completion.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error in AI generation: {e}")
        return generate_fallback_content(title, description, language, pages)

def generate_fallback_content(title, description, language, pages):
    """محتوى احتياطي"""
    if language == 'ar':
        return f"""
        المقدمة:
        يمثل موضوع "{title}" أهمية بالغة في المجال الأكاديمي المعاصر. {description}
        
        الإطار النظري:
        يستند هذا البحث إلى مجموعة من النظريات والأطر المفاهيمية الراسخة في الأدبيات الأكاديمية، مما يساهم في تقديم فهم أعمق وأشمل للموضوع المطروح.
        
        المنهجية:
        اعتمد البحث على المنهج الوصفي التحليلي، مع استخدام أدوات جمع البيانات المناسبة التي تضمن الحصول على معلومات دقيقة وموثوقة.
        
        النتائج:
        توصل البحث إلى مجموعة من النتائج المهمة التي تساهم في إثراء المعرفة حول الموضوع، وتقدم إضافات نوعية للمجال المعرفي.
        
        الخاتمة والتوصيات:
        ختم البحث بمجموعة من التوصيات العملية التي يمكن تطبيقها في هذا المجال، مع اقتراحات لبحوث مستقبلية.
        """
    elif language == 'ru':
        return f"""
        Введение:
        Тема "{title}" представляет большую важность в современной академической сфере. {description}
        
        Теоретическая основа:
        Это исследование основано на ряде теорий и концептуальных框架, устоявшихся в академической литературе, что способствует более глубокому и всестороннему пониманию рассматриваемой темы.
        
        Методология:
        Исследование использовало описательно-аналитический метод с применением соответствующих инструментов сбора данных, обеспечивающих получение точной и надежной информации.
        
        Результаты:
        Исследование пришло к ряду важных выводов, которые обогащают знания по теме и вносят качественный вклад в область знаний.
        
        Заключение и рекомендации:
        Исследование завершается рядом практических рекомендаций, которые могут быть применены в этой области, с предложениями для будущих исследований.
        """
    else:
        return f"""
        Introduction:
        The topic of "{title}" is of great importance in the contemporary academic field. {description}
        
        Theoretical Framework:
        This research is based on a set of well-established theories and conceptual frameworks in academic literature, contributing to a deeper and more comprehensive understanding of the subject.
        
        Methodology:
        The research adopted the descriptive analytical approach, using appropriate data collection tools that ensure accurate and reliable information.
        
        Results:
        The research reached a set of important results that contribute to enriching knowledge about the topic and provide qualitative additions to the field of knowledge.
        
        Conclusion and Recommendations:
        The research concluded with a set of practical recommendations that can be applied in this field, along with suggestions for future research.
        """

def create_word_document(content, title, language):
    """إنشاء مستند Word"""
    doc = Document()
    
    # إضافة العنوان الرئيسي
    title_heading = doc.add_heading(title, 0)
    
    # إضافة تاريخ الإنشاء
    doc.add_paragraph(f"تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph()  # سطر فارغ
    
    # معالجة المحتوى
    sections = content.split('\n\n')
    for section in sections:
        if section.strip():
            if ':' in section:
                section_title, section_content = section.split(':', 1)
                # إضافة عنوان القسم
                doc.add_heading(section_title.strip(), level=1)
                # إضافة محتوى القسم
                doc.add_paragraph(section_content.strip())
            else:
                doc.add_paragraph(section.strip())
            doc.add_paragraph()  # سطر فارغ بين الأقسام
    
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
                 "الوصف: {}\n"
                 "الصفحات: {}\n"
                 "لغة البحث: {}\n\n"
                 "جاهز لتوليد البحث 📝".format(
                     user_data.get('research_title', 'N/A'),
                     user_data.get('research_description', 'N/A')[:100] + "...",
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
    
    # توليد المحتوى باستخدام الذكاء الاصطناعي
    content = await generate_ai_content(
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

def run_bot():
    """تشغيل بوت التلجرام"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت يعمل الآن على Render!")
    application.run_polling()

def run_flask():
    """تشغيل خادم Flask"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

async def main():
    """الدالة الرئيسية"""
    # تشغيل البوت في خلفية
    import threading
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل Flask في المقدمة
    run_flask()

if __name__ == '__main__':
    # للتشغيل المحلي
    run_bot()
