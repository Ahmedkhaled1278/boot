import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re

# ==========================================
# إعدادات الأمير المتمرد - النسخة المصححة 100%
# ==========================================

# توكن التليجرام
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("❌ خطأ: TELEGRAM_TOKEN غير موجود في Environment Variables")

# مفتاح Gemini الخاص بك (خليه في Environment Variables)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("❌ خطأ: GOOGLE_API_KEY غير موجود في Environment Variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)

def generate_rebel_code(prompt):
    """دالة توليد الأكواد بالتعديل الجديد لتجنب خطأ 404"""
    try:
        # التعديل الإلزامي: إضافة models/ قبل اسم الموديل
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
        return f"❌ خطأ في المحرك (404/الاتصال): {str(e)}"

def make_zip(text):
    """دالة ضغط الملفات"""
    buf = io.BytesIO()
    # تعديل Regex لالتقاط جميع الملفات حتى بدون سطر فاضي قبل END
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n([\s\S]*?)---END FILE---", text)
    
    with zipfile.ZipFile(buf, "w") as z:
        if not files:
            z.writestr("Instructions.txt", text)
        for name, code in files:
            z.writestr(name.strip(), code.strip())
    
    buf.seek(0)
    return buf

# --- الأوامر ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "⚔️ **تم تحديث الترسانة بالمسار الصحيح!**\nأرسل طلبك الآن وسأقوم ببناء الملفات فوراً.")

@bot.message_handler(func=lambda m: True)
def build(m):
    wait = bot.reply_to(m, "⚙️ جاري البناء باستخدام المحرك المحدث... انتظر قليلاً.")
    
    try:
        res_text = generate_rebel_code(m.text)
        
        if "---FILE:" in res_text:
            zip_data = make_zip(res_text)
            bot.send_document(
                m.chat.id, 
                zip_data, 
                caption="✅ تم الإنجاز! بصمة الأمير المتمرد 🔥", 
                visible_file_name="Rebel_Project.zip"
            )
        else:
            bot.reply_to(m, res_text)
            
    except Exception as e:
        bot.reply_to(m, f"❌ حدث خطأ فني: {str(e)}")
    
    try:
        bot.delete_message(m.chat.id, wait.message_id)
    except:
        pass  # لو الرسالة اتحذفت أو حصل خطأ تجاهله

print("الترسانة أونلاين بالتعديل الجديد...")
bot.infinity_polling()
