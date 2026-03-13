import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re

# ==========================================
# إعدادات مصنع الأمير المتمرد - الإصدار الذهبي
# ==========================================

# توكن التليجرام (اسحبه من Variables في Railway)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") 

# مفتاح Gemini الخاص بك (مدمج بناءً على طلبك)
GOOGLE_API_KEY = "AIzaSyAm6Mpv9pikiAbsIlYwNEpum-806-UwWJ0"

# إعداد البوت والمحرك
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)

def generate_rebel_code(prompt):
    """دالة توليد الأكواد باستخدام ذكاء Gemini"""
    try:
        # استخدام موديل 1.5-flash لضمان السرعة وتجنب أخطاء 404
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # تعليمات النظام لضمان خروج الأكواد في ملفات منظمة
        system_instruction = (
            "أنت مهندس برمجيات محترف ملقب بـ (الأمير المتمرد). "
            "مهمتك بناء مشاريع كاملة 100% بدون أي نقص أو تعليقات فارغة. "
            "يجب أن يكون ردك بالتنسيق التالي حصراً لكل ملف:\n"
            "---FILE: اسم_الملف.الامتداد---\n"
            "الكود البرمجي الكامل هنا\n"
            "---END FILE---\n"
        )
        
        response = model.generate_content(system_instruction + prompt)
        return response.text
    except Exception as e:
        return f"❌ خطأ في محرك الذكاء: {str(e)}"

def make_zip(text):
    """دالة تحويل الأكواد النصية إلى ملف Zip حقيقي"""
    buf = io.BytesIO()
    # استخراج الملفات باستخدام التعبيرات النمطية (Regex)
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", text, re.DOTALL)
    
    with zipfile.ZipFile(buf, "w") as z:
        if not files:
            # لو الرد مكنش فيه ملفات منظمة، نحط الرد في ملف نصي للشرح
            z.writestr("read_me_first.txt", text)
        for name, code in files:
            # تنظيف الاسم والكود من أي مسافات زايدة
            z.writestr(name.strip(), code.strip())
            
    buf.seek(0)
    return buf

# --- معالجة أوامر التليجرام ---

@bot.message_handler(commands=['start'])
def start(m):
    """رسالة الترحيب"""
    welcome_text = (
        "⚔️ **مرحباً بك في مصنع برمجيات الأمير المتمرد!**\n\n"
        "أنا جاهز الآن لتوليد وبناء أي كود برمجي أو مشروع كامل.\n"
        "فقط أرسل لي اسم المشروع (مثلاً: موقع متجر إلكتروني، سكربت بايثون، صفحة هبوط)...\n"
        "وسأقوم بإرسال الملفات لك مضغوطة في ملف **Zip** جاهز للتشغيل. 🔥"
    )
    bot.reply_to(m, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def build_request(m):
    """استلام طلب البناء وتنفيذه"""
    # إشعار المستخدم أن العمل جاري
    status_msg = bot.reply_to(m, "⚙️ جاري تشغيل الترسانة وبناء مشروعك... انتظر قليلاً.")
    
    try:
        # 1. طلب الكود من الذكاء الاصطناعي
        ai_response = generate_rebel_code(m.text)
        
        # 2. فحص هل الرد يحتوي على ملفات
        if "---FILE:" in ai_response:
            zip_data = make_zip(ai_response)
            # 3. إرسال ملف الـ Zip
            bot.send_document(
                m.chat.id, 
                zip_data, 
                visible_file_name="Rebel_Project_Files.zip", 
                caption="✅ تم الانتهاء من بناء مشروعك بنجاح!\nبواسطة: **الأمير المتمرد** ⚔️"
            )
        else:
            # لو الرد نصي عادي (نصيحة أو شرح)
            bot.reply_to(m, ai_response)
            
    except Exception as e:
        bot.reply_to(m, f"❌ عذراً يا بطل، حدث خطأ فني: {str(e)}")
    
    # حذف رسالة "جاري العمل" بعد الانتهاء
    bot.delete_message(m.chat.id, status_msg.message_id)

# تشغيل البوت للأبد
print("The Rebel Prince Factory is ONLINE...")
bot.infinity_polling()

