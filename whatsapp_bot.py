from flask import Flask, request
import requests
import os
import threading
import time

from google import genai
from tavily import TavilyClient


# =========================================================
# Flask App
# =========================================================

app = Flask(__name__)


# =========================================================
# Environment Variables
# =========================================================

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

VERIFY_TOKEN = os.environ.get(
    "VERIFY_TOKEN",
    "DairyBot2026"
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# يمكن تغييره من Render Environment Variables
GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

GEMINI_FALLBACK_MODEL = os.environ.get(
    "GEMINI_FALLBACK_MODEL",
    "gemini-2.5-flash-lite"
)

GRAPH_API_VERSION = os.environ.get(
    "GRAPH_API_VERSION",
    "v19.0"
)


# =========================================================
# Check Environment Variables
# =========================================================

print("========================================")
print("🚀 Dairy Nutrition WhatsApp Bot")
print("========================================")

if WHATSAPP_TOKEN:
    print("✅ WHATSAPP_TOKEN loaded")
else:
    print("❌ WHATSAPP_TOKEN is missing")

if PHONE_NUMBER_ID:
    print("✅ PHONE_NUMBER_ID loaded")
else:
    print("❌ PHONE_NUMBER_ID is missing")

if GEMINI_API_KEY:
    print("✅ GEMINI_API_KEY loaded")
else:
    print("❌ GEMINI_API_KEY is missing")

if TAVILY_API_KEY:
    print("✅ TAVILY_API_KEY loaded")
else:
    print("❌ TAVILY_API_KEY is missing")


# =========================================================
# Initialize Gemini
# =========================================================

try:

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    print("✅ Gemini client initialized")

except Exception as e:

    client = None

    print(f"❌ Gemini initialization error: {e}")


# =========================================================
# Initialize Tavily
# =========================================================

try:

    tavily_client = TavilyClient(
        api_key=TAVILY_API_KEY
    )

    print("✅ Tavily client initialized")

except Exception as e:

    tavily_client = None

    print(f"❌ Tavily initialization error: {e}")


# =========================================================
# Prevent Duplicate WhatsApp Messages
# =========================================================

processed_messages = set()

processed_messages_lock = threading.Lock()


def is_message_processed(message_id):
    """
    Check whether a WhatsApp message was already processed.
    """

    with processed_messages_lock:

        if message_id in processed_messages:

            return True

        processed_messages.add(message_id)

        # منع الذاكرة من النمو بلا حدود
        if len(processed_messages) > 5000:

            # حذف جزء من الرسائل القديمة
            old_messages = list(processed_messages)[:1000]

            for old_id in old_messages:
                processed_messages.discard(old_id)

        return False


# =========================================================
# WhatsApp Send Message
# =========================================================

def send_whatsapp_message(to, text):

    if not WHATSAPP_TOKEN:
        print("❌ WHATSAPP_TOKEN is missing")
        return False

    if not PHONE_NUMBER_ID:
        print("❌ PHONE_NUMBER_ID is missing")
        return False

    if not to:
        print("❌ Recipient phone number is missing")
        return False

    if not text:
        print("❌ Message text is empty")
        return False

    # WhatsApp text message limit
    if len(text) > 4000:
        text = text[:3990] + "\n\n[تم اختصار الإجابة]"

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
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

    try:

        print("----------------------------------------")
        print(f"📤 Sending WhatsApp message to: {to}")

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )

        print(
            f"📡 WhatsApp API status: "
            f"{response.status_code}"
        )

        print(
            f"📡 WhatsApp API response: "
            f"{response.text}"
        )

        if response.status_code == 200:

            print("✅ WhatsApp message sent successfully")

            return True

        print("❌ WhatsApp message failed")

        return False

    except Exception as e:

        print(
            f"❌ WhatsApp sending error: {e}"
        )

        return False


# =========================================================
# Tavily Search
# =========================================================

def search_scientific_sources(query):

    if tavily_client is None:

        print("⚠️ Tavily client unavailable")

        return ""

    try:

        scientific_query = (
            query
            + " AND "
            + "(dairy cattle OR dairy cows OR "
              "الأبقار الحلوب) "
            + "(scientific research OR academic study "
              "OR بحث علمي OR دراسة أكاديمية)"
        )

        print("----------------------------------------")
        print("🔎 Tavily query:")
        print(scientific_query)

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
            f"🔎 Tavily returned "
            f"{len(results)} results"
        )

        context = ""

        for index, result in enumerate(results):

            title = result.get(
                "title",
                "Unknown source"
            )

            content = result.get(
                "content",
                ""
            )

            url = result.get(
                "url",
                ""
            )

            context += (
                f"\nSource {index + 1}\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Information: {content}\n"
            )

        return context

    except Exception as e:

        print(
            f"❌ Tavily error: {e}"
        )

        return ""


