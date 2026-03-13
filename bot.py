import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re

# ==========================================
# إعدادات الأمير المتمرد - الإصدار النهائي المستقر
# ==========================================

# توكن التليجرام (اسحبه من Variables في Railway)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") 

# مفتاح Gemini الخاص بك (مدمج لضمان العمل)
GOOGLE_API_KEY = "AIzaSyAm6Mpv9pikiAbsIlYwNEpum-806-UwWJ0"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# إعداد المحرك
genai.configure(api_key=GOOGLE_API_KEY)

def generate_rebel_code(prompt):
    """دالة توليد الأكواد باستخدام أضمن مسار للموديل"""
    try:
        # التعديل النهائي لحل مشكلة 404: استخدام المسار الكامل للموديل
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        system_instruction = (
            "أنت مهندس برمجيات محترف (الأمير المتمرد). ابني المشروع كاملاً وبدقة.\n"
            "التنسيق الإلزامي للملفات:\n"
            "---FILE: filename.ext---\n"
            "الكود الكامل هنا\n"
            "---END FILE---\n"
        )
        
        response = model.generate_content(system_instruction + prompt)
        return response.text
    except Exception as e:
        # محاولة أخيرة لو الموديل الأول لم يستجب في منطقتك
        try:
            model_fallback = genai.GenerativeModel("gemini-pro")
            return model_fallback.generate_content(prompt).text
        except:
            return f"❌ خطأ في الاتصال: {str(e)}"

def make_zip(text):
    """دالة ضغط الملفات المستخرجة"""
    buf = io.BytesIO()
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", text, re.DOTALL)
    
    with zipfile.ZipFile(buf, "w") as z:
        if not files:
            z.writestr("Instructions.txt", text)
        for name, code in files:
            z.writestr(name.strip(), code.strip())
            
    buf.seek(0)
    return buf

# --- أوامر البوت ---

@bot.message_handler(commands=['start'])
def start(m):
    welcome_text = (
        "⚔️ **ترسانة الأمير المتمرد جاهزة الآن!**\n\n"
        "تم تحديث مسارات الموديلات لحل مشكلة الـ 404.\n"
        "أرسل طلبك الآن (مثلاً: ابني لي تطبيق واتساب) وسأرسل لك الـ Zip."
    )
    bot.reply_to(m, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def build(m):
    # إشعار المستخدم بالبدء
    wait = bot.reply_to(m, "⚙️ جاري البناء والضغط بصيغة Zip... انتظر قليلاً.")
    
    try:
        res_text = generate_rebel_code(m.text)
        
        if "---FILE:" in res_text:
            zip_data = make_zip(res_text)
            bot.send_document(
                m.chat.id, 
                zip_data, 
                visible_file_name="Rebel_Project.zip", 
                caption="✅ تم الإنجاز! بصمة الأمير المتمرد 🔥"
            )
        else:
            bot.reply_to(m, res_text)
            
    except Exception as e:
        bot.reply_to(m, f"❌ حدث خطأ فني: {str(e)}")
    
    # حذف رسالة الانتظار
    try:
        bot.delete_message(m.chat.id, wait.message_id)
    except:
        pass

print("الترسانة أونلاين والموديلات محدثة...")
bot.infinity_polling()

