from flask import Flask, request
import requests
import os
from tavily import TavilyClient

app = Flask(__name__)

# =========================================================
# إعدادات البيئة
# =========================================================

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "DairyBot2026")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

WHATSAPP_API_VERSION = "v26.0"

# =========================================================
# التحقق من إعدادات البيئة
# =========================================================

if not WHATSAPP_TOKEN:
    print("WARNING: WHATSAPP_TOKEN is missing")
if not PHONE_NUMBER_ID:
    print("WARNING: PHONE_NUMBER_ID is missing")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is missing")
if not TAVILY_API_KEY:
    print("WARNING: TAVILY_API_KEY is missing")

# =========================================================
# تهيئة Tavily فقط
# =========================================================

tavily_client = None
if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# =========================================================
# Webhook
# =========================================================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403

    if request.method == "POST":
        try:
            body = request.get_json(silent=True)
            if not body or body.get("object") != "whatsapp_business_account":
                return "EVENT_RECEIVED", 200

            entries = body.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])

                    if not messages:
                        continue

                    for message_data in messages:
                        sender_phone = message_data.get("from")
                        message_type = message_data.get("type")

                        if message_type != "text":
                            if sender_phone:
                                send_whatsapp_message(
                                    sender_phone,
                                    "⚠️ حاليًا البوت يدعم الرسائل النصية فقط."
                                )
                            continue

                        msg_text = message_data.get("text", {}).get("body", "").strip()
                        if not msg_text:
                            continue

                        print(f"User message: {msg_text}")

                        # رسالة مؤقتة
                        send_whatsapp_message(
                            sender_phone,
                            "⏳ جاري تحليل سؤالك والبحث في المراجع العلمية..."
                        )

                        # معالجة الذكاء الاصطناعي
                        reply = process_with_ai(msg_text)

                        # إرسال الإجابة النهائية
                        send_whatsapp_message(sender_phone, reply)

            return "EVENT_RECEIVED", 200

        except Exception as e:
            print(f"ERROR processing webhook: {e}")
            return "EVENT_RECEIVED", 200

# =========================================================
# معالجة السؤال (Tavily + Direct Gemini API)
# =========================================================

def process_with_ai(query):
    try:
        print("Starting AI processing...")

        # 1. البحث العلمي
        context = ""
        if tavily_client:
            scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية)"
            search_response = tavily_client.search(
                scientific_query,
                search_depth="advanced",
                max_results=3
            )
            results = search_response.get("results", [])
            for index, result in enumerate(results):
                context += f"Source [{index + 1}]\nTitle: {result.get('title', '')}\nURL: {result.get('url', '')}\nInformation: {result.get('content', '')}\n\n"
        else:
            context = "No external scientific search was available."

        # 2. تجهيز الـ Prompt
        prompt = f"""
أنت مستشار خبير في تغذية وإدارة الأبقار الحلوب
(Dairy Cattle Nutrition and Management).

أجب على سؤال المستخدم باللغة العربية بطريقة علمية
وواضحة وعملية.

اعتمد قدر الإمكان على مبادئ NASEM في تغذية الأبقار
الحلوب، واستفد من نتائج البحث العلمي الموجودة في
السياق أدناه.

لا تخترع أرقامًا أو مراجع غير موجودة.
إذا كانت المعلومة تعتمد على حالة معينة، وضح ذلك.

السياق العلمي:
{context}

سؤال المستخدم:
{query}

قدم إجابة منظمة ومختصرة نسبيًا، ويمكن استخدام النقاط والجداول البسيطة.
"""

        # 3. الاتصال المباشر بـ Gemini عبر REST API (تخطي مشاكل المكتبة)
        if not GEMINI_API_KEY:
            return "⚠️ مفتاح Gemini غير موجود في إعدادات Render."

        # نستخدم أحدث موديل مستقر من خلال الرابط المباشر
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        print("Sending Direct HTTP Request to Gemini API...")
        response = requests.post(gemini_url, headers=headers, json=payload, timeout=30)
        
        if response.ok:
            data = response.json()
            answer = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if answer:
                print("Gemini response received successfully via HTTP.")
                return answer.strip()
            else:
                return "⚠️ الذكاء الاصطناعي لم يرجع إجابة نصية صالحة."
        else:
            print(f"Gemini API Direct Error: {response.status_code} - {response.text}")
            return "⚠️ عذرًا، تم رفض الطلب من خادم الذكاء الاصطناعي. تأكد من صحة مفتاح API الخاص بك."

    except Exception as e:
        print("======================================")
        print(f"Error in process_with_ai: {e}")
        print("======================================")
        return "⚠️ عذرًا، حدث خطأ داخلي أثناء معالجة السؤال. حاول مرة أخرى بعد قليل."

# =========================================================
# إرسال رسالة WhatsApp
# =========================================================

def send_whatsapp_message(to, text):
    try:
        if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
            return False

        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        
        requests.post(url, headers=headers, json=data, timeout=30)
        return True

    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False

# =========================================================
# Health Check & Run
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return "Dairy Nutrition AI Bot is running.", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
