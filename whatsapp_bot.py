from flask import Flask, request, jsonify
import requests
import os
from google import genai
from tavily import TavilyClient

app = Flask(__name__)

# =========================================================
# 1. إعدادات البيئة والمفاتيح
# =========================================================
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "DairyBot2026")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

WHATSAPP_API_VERSION = "v26.0"
GEMINI_MODEL = "gemini-1.5-flash" # الإصدار المعتمد والمستقر

# =========================================================
# 2. تهيئة خدمات الذكاء الاصطناعي
# =========================================================
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Init Error: {e}")

tavily_client = None
if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


# =========================================================
# 3. دالة معالجة الأسئلة (البحث + التفكير)
# =========================================================
def ask_ai(query):
    try:
        context = ""
        # 1. البحث العلمي (Tavily)
        if tavily_client:
            print("Searching Tavily...")
            search_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب)"
            res = tavily_client.search(search_query, search_depth="advanced", max_results=3)
            for i, item in enumerate(res.get("results", [])):
                context += f"\n[{i+1}] {item.get('title')} - {item.get('content')}"
        
        # 2. صياغة السؤال للموديل
        prompt = f"""
أنت خبير في تغذية وإدارة الأبقار الحلوب. أجب باللغة العربية بأسلوب علمي دقيق.
اعتمد على مبادئ NASEM والمراجع التالية إن وجدت:
{context}

السؤال: {query}
"""
        # 3. إرسال السؤال لجوجل (Gemini)
        if not gemini_client:
            return "⚠️ مفتاح Gemini غير متوفر."
            
        print(f"Asking Gemini ({GEMINI_MODEL})...")
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            return "⚠️ لم أتمكن من صياغة إجابة، يرجى المحاولة لاحقاً."

    except Exception as e:
        print(f"AI Process Error: {e}")
        return "⚠️ حدث خطأ في خوادم الذكاء الاصطناعي. يرجى التأكد من صلاحية مفتاح Gemini API."


# =========================================================
# 4. دالة إرسال رسائل الواتساب
# =========================================================
def send_whatsapp_message(to_number, text_msg):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WhatsApp Keys!")
        return
    
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_msg}
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        print(f"WhatsApp Send Error: {e}")


# =========================================================
# 5. مسارات الويب (Webhooks & Endpoints)
# =========================================================

# مسار اختبار سريع من المتصفح (عشان تتأكد إن Gemini شغال)
@app.route("/test-ai", methods=["GET"])
def test_ai():
    test_query = request.args.get("query", "ما هو الـ BCS في الأبقار؟")
    answer = ask_ai(test_query)
    return jsonify({"query": test_query, "answer": answer})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # التحقق من Meta (GET)
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Invalid Token", 403

    # استقبال الرسائل (POST)
    if request.method == "POST":
        try:
            body = request.get_json(silent=True)
            if not body or body.get("object") != "whatsapp_business_account":
                return "OK", 200

            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    messages = change.get("value", {}).get("messages", [])
                    for msg in messages:
                        sender_phone = msg.get("from")
                        
                        if msg.get("type") == "text":
                            user_text = msg.get("text", {}).get("body", "").strip()
                            if user_text:
                                print(f"Received: {user_text}")
                                # إرسال رسالة انتظار
                                send_whatsapp_message(sender_phone, "⏳ جاري البحث والتحليل...")
                                # معالجة وإرسال الرد النهائي
                                final_answer = ask_ai(user_text)
                                send_whatsapp_message(sender_phone, final_answer)
                        else:
                            send_whatsapp_message(sender_phone, "⚠️ عذراً، أستقبل الرسائل النصية فقط حالياً.")
                            
            return "OK", 200
        except Exception as e:
            print(f"Webhook Error: {e}")
            return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "Dairy Bot is Active 🚀", 200

# =========================================================
# 6. تشغيل السيرفر
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
