import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re
import requests
import subprocess
from googleapiclient.discovery import build
from google.oauth2 import service_account

# =========================
# الإعدادات
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")       # Cloudflare API Token
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")     # Cloudflare Account ID
SERVICE_ACCOUNT_JSON = "service_account.json"  # Google Play JSON

bot = telebot.TeleBot(TELEGRAM_TOKEN)

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

user_mode = {}
user_status = {}  # idle / running / stopped

# =========================
# AI ENGINE
# =========================
def ask_ai(prompt):
    system = """
أنت مهندس برمجيات محترف.

إذا طلب المستخدم إنشاء موقع أو شبكة اجتماعية قم بإنشاء مشروع كامل:

Frontend: HTML, CSS, JavaScript
Backend: Node.js + Express (لشبكات اجتماعية)

المشروع يجب أن يحتوي:

- صفحة تسجيل
- صفحة تسجيل دخول
- صفحة المنشورات (Feed)
- رفع صور
- تعليقات
- إعجابات

التنسيق الإجباري للملفات:

---FILE: filename.ext---
الكود هنا
---END FILE---
"""
    response = model.generate_content(system + prompt)
    if hasattr(response, "text"):
        return response.text
    return str(response)

# =========================
# استخراج الملفات
# =========================
def extract_files(text):
    files = re.findall(
        r"---FILE:\s*(.*?)\s*---(.*?)---END FILE---",
        text,
        re.DOTALL
    )
    project = {}
    for path, content in files:
        project[path.strip()] = content.strip()
    return project

# =========================
# ضغط الملفات
# =========================
def make_zip(name, files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for path, content in files.items():
            z.writestr(f"{name}/{path}", content)
    buffer.seek(0)
    return buffer

# =========================
# نشر المشروع أونلاين (Cloudflare Pages)
# =========================
def deploy_cloudflare(project_name, files):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects"
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    data = {"name": project_name, "production_branch": "main"}
    requests.post(url, headers=headers, json=data)
    site_url = f"https://{project_name}.pages.dev"
    return site_url

# =========================
# بناء APK أندرويد
# =========================
def build_android_apk(project_name, files):
    os.makedirs(project_name, exist_ok=True)
    for path, content in files.items():
        full_path = os.path.join(project_name, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    subprocess.run(["cordova", "create", f"{project_name}-app", project_name], check=True)
    subprocess.run(["cordova", "platform", "add", "android"], cwd=f"{project_name}-app", check=True)
    www_path = os.path.join(f"{project_name}-app", "www")
    for file_name, content in files.items():
        full_path = os.path.join(www_path, file_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    subprocess.run(["cordova", "build", "android"], cwd=f"{project_name}-app", check=True)
    apk_path = os.path.join(f"{project_name}-app", "platforms", "android", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    return apk_path

# =========================
# نشر APK على Google Play
# =========================
def publish_to_play(apk_path, package_name):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_JSON,
        scopes=['https://www.googleapis.com/auth/androidpublisher']
    )
    service = build('androidpublisher', 'v3', credentials=credentials)
    edit_request = service.edits().insert(body={}, packageName=package_name)
    edit = edit_request.execute()
    edit_id = edit['id']
    apk_response = service.edits().apks().upload(
        editId=edit_id,
        packageName=package_name,
        media_body=apk_path
    ).execute()
    commit_response = service.edits().commit(editId=edit_id, packageName=package_name).execute()
    play_url = f"https://play.google.com/store/apps/details?id={package_name}"
    return play_url

# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    user_status[msg.chat.id] = "idle"
    bot.send_message(msg.chat.id, "🤖 بوت البناء المتكامل\nالأوامر:\n/site → إنشاء موقع أو شبكة اجتماعية وتحويلها لتطبيق أندرويد + نشر على Google Play\n/stop → إيقاف المشروع مؤقتًا")

# =========================
# SITE MODE
# =========================
@bot.message_handler(commands=['site'])
def site(msg):
    user_mode[msg.chat.id] = "site"
    user_status[msg.chat.id] = "running"
    bot.send_message(msg.chat.id, "⚙️ جاري العمل على المشروع...")

# =========================
# STOP COMMAND
# =========================
@bot.message_handler(commands=['stop'])
def stop_project(msg):
    user_status[msg.chat.id] = "stopped"
    bot.send_message(msg.chat.id, "⛔ تم إيقاف المشروع مؤقتًا.")

# =========================
# MAIN HANDLER
# =========================
@bot.message_handler(func=lambda m: True)
def main(msg):
    status = user_status.get(msg.chat.id, "idle")
    if status == "stopped":
        bot.send_message(msg.chat.id, "⛔ تم إيقاف المشروع، استخدم /site لإعادة التشغيل.")
        return
    elif status == "running":
        bot.send_message(msg.chat.id, "⚙️ جاري العمل بالفعل على مشروع آخر، انتظر انتهاءه.")
        return

    user_status[msg.chat.id] = "running"

    bot.send_message(msg.chat.id, "⚙️ جاري إنشاء المشروع...")

    try:
        ai_text = ask_ai(msg.text)
        files = extract_files(ai_text)
        project = msg.text.split("\n")[0][:20] or "project"

        zip_file = make_zip(project, files)
        bot.send_document(msg.chat.id, zip_file, visible_file_name=f"{project}.zip")

        try:
            link = deploy_cloudflare(project, files)
            bot.send_message(msg.chat.id, f"🌐 المشروع نُشر أونلاين:\n{link}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ خطأ أثناء النشر: {str(e)}\nيمكنك تشغيل المشروع محلياً.")

        try:
            apk_file = build_android_apk(project, files)
            with open(apk_file, "rb") as f:
                bot.send_document(msg.chat.id, f, visible_file_name=f"{project}.apk")
            bot.send_message(msg.chat.id, "📱 تم إنشاء تطبيق أندرويد APK بنجاح!")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ لم يتم إنشاء APK: {str(e)}")

        try:
            package_name = f"com.example.{project.lower()}"
            play_link = publish_to_play(apk_file, package_name)
            bot.send_message(msg.chat.id, f"✅ التطبيق نُشر على Google Play:\n{play_link}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ لم يتم نشر التطبيق على Google Play: {str(e)}")

    finally:
        user_status[msg.chat.id] = "idle"
        bot.send_message(msg.chat.id, "✅ تم الانتهاء من المشروع!")

# =========================
# تشغيل البوت
# =========================
print("BOT ONLINE")
bot.infinity_polling(skip_pending=True)
