import os
import telebot
import google.generativeai as genai
import zipfile
import io
import re
import requests
import subprocess
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account

# =========================
# إعدادات
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub Personal Access Token
SERVICE_ACCOUNT_JSON = "service_account.json"  # Google Play JSON
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")   # Netlify Token

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

user_mode = {}
user_status = {}

# =========================
# AI ENGINE
# =========================
def ask_ai(prompt):
    system = """
أنت مهندس برمجيات محترف. أنشئ مشروع كامل: HTML/CSS/JS + Node.js/Express Backend لشبكة اجتماعية.
تنسيق الملفات:
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
# رفع الملفات على GitHub
# =========================
def upload_github(project_name, files):
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo = user.create_repo(project_name, auto_init=True)
    for path, content in files.items():
        repo.create_file(path, "Upload by bot", content)
    return f"https://github.com/{user.login}/{project_name}"

# =========================
# نشر الموقع على Netlify
# =========================
def deploy_netlify(project_name, zip_bytes):
    headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}"}
    files = {'file': ('project.zip', zip_bytes.getvalue())}
    response = requests.post("https://api.netlify.com/api/v1/sites", headers=headers, files=files)
    if response.status_code in [200, 201]:
        return response.json()["url"]
    return None

# =========================
# بناء APK
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
    service.edits().apks().upload(editId=edit_id, packageName=package_name, media_body=apk_path).execute()
    service.edits().commit(editId=edit_id, packageName=package_name).execute()
    return f"https://play.google.com/store/apps/details?id={package_name}"

# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    user_status[msg.chat.id] = "idle"
    bot.send_message(msg.chat.id, "🤖 بوت البناء المتكامل\n/site → إنشاء مشروع شبكة اجتماعية + APK + نشر على GitHub + Netlify + Google Play\n/stop → إيقاف المشروع")

@bot.message_handler(commands=['site'])
def site(msg):
    user_mode[msg.chat.id] = "site"
    user_status[msg.chat.id] = "running"
    bot.send_message(msg.chat.id, "⚙️ جاري العمل على المشروع...")

@bot.message_handler(commands=['stop'])
def stop_project(msg):
    user_status[msg.chat.id] = "stopped"
    bot.send_message(msg.chat.id, "⛔ تم إيقاف المشروع مؤقتًا.")

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
            github_link = upload_github(project, files)
            bot.send_message(msg.chat.id, f"🌐 تم رفع المشروع على GitHub:\n{github_link}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ خطأ GitHub: {str(e)}")

        try:
            netlify_link = deploy_netlify(project, zip_file)
            bot.send_message(msg.chat.id, f"🌐 المشروع نُشر على Netlify:\n{netlify_link}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ خطأ Netlify: {str(e)}")

        try:
            apk_file = build_android_apk(project, files)
            with open(apk_file, "rb") as f:
                bot.send_document(msg.chat.id, f, visible_file_name=f"{project}.apk")
            bot.send_message(msg.chat.id, "📱 تم إنشاء APK بنجاح!")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ خطأ APK: {str(e)}")

        try:
            package_name = f"com.example.{project.lower()}"
            play_link = publish_to_play(apk_file, package_name)
            bot.send_message(msg.chat.id, f"✅ التطبيق نُشر على Google Play:\n{play_link}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"⚠️ خطأ Google Play: {str(e)}")

    finally:
        user_status[msg.chat.id] = "idle"
        bot.send_message(msg.chat.id, "✅ تم الانتهاء من المشروع!")

print("BOT ONLINE")
bot.infinity_polling(skip_pending=True)
