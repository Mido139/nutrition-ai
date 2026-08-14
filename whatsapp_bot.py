from flask import Flask, request
import requests
import os
from google import genai
from tavily import TavilyClient

app = Flask(__name__)

# =========================================================
# إعدادات البيئة
# =========================================================

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

VERIFY_TOKEN = os.environ.get(
    "VERIFY_TOKEN",
    "DairyBot2026"
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# إصدار WhatsApp Graph API
WHATSAPP_API_VERSION = "v26.0"

# موديل Gemini - تم التعديل للإصدار الأساسي المضمون
GEMINI_MODEL = "gemini-pro"


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
# تهيئة Gemini و Tavily
# =========================================================

client = None
tavily_client = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


# =========================================================
# Webhook
# =========================================================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # -----------------------------------------------------
    # 1. Meta Webhook Verification
    # -----------------------------------------------------

    if request.method == "GET":

        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        print(
            f"Webhook verification request: "
            f"mode={mode}, token_received={bool(token)}"
        )

        if mode == "subscribe" and token == VERIFY_TOKEN:

            print("Webhook verification successful")

            return challenge, 200

        print("Webhook verification failed")

        return "Forbidden", 403


    # -----------------------------------------------------
    # 2. استقبال رسائل WhatsApp
    # -----------------------------------------------------

    if request.method == "POST":

        try:

            body = request.get_json(silent=True)

            print("======================================")
            print("WhatsApp Webhook received")
            print("======================================")
            print(body)

            if not body:
                return "EVENT_RECEIVED", 200


            # التأكد أن الحدث خاص بـ WhatsApp
            if body.get("object") != "whatsapp_business_account":
                return "EVENT_RECEIVED", 200


            entries = body.get("entry", [])

            if not entries:
                return "EVENT_RECEIVED", 200


            for entry in entries:

                changes = entry.get("changes", [])

                for change in changes:

                    value = change.get("value", {})

                    messages = value.get("messages", [])

                    # -------------------------------------------------
                    # لا توجد رسالة، مثل delivery/read/status
                    # -------------------------------------------------

                    if not messages:
                        print("Webhook event contains no messages")
                        continue


                    # معالجة كل الرسائل الموجودة
                    for message_data in messages:

                        sender_phone = message_data.get("from")

                        message_type = message_data.get("type")

                        print(
                            f"Message received from: "
                            f"{sender_phone}"
                        )

                        print(
                            f"Message type: "
                            f"{message_type}"
                        )


                        # ---------------------------------------------
                        # الرسائل النصية فقط
                        # ---------------------------------------------

                        if message_type != "text":

                            if sender_phone:
                                send_whatsapp_message(
                                    sender_phone,
                                    "⚠️ حاليًا البوت يدعم الرسائل النصية فقط."
                                )

                            continue


                        text_data = message_data.get("text", {})

                        msg_text = text_data.get("body", "").strip()


                        if not msg_text:
                            continue


                        print(
                            f"User message: {msg_text}"
                        )


                        # ---------------------------------------------
                        # رسالة مؤقتة
                        # ---------------------------------------------

                        send_whatsapp_message(
                            sender_phone,
                            "⏳ جاري تحليل سؤالك والبحث في المراجع العلمية..."
                        )


                        # ---------------------------------------------
                        # الذكاء الاصطناعي
                        # ---------------------------------------------

                        reply = process_with_ai(msg_text)


                        # ---------------------------------------------
                        # إرسال الإجابة
                        # ---------------------------------------------

                        send_whatsapp_message(
                            sender_phone,
                            reply
                        )


            return "EVENT_RECEIVED", 200


        except Exception as e:

            print(
                f"ERROR processing webhook: {e}"
            )

            # مهم جدًا:
            # نرجع 200 إلى Meta حتى لا تعيد إرسال نفس الحدث
            return "EVENT_RECEIVED", 200


# =========================================================
# معالجة السؤال باستخدام Tavily + Gemini
# =========================================================

def process_with_ai(query):

    try:

        print("Starting AI processing...")

        # -------------------------------------------------
        # البحث العلمي
        # -------------------------------------------------

        context = ""

        if tavily_client:

            scientific_query = (
                query
                + " AND "
                "(dairy cattle OR dairy cows OR الأبقار الحلوب) "
                "(بحث علمي OR دراسة أكاديمية)"
            )

            print(
                f"Tavily query: {scientific_query}"
            )

            search_response = tavily_client.search(
                scientific_query,
                search_depth="advanced",
                max_results=3
            )

            results = search_response.get(
                "results",
                []
            )

            print(
                f"Tavily returned {len(results)} results"
            )


            for index, result in enumerate(results):

                content = result.get(
                    "content",
                    ""
                )

                title = result.get(
                    "title",
                    ""
                )

                url = result.get(
                    "url",
                    ""
                )

                context += (
                    f"Source [{index + 1}]\n"
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Information: {content}\n\n"
                )

        else:

            print(
                "TAVILY_API_KEY is missing"
            )

            context = (
                "No external scientific search was available."
            )


        # -------------------------------------------------
        # Prompt
        # -------------------------------------------------

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

قدم إجابة منظمة ومختصرة نسبيًا، ويمكن استخدام
النقاط والجداول البسيطة عند الحاجة.
"""


        # -------------------------------------------------
        # Gemini
        # -------------------------------------------------

        if not client:

            return (
                "⚠️ مفتاح Gemini غير موجود في إعدادات Render."
            )


        print(
            f"Sending request to Gemini model: "
            f"{GEMINI_MODEL}"
        )


        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )


        # -------------------------------------------------
        # استخراج الإجابة
        # -------------------------------------------------

        if response and response.text:

            answer = response.text.strip()

            print(
                "Gemini response received successfully"
            )

            return answer


        print(
            "Gemini returned an empty response"
        )

        return (
            "⚠️ حصلت مشكلة ولم يرجع الذكاء الاصطناعي إجابة."
        )


    except Exception as e:

        print(
            "======================================"
        )

        print(
            f"Error in process_with_ai: {e}"
        )

        print(
            "======================================"
        )

        return (
            "⚠️ عذرًا، حدث خطأ أثناء معالجة السؤال. "
            "حاول مرة أخرى بعد قليل."
        )


# =========================================================
# إرسال رسالة WhatsApp
# =========================================================

def send_whatsapp_message(to, text):

    try:

        if not WHATSAPP_TOKEN:

            print(
                "WHATSAPP_TOKEN is missing"
            )

            return False


        if not PHONE_NUMBER_ID:

            print(
                "PHONE_NUMBER_ID is missing"
            )

            return False


        url = (
            f"https://graph.facebook.com/"
            f"{WHATSAPP_API_VERSION}/"
            f"{PHONE_NUMBER_ID}/messages"
        )


        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }


        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": text
            }
        }


        print(
            f"Sending WhatsApp message to {to}"
        )


        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )


        print(
            f"WhatsApp API status: "
            f"{response.status_code}"
        )

        print(
            f"WhatsApp API response: "
            f"{response.text}"
        )


        if response.ok:

            return True

        return False


    except Exception as e:

        print(
            f"Error sending WhatsApp message: {e}"
        )

        return False


# =========================================================
# Health Check
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return "Dairy Nutrition AI Bot is running.", 200


# =========================================================
# تشغيل السيرفر
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print(
        f"Starting server on port {port}"
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
