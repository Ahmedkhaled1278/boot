import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re
from github import Github

# الإعدادات (تأكد من وضعها في Variables على Railway)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # اختياري لو عايز رفع لجيتهاب

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# دالة ذكاء الأمير المتمرد
def rebel_ai_engine(prompt):
    system_prompt = (
        "أنت مهندس برمجيات محترف (الأمير المتمرد). وظيفتك بناء مشاريع كاملة.\n"
        "يجب أن يكون الرد بتنسيق ملفات محدد كالتالي:\n"
        "---FILE: اسم_الملف.الامتداد---\n"
        "الكود هنا\n"
        "---END FILE---\n"
    )
    response = model.generate_content(system_prompt + prompt)
    return response.text

# استخراج الملفات وضغطها
def create_project_zip(project_name, ai_text):
    buffer = io.BytesIO()
    files = re.findall(r"---FILE:\s*(.*?)\s*---\n(.*?)\n---END FILE---", ai_text, re.DOTALL)
    
    with zipfile.ZipFile(buffer, "w") as z:
        if not files: # لو الذكاء الاصطناعي رد بنص عادي
            z.writestr(f"{project_name}/readme.txt", ai_text)
        for path, content in files:
            z.writestr(f"{project_name}/{path.strip()}", content.strip())
    
    buffer.seek(0)
    return buffer, files

# رفع الكود لـ GitHub (اختياري)
def push_to_github(repo_name, files_list):
    if not GITHUB_TOKEN: return None
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        repo = user.create_repo(repo_name, private=False)
        for path, content in files_list:
            repo.create_file(path.strip(), "Initial commit by Rebel Bot", content.strip())
        return repo.html_url
    except:
        return None

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "⚔️ **مرحباً بك في مصنع برمجيات الأمير المتمرد**\n\nأرسل لي اسم المشروع أو الفكرة (مثلاً: موقع متجر، بوت تليجرام، صفحة هبوط) وسأقوم ببنائها لك فوراً.")

@bot.message_handler(func=lambda m: True)
def handle_build(message):
    msg = bot.reply_to(message, "⚙️ جاري تشغيل الترسانة وبناء مشروعك...")
    
    try:
        # 1. توليد الكود بالذكاء الاصطناعي
        ai_response = rebel_ai_engine(message.text)
        project_name = "Rebel_Project_" + str(message.chat.id)[:4]
        
        # 2. إنشاء ملف الـ Zip
        zip_file, files_found = create_project_zip(project_name, ai_response)
        
        # 3. إرسال ملف الـ Zip للمستخدم
        bot.send_document(
            message.chat.id, 
            zip_file, 
            visible_file_name=f"{project_name}.zip",
            caption="✅ تم بناء الملفات بنجاح!"
        )
        
        # 4. محاولة الرفع لـ GitHub لو الـ Token موجود
        if GITHUB_TOKEN and files_found:
            github_url = push_to_github(project_name + "_repo", files_found)
            if github_url:
                bot.send_message(message.chat.id, f"🌐 تم رفع النسخة المصدرية لـ GitHub:\n{github_url}")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ تقني: {str(e)}")
    
    finally:
        bot.delete_message(message.chat.id, msg.message_id)

print("الترسانة تعمل الآن...")
bot.infinity_polling()