# =========================================================
# Gemini AI
# =========================================================

def ask_gemini(prompt):

    if client is None:

        return (
            "⚠️ حدث خطأ في الاتصال بخدمة "
            "الذكاء الاصطناعي."
        )

    models_to_try = [
        GEMINI_MODEL,
        GEMINI_FALLBACK_MODEL
    ]

    last_error = None

    for model_name in models_to_try:

        try:

            print(
                f"🤖 Sending request to Gemini model: "
                f"{model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text:

                print(
                    "✅ Gemini response received "
                    "successfully"
                )

                return response.text.strip()

            print(
                f"⚠️ Gemini returned empty response "
                f"using {model_name}"
            )

        except Exception as e:

            last_error = e

            error_text = str(e)

            print(
                f"❌ Gemini error using "
                f"{model_name}: {error_text}"
            )

            # لو المشكلة 503 / high demand
            if "503" in error_text or "UNAVAILABLE" in error_text:

                print(
                    "⚠️ Gemini model temporarily "
                    "unavailable."
                )

                # ننتظر قليلًا ثم نجرب الموديل التالي
                time.sleep(2)

                continue

            # لو الموديل غير موجود
            if (
                "404" in error_text
                or "NOT_FOUND" in error_text
            ):

                print(
                    "⚠️ Gemini model not found. "
                    "Trying fallback model."
                )

                continue

            # أي خطأ آخر
            continue

    print(
        f"❌ All Gemini models failed: "
        f"{last_error}"
    )

    return (
        "⚠️ حدث خطأ مؤقت أثناء معالجة السؤال "
        "بالذكاء الاصطناعي. حاول مرة أخرى."
    )


# =========================================================
# AI Processing
# =========================================================

def process_with_ai(query):

    try:

        print("----------------------------------------")
        print("🧠 Starting AI processing...")
        print(f"📝 User question: {query}")

        # -------------------------------------------------
        # Scientific Search
        # -------------------------------------------------

        context = search_scientific_sources(
            query
        )

        # -------------------------------------------------
        # Prompt
        # -------------------------------------------------

        prompt = f"""
أنت مستشار متخصص في تغذية وإدارة الأبقار الحلوب
(Dairy Cattle Nutrition & Management).

أجب على سؤال المستخدم باللغة العربية بشكل واضح
وعلمي وعملي.

اعتمد قدر الإمكان على مبادئ NASEM وتوصيات تغذية
الأبقار الحلوب، واستخدم نتائج البحث العلمي المرفقة
لزيادة دقة الإجابة.

مهم جدًا:
- لا تخترع أرقامًا أو مراجع.
- إذا كانت المعلومة غير مؤكدة وضح ذلك.
- لا تكرر السؤال.
- لا تكتب كلامًا عامًا بدون فائدة.
- أعطِ إجابة مباشرة.
- استخدم نقاطًا عند الحاجة.
- إذا كان السؤال يحتاج بيانات إضافية مثل وزن الحيوان،
  إنتاج اللبن، نسبة الدهن، مرحلة الإدرار أو DMI،
  اذكر البيانات المطلوبة.
- لا تذكر أنك نموذج ذكاء اصطناعي.
- لا تقل "جاري البحث".
- أرسل إجابة واحدة مكتملة.

السياق العلمي:

{context}

سؤال المستخدم:

{query}
"""

        # -------------------------------------------------
        # Gemini
        # -------------------------------------------------

        reply = ask_gemini(
            prompt
        )

        if not reply:

            reply = (
                "⚠️ لم أتمكن من إنشاء إجابة الآن."
            )

        print("✅ AI processing finished")

        return reply

    except Exception as e:

        print(
            f"❌ Error in process_with_ai: {e}"
        )

        return (
            "⚠️ عذراً، حدث خطأ أثناء معالجة "
            "السؤال. حاول مرة أخرى."
        )


# =========================================================
# Background Message Processing
# =========================================================

def process_message_in_background(
    sender_phone,
    msg_text
):

    try:

        print("----------------------------------------")
        print(
            f"🔄 Background processing started "
            f"for {sender_phone}"
        )

        # معالجة السؤال
        reply = process_with_ai(
            msg_text
        )

        # إرسال الرد النهائي فقط
        print(
            f"📤 Sending final answer to "
            f"{sender_phone}"
        )

        send_whatsapp_message(
            sender_phone,
            reply
        )

        print(
            "✅ Background processing completed"
        )

    except Exception as e:

        print(
            f"❌ Background processing error: {e}"
        )


# =========================================================
# Webhook
# =========================================================

@app.route(
    "/webhook",
    methods=["GET", "POST"]
)
def webhook():

    # =====================================================
    # META VERIFICATION
    # =====================================================

    if request.method == "GET":

        mode = request.args.get(
            "hub.mode"
        )

        token = request.args.get(
            "hub.verify_token"
        )

        challenge = request.args.get(
            "hub.challenge"
        )

        print("----------------------------------------")
        print("🔐 Webhook verification request")
        print(f"Mode: {mode}")
        print(f"Token received: {token}")

        if (
            mode == "subscribe"
            and token == VERIFY_TOKEN
        ):

            print(
                "✅ WhatsApp Webhook verified"
            )

            return challenge, 200

        print(
            "❌ Webhook verification failed"
        )

        return "Forbidden", 403

    # =====================================================
    # RECEIVE POST FROM META
    # =====================================================

    if request.method == "POST":

        body = request.get_json(
            silent=True
        )

        print("\n========================================")
        print("📩 WhatsApp Webhook received")
        print("========================================")

        print(body)

        if not body:

            print(
                "⚠️ Empty webhook body"
            )

            return "EVENT_RECEIVED", 200

        # =================================================
        # Check WhatsApp object
        # =================================================

        if (
            body.get("object")
            != "whatsapp_business_account"
        ):

            print(
                "ℹ️ Not a WhatsApp Business event"
            )

            return "EVENT_RECEIVED", 200

        try:

            entry = body.get(
                "entry",
                []
            )

            if not entry:

                return "EVENT_RECEIVED", 200

            changes = entry[0].get(
                "changes",
                []
            )

            if not changes:

                return "EVENT_RECEIVED", 200

            value = changes[0].get(
                "value",
                {}
            )

            messages = value.get(
                "messages",
                []
            )

            # =================================================
            # Status events / other events
            # =================================================

            if not messages:

                print(
                    "ℹ️ Webhook event has no messages"
                )

                return "EVENT_RECEIVED", 200

            # =================================================
            # Get message
            # =================================================

            message_data = messages[0]

            message_id = message_data.get(
                "id"
            )

            if not message_id:

                print(
                    "⚠️ Message ID not found"
                )

                return "EVENT_RECEIVED", 200

            print(
                f"🆔 Message ID: {message_id}"
            )

            # =================================================
            # DUPLICATE PROTECTION
            # =================================================

            if is_message_processed(
                message_id
            ):

                print(
                    "⚠️ DUPLICATE MESSAGE "
                    "- IGNORED"
                )

                return "EVENT_RECEIVED", 200

            # =================================================
            # Message Type
            # =================================================

            message_type = message_data.get(
                "type"
            )

            print(
                f"📱 Message type: "
                f"{message_type}"
            )

            # نتعامل مع النص فقط
            if message_type != "text":

                print(
                    "ℹ️ Message is not text "
                    "- ignored"
                )

                return "EVENT_RECEIVED", 200

            # =================================================
            # Sender Phone
            # =================================================

            sender_phone = message_data.get(
                "from"
            )

            # =================================================
            # Message Text
            # =================================================

            msg_text = (
                message_data
                .get("text", {})
                .get("body", "")
            )

            if not sender_phone:

                print(
                    "❌ Sender phone missing"
                )

                return "EVENT_RECEIVED", 200

            if not msg_text:

                print(
                    "❌ Message text missing"
                )

                return "EVENT_RECEIVED", 200

            print(
                f"👤 Message received from: "
                f"{sender_phone}"
            )

            print(
                f"💬 User message: "
                f"{msg_text}"
            )

            # =================================================
            # IMPORTANT:
            #
            # Start processing in background.
            #
            # We immediately return 200 to Meta.
            # This prevents Meta from retrying the webhook
            # while Gemini/Tavily is processing.
            # =================================================

            thread = threading.Thread(
                target=process_message_in_background,
                args=(
                    sender_phone,
                    msg_text
                ),
                daemon=True
            )

            thread.start()

            print(
                "🚀 Background AI thread started"
            )

            # =================================================
            # Return immediately to Meta
            # =================================================

            return "EVENT_RECEIVED", 200

        except Exception as e:

            print(
                f"❌ Webhook processing error: "
                f"{e}"
            )

            # مهم:
            # نرجع 200 حتى لا تعيد Meta إرسال نفس الحدث
            return "EVENT_RECEIVED", 200

    return "EVENT_RECEIVED", 200


# =========================================================
# Health Check
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return "Dairy Nutrition WhatsApp Bot is running ✅", 200


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print("----------------------------------------")
    print(
        f"🚀 Starting server on port {port}"
    )

    print(
        f"🤖 Gemini model: {GEMINI_MODEL}"
    )

    print(
        f"🔄 Gemini fallback: "
        f"{GEMINI_FALLBACK_MODEL}"
    )

    print(
        f"📱 WhatsApp API: "
        f"{GRAPH_API_VERSION}"
    )

    print("----------------------------------------")

    app.run(
        host="0.0.0.0",
        port=port
    )
