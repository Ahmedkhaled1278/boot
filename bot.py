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

# سحب التوكن أوتوماتيك من متغيرات البيئة في Railway
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_data = {}

# --- دالة المحرك الذكي (Gemini Engine) ---
def get_ai_response(user_id, prompt):
    # التأكد من وجود المفتاح
    api_key = user_data.get(user_id, {}).get('api_key') or os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        return "⚠️ خطأ: لم يتم العثور على مفتاح API الخاص بك."
    
    try:
        genai.configure(api_key=api_key)
        
        # التعديل الجوهري: استخدام موديل flash وتصحيح صياغة الاتصال
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # ده الموديل المستقر
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
        
        # إرسال الطلب للموديل
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # لو حصل خطأ 404 أو غيره هيظهر هنا بوضوح
        return f"❌ عذراً يا بطل، حصلت مشكلة في الاتصال: {str(e)}"

# --- دالة ضغط الملفات (The Zipper) ---
def extract_and_zip(project_name, ai_text):
    zip_buffer = io.BytesIO()
    # البحث عن نمط الملفات اللي الذكاء الاصطناعي بيكتبها
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", ai_text, re.DOTALL)
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        if not files:
            # لو مفيش أكواد، حط الرد النصي في ملف
            zf.writestr(f"{project_name}/ReadMe_Instruction.txt", ai_text)
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
        "تم تحديث النظام للنسخة المستقرة.\n"
        "للبدء، أضف مفتاحك أو ابدأ البناء فوراً لو المفتاح مضاف مسبقاً."
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
    bot.send_message(message.chat.id, "✅ تم تفعيل الترسانة بنجاح! جاهز للأوامر.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['🚀 بناء مشروع ضخم', '🛠️ فحص وإصلاح كود'])
def action_select(message):
    user_id = message.chat.id
    # التأكد من وجود المفتاح
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
    
    if mode == 'build':
        bot.send_message(user_id, "أرسل اسم المشروع ووصفه (مثلاً: تطبيق متجر إلكتروني كامل):")
    else:
        bot.send_message(user_id, "أرسل الأكواد اللي محتاجة تصليح:")

@bot.message_handler(func=lambda m: m.chat.id in user_data and 'api_key' in user_data[m.chat.id])
def execute_task(message):
    user_id = message.chat.id
    data = user_data[user_id]
    if 'mode' not in data: return

    status = bot.reply_to(message, "⚙️ مصنع الأمير المتمرد يعمل الآن.. انتظر الملف المضغوط...")
    
    try:
        if data['mode'] == 'fix':
            prompt = f"قم بإصلاح وتطوير هذا الكود ليكون احترافياً: \n\n{message.text}"
            p_name = "Code_Fixed"
        else:
            p_name = message.text.split('\n')[0].strip()[:15]
            prompt = (
                f"ابني مشروعاً كاملاً باسم {p_name}. "
                f"المتطلبات: {message.text}. "
                "يجب أن تكون الأكواد كاملة وجاهزة داخل ملفات."
            )

        ai_response = get_ai_response(user_id, prompt)
        
        # لو الرد فيه ملفات، اضغطها
        if "---FILE:" in ai_response:
            zip_res = extract_and_zip(p_name, ai_response)
            bot.send_document(
                user_id, zip_res, 
                visible_file_name=f"{p_name}_Rebel_Project.zip",
                caption="✅ تم بناء المشروع بنجاح! فك الضغط وابدأ العمل. 🔥"
            )
        else:
            # لو الرد نصي عادي (زي شرح أو حل مشكلة بسيطة)
            bot.reply_to(message, ai_response)
            
    except Exception as e:
        bot.send_message(user_id, f"❌ حدث خطأ فني: {str(e)}")
    
    bot.delete_message(user_id, status.message_id)

# تشغيل
print("The Rebel Prince is LIVE on Railway!")
bot.infinity_polling()

