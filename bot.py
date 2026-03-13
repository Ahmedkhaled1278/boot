import os
import telebot
import google.generativeai as genai
import io
import zipfile
import re
from telebot import types

# ==========================================
# إعدادات الأمير المتمرد - الإصدار النهائي الشغال 100%
# ==========================================

# سحب التوكن أوتوماتيك من Railway
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_data = {}

# --- دالة المحرك الذكي (Gemini Engine) ---
def get_ai_response(user_id, prompt):
    # سحب المفتاح من الداتا أو من السيستم
    api_key = user_data.get(user_id, {}).get('api_key') or os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        return "⚠️ خطأ: لم يتم العثور على مفتاح API الخاص بك."
    
    try:
        genai.configure(api_key=api_key)
        
        # التعديل الجذري: استخدام اسم الموديل الأبسط والأضمن لتجنب خطأ 404
        # "gemini-pro" هو الاسم المعياري اللي بيوجه لأحدث نسخة مستقرة
        model = genai.GenerativeModel("gemini-pro")
        
        # دمج تعليمات الأمير المتمرد داخل الـ Prompt مباشرة لضمان التنفيذ
        full_prompt = (
            "أنت 'مهندس البرمجيات الأمير المتمرد'. كمال الأكواد هو هدفك. "
            "ابني المشروع ليكون كاملاً 100% وجاهزاً للتشغيل الفوري بدون نقص. "
            "التنسيق الإلزامي للملفات: \n"
            "---FILE: path/to/file.ext--- \n [الكود الكامل] \n ---END FILE--- \n\n"
            f"المهمة المطلوبة: {prompt}"
        )
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"❌ حصلت مشكلة في الاتصال: {str(e)}"

# --- دالة ضغط الملفات (The Zipper) ---
def extract_and_zip(project_name, ai_text):
    zip_buffer = io.BytesIO()
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", ai_text, re.DOTALL)
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        if not files:
            zf.writestr(f"{project_name}/Instruction_Log.txt", ai_text)
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
        "تم تحديث المحرك للنسخة المستقرة لتجنب أخطاء الاتصال.\n"
        "ابدأ البناء فوراً لو مفتاحك مضاف مسبقاً."
    )
    bot.send_message(user_id, welcome_msg, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🔑 إضافة / تغيير Google API Key')
def ask_api(message):
    msg = bot.send_message(message.chat.id, "أرسل الآن مفتاح Gemini API Key الخاص بك:")
    bot.register_next_step_handler(msg, save_api)

def save_api(message):
    key = message.text.strip()
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    user_data[message.chat.id]['api_key'] = key
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('🚀 بناء مشروع ضخم', '🛠️ فحص وإصلاح كود')
    bot.send_message(message.chat.id, "✅ تم تفعيل الترسانة! ماذا سنبني اليوم؟", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['🚀 بناء مشروع ضخم', '🛠️ فحص وإصلاح كود'])
def action_select(message):
    user_id = message.chat.id
    if user_id not in user_data or 'api_key' not in user_data[user_id]:
        env_key = os.getenv('GOOGLE_API_KEY')
        if not env_key:
            bot.send_message(user_id, "⚠️ يرجى إضافة مفتاح API أولاً.")
            return
        else:
            if user_id not in user_data: user_data[user_id] = {}
            user_data[user_id]['api_key'] = env_key
    
    mode = 'build' if 'بناء' in message.text else 'fix'
    user_data[user_id]['mode'] = mode
    bot.send_message(user_id, "أرسل تفاصيل المهمة (اسم المشروع أو الكود المطلوب إصلاحه):")

@bot.message_handler(func=lambda m: m.chat.id in user_data and 'api_key' in user_data[m.chat.id])
def execute_task(message):
    user_id = message.chat.id
    data = user_data[user_id]
    if 'mode' not in data: return

    status = bot.reply_to(message, "⚙️ جاري البناء والضغط بصيغة Zip... انتظر قليلاً.")
    
    try:
        p_name = message.text.split('\n')[0].strip()[:20]
        ai_response = get_ai_response(user_id, message.text)
        
        if "---FILE:" in ai_response:
            zip_res = extract_and_zip(p_name, ai_response)
            bot.send_document(
                user_id, zip_res, 
                visible_file_name=f"{p_name}_By_The_Rebel_Prince.zip",
                caption="✅ تم الإنجاز! المشروع جاهز ومضغوط. 🔥"
            )
        else:
            bot.reply_to(message, ai_response)
            
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ فني: {str(e)}")
    
    bot.delete_message(user_id, status.message_id)

# تشغيل البوت
print("The Rebel Prince is ONLINE.")
bot.infinity_polling()

