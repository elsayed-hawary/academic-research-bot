import os
import logging
import sqlite3
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from docx import Document
from groq import Groq
from datetime import datetime
from flask import Flask

# 🔑 مفاتيح API من متغيرات البيئة
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8142771350:AAHG7ZNBsi61XmmMIEspCKnEgfX3gqczhSo')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', 'AAHG7ZNBsi61XmmMIEspCKnEgfX3gqczhSo')

# 🔧 إعداد الذكاء الاصطناعي
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != 'YOUR_GROQ_API_KEY_HERE' else None

# 🔥 إعداد Flask - هذا هو التصحيح الرئيسي
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Academic Research Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy and running!"

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
    conn = sqlite3.connect('/tmp/research_bot.db')  # استخدام /tmp في Render
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
    conn = sqlite3.connect('/tmp/research_bot.db')
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
        
        أرجو كتابة بحث أكاديمي متكامل.
        """
    elif language == 'ru':
        prompt = f"""
        Вы профессиональный академический помощник. Мне нужно, чтобы вы написали академическое исследование на русском языке по следующей теме:
        
        Название: {title}
        Описание: {description}
        Примерное количество страниц: {pages}
        
        Пожалуйста, напишите комплексное академическое исследование.
        """
    else:
        prompt = f"""
        You are a professional academic assistant. I want you to write an academic research paper in English on the following topic:
        
        Title: {title}
        Description: {description}
        Approximate pages: {pages}
        
        Please write a comprehensive academic research paper.
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
        يمثل موضوع "{title}" أهمية بالغة في المجال الأكاديمي. {description}
        
        الإطار النظري:
        يستند هذا البحث إلى مجموعة من النظريات والأطر المفاهيمية.
        
        المنهجية:
        اعتمد البحث على المنهج الوصفي التحليلي.
        
        النتائج:
        توصل البحث إلى نتائج مهمة تساهم في إثراء المعرفة.
        
        الخاتمة:
        ختم البحث بمجموعة من التوصيات العملية.
        """
    elif language == 'ru':
        return f"""
        Введение:
        Тема "{title}" представляет большую важность в академической сфере. {description}
        
        Теоретическая основа:
        Это исследование основано на ряде теорий и концептуальных框架.
        
        Методология:
        Исследование использовало описательно-аналитический метод.
        
        Результаты:
        Исследование пришло к важным выводам.
        
        Заключение:
        Исследование завершается рядом практических рекомендаций.
        """
    else:
        return f"""
        Introduction:
        The topic of "{title}" is of great importance. {description}
        
        Theoretical Framework:
        This research is based on a set of theories.
        
        Methodology:
        The research adopted descriptive analytical approach.
        
        Results:
        The research reached important results.
        
        Conclusion:
        The research concluded with practical recommendations.
        """

def create_word_document(content, title, language):
    """إنشاء مستند Word"""
    doc = Document()
    doc.add_heading(title, 0)
    
    for section in content.split('\n\n'):
        if section.strip():
            if ':' in section:
                section_title, section_content = section.split(':', 1)
                doc.add_heading(section_title.strip(), level=1)
                doc.add_paragraph(section_content.strip())
            else:
                doc.add_paragraph(section.strip())
    
    filename = f"/tmp/research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
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
            text="✅ تم إدخال جميع البيانات جاهز لتوليد البحث",
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
    
    content = await generate_ai_content(
        user_data.get('research_title', 'بحث أكاديمي'),
        user_data.get('research_description', 'وصف البحث'),
        user_data.get('research_language', 'ar'),
        user_data.get('page_count', 5)
    )
    
    filename = create_word_document(
        content,
        user_data.get('research_title', 'بحث أكاديمي'),
        user_data.get('research_language', 'ar')
    )
    
    with open(filename, 'rb') as file:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file,
            caption=texts['completed']
        )
    
    import os
    os.remove(filename)
    
    keyboard = [[InlineKeyboardButton("🔄 إنشاء بحث جديد", callback_data="restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🎉 هل تريد إنشاء بحث جديد؟",
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
        "اختر لغة الواجهة:",
        reply_markup=reply_markup
    )

def run_bot():
    """تشغيل بوت التلجرام في thread منفصل"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 البوت يعمل الآن على Render!")
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in bot: {e}")

def run_flask():
    """تشغيل Flask"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # تشغيل البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل Flask في thread الرئيسي
    run_flask()