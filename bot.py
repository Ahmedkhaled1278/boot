import os
import telebot
import google.generativeai as genai
import io
import zipfile
import re
from telebot import types

# ==========================================
# إعدادات الأمير المتمرد - التعديل الاحترافي
# ==========================================

# سحب التوكن أوتوماتيك من متغيرات البيئة في Railway
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_data = {}

# --- دالة المحرك الذكي (Gemini Engine) ---
def get_ai_response(user_id, prompt):
    # التأكد من وجود المفتاح في بيانات المستخدم أو في متغيرات البيئة
    api_key = user_data.get(user_id, {}).get('api_key') or os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        return "⚠️ خطأ: لم يتم العثور على مفتاح API الخاص بك."
    
    try:
        genai.configure(api_key=api_key)
        # تم التغيير لـ flash لضمان الاستقرار وسرعة الرد
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=(
                "أنت 'مهندس البرمجيات الأمير المتمرد'. بصمتك هي الكمال. "
                "عند بناء أي مشروع، يجب أن تكتب كل سطر برمجي "
                "ليكون المشروع كاملاً 100% وجاهزاً للتشغيل الفوري. "
                "ممنوع استخدام التعليقات مثل '// اكتب الكود هنا'. "
                "يجب إرفاق ملفات تشغيل المشروع بضغطة واحدة. "
                "تنسيق الملفات الإلزامي: "
                "---FILE: path/to/file.ext--- \n [الكود الكامل] \n ---END FILE---"
            )
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ فشل الاتصال بمفتاح API: {str(e)}"

# --- دالة ضغط الملفات (The Zipper) ---
def extract_and_zip(project_name, ai_text):
    zip_buffer = io.BytesIO()
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", ai_text, re.DOTALL)
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        if not files:
            zf.writestr(f"{project_name}/Response_Log.txt", ai_text)
        for filepath, content in files:
            zf.writestr(f"{project_name}/{filepath.strip()}", content.strip())
            
    zip_buffer.seek(0)
    return zip_buffer

# --- معالجة الأوامر والرسائل ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton('🔑 إضافة / تغيير Google API Key'))
    
    welcome_msg = (
        "مرحباً بك في مصنع برمجيات **الأمير المتمرد**! ⚔️🔥\n\n"
        "هنا نقوم ببناء المشاريع الضخمة وتطوير الأكواد المستحيلة.\n"
        "للبدء، أضف مفتاح API الخاص بك من جوجل."
    )
    bot.send_message(user_id, welcome_msg, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🔑 إضافة / تغيير Google API Key')
def ask_api(message):
    msg = bot.send_message(message.chat.id, "أرسل الآن مفتاح Google Gemini API Key الخاص بك:")
    bot.register_next_step_handler(msg, save_api)

def save_api(message):
    key = message.text.strip()
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    user_data[message.chat.id]['api_key'] = key
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('🚀 بناء مشروع ضخم', '🛠️ فحص وإصلاح كود')
    bot.send_message(message.chat.id, "✅ تم تفعيل ترسانة الأمير المتمرد بمفتاحك الخاص. ماذا سنفعل الآن؟", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['🚀 بناء مشروع ضخم', '🛠️ فحص وإصلاح كود'])
def action_select(message):
    user_id = message.chat.id
    # تعديل الأمان للتأكد من وجود البيانات
    if user_id not in user_data or 'api_key' not in user_data[user_id]:
        # محاولة سحب المفتاح من البيئة لو مش موجود في الداتا
        if not os.getenv('GOOGLE_API_KEY'):
            bot.send_message(user_id, "⚠️ يرجى إضافة مفتاح API أولاً.")
            return
        else:
            if user_id not in user_data: user_data[user_id] = {}
            user_data[user_id]['api_key'] = os.getenv('GOOGLE_API_KEY')
    
    mode = 'build' if 'بناء' in message.text else 'fix'
    user_data[user_id]['mode'] = mode
    
    if mode == 'build':
        bot.send_message(user_id, "أرسل اسم المشروع ووصفاً تفصيلياً (مثلاً: نسخة واتساب كاملة):")
    else:
        bot.send_message(user_id, "أرسل الأكواد التي تريد مني فحصها وإصلاحها:")

@bot.message_handler(func=lambda m: m.chat.id in user_data and 'api_key' in user_data[m.chat.id])
def execute_task(message):
    user_id = message.chat.id
    data = user_data[user_id]
    if 'mode' not in data: return

    status = bot.reply_to(message, "⚙️ الأمير المتمرد يعمل الآن.. جاري المعالجة والبناء...")
    
    try:
        if data['mode'] == 'fix':
            prompt = f"قم بفحص الأخطاء في الكود التالي، أصلحها، وطور الكود ليكون احترافياً وكاملاً: \n\n{message.text}"
            p_name = "Rebel_Fix"
        else:
            p_name = message.text.split('\n')[0].strip()[:20] # اختصار الاسم
            prompt = (
                f"ابني مشروعاً ضخماً وكاملاً باسم {p_name}. "
                f"الوصف والمتطلبات: {message.text}. "
                "يجب أن يكون الكود شاملاً لكل شيء وبدون أي نقص."
            )

        ai_response = get_ai_response(user_id, prompt)
        
        if "---FILE:" in ai_response:
            zip_res = extract_and_zip(p_name, ai_response)
            bot.send_document(
                user_id, zip_res, 
                visible_file_name=f"{p_name}_By_The_Rebel_Prince.zip",
                caption="✅ تم الإنجاز بنجاح! المشروع كامل وبصمة الأمير المتمرد حاضرة. 🔥"
            )
        else:
            bot.reply_to(message, ai_response)
    except Exception as e:
        bot.send_message(user_id, f"❌ حدث خطأ غير متوقع: {str(e)}")
    
    bot.delete_message(user_id, status.message_id)

# تشغيل البوت
print("The Rebel Prince Factory is Running on Railway...")
bot.infinity_polling()

