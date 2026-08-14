from flask import Flask, request, jsonify
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


# =========================================================
# API Versions / Models
# =========================================================

WHATSAPP_API_VERSION = "v26.0"

# Gemini 3.6 Flash - Stable
GEMINI_MODEL = "gemini-3.6-flash"


# =========================================================
# تهيئة Gemini
# =========================================================

gemini_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("Gemini client initialized successfully.")

    except Exception as e:
        print(
            f"Gemini Init Error: {e}"
        )


# =========================================================
# تهيئة Tavily
# =========================================================

tavily_client = None

if TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(
            api_key=TAVILY_API_KEY
        )

        print("Tavily client initialized successfully.")

    except Exception as e:
        print(
            f"Tavily Init Error: {e}"
        )


# =========================================================
# AI Processing
# =========================================================

def ask_ai(query):

    try:

        print("======================================")
        print("Starting AI processing...")
        print("======================================")


        # -------------------------------------------------
        # البحث العلمي عبر Tavily
        # -------------------------------------------------

        context = ""

        if tavily_client:

            print("Searching Tavily...")

            search_query = (
                query
                + " AND "
                "(dairy cattle OR dairy cows OR الأبقار الحلوب) "
                "(بحث علمي OR دراسة أكاديمية)"
            )

            print(
                f"Tavily query: {search_query}"
            )

            search_response = tavily_client.search(
                search_query,
                search_depth="advanced",
                max_results=3
            )

            results = search_response.get(
                "results",
                []
            )

            print(
                f"Tavily returned {len(results)} results."
            )


            for i, item in enumerate(results):

                title = item.get(
                    "title",
                    ""
                )

                url = item.get(
                    "url",
                    ""
                )

                content = item.get(
                    "content",
                    ""
                )

                context += (
                    f"\nSource [{i + 1}]\n"
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Information: {content}\n"
                )

        else:

            print(
                "TAVILY_API_KEY is not available."
            )


        # -------------------------------------------------
        # Prompt
        # -------------------------------------------------

        prompt = f"""
أنت خبير وباحث أكاديمي متخصص في تغذية وإدارة الأبقار
الحلوب (Dairy Cattle Nutrition and Management).

أجب على سؤال المستخدم باللغة العربية بأسلوب علمي واضح
ودقيق.

اعتمد على مبادئ NASEM في تغذية الأبقار الحلوب، واستفد
من الأبحاث والمصادر العلمية الموجودة في السياق.

لا تخترع مراجع أو أرقامًا غير مؤكدة.

إذا كانت الإجابة تعتمد على عمر الحيوان أو إنتاج الحليب
أو وزن الجسم أو مرحلة الإدرار، وضح ذلك.

المصادر العلمية:
{context}

سؤال المستخدم:
{query}

قدم إجابة منظمة ومفهومة، ويمكن استخدام النقاط والجداول
عند الحاجة.
"""


        # -------------------------------------------------
        # التأكد من Gemini API
        # -------------------------------------------------

        if not gemini_client:

            print(
                "Gemini client is not initialized."
            )

            return (
                "⚠️ مفتاح Gemini API غير متوفر "
                "في إعدادات Render."
            )


        # -------------------------------------------------
        # Gemini 3.6 Flash
        # -------------------------------------------------

        print(
            f"Sending request to Gemini model: "
            f"{GEMINI_MODEL}"
        )


        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )


        # -------------------------------------------------
        # قراءة الإجابة
        # -------------------------------------------------

        if response and response.text:

            answer = response.text.strip()

            print(
                "Gemini response received successfully."
            )

            return answer


        print(
            "Gemini returned an empty response."
        )

        return (
            "⚠️ لم أتمكن من الحصول على إجابة من "
            "Gemini حاليًا."
        )


    except Exception as e:

        print(
            "======================================"
        )

        print(
            f"AI Process Error: {e}"
        )

        print(
            "======================================"
        )

        return (
            "⚠️ حدث خطأ أثناء معالجة السؤال "
            "بالذكاء الاصطناعي. حاول مرة أخرى."
        )


# =========================================================
# إرسال رسالة WhatsApp
# =========================================================

def send_whatsapp_message(
    to_number,
    text_msg
):

    if not WHATSAPP_TOKEN:

        print(
            "ERROR: WHATSAPP_TOKEN is missing."
        )

        return False


    if not PHONE_NUMBER_ID:

        print(
            "ERROR: PHONE_NUMBER_ID is missing."
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


    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": text_msg
        }
    }


    try:

        print(
            f"Sending WhatsApp message to: "
            f"{to_number}"
        )


        response = requests.post(
            url,
            headers=headers,
            json=payload,
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
            f"WhatsApp Send Error: {e}"
        )

        return False


# =========================================================
# Test AI Endpoint
# =========================================================

@app.route(
    "/test-ai",
    methods=["GET"]
)
def test_ai():

    test_query = request.args.get(
        "query",
        "ما هو BCS في الأبقار الحلوب؟"
    )

    answer = ask_ai(
        test_query
    )

    return jsonify({
        "query": test_query,
        "answer": answer
    })


# =========================================================
# WhatsApp Webhook
# =========================================================

@app.route(
    "/webhook",
    methods=["GET", "POST"]
)
def webhook():

    # =====================================================
    # Meta Verification
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


        print(
            "Webhook verification request received."
        )


        if (
            mode == "subscribe"
            and token == VERIFY_TOKEN
        ):

            print(
                "Webhook verification successful."
            )

            return challenge, 200


        print(
            "Webhook verification failed."
        )

        return "Forbidden", 403


    # =====================================================
    # استقبال الرسائل
    # =====================================================

    if request.method == "POST":

        try:

            body = request.get_json(
                silent=True
            )


            print(
                "======================================"
            )

            print(
                "WhatsApp Webhook received"
            )

            print(
                "======================================"
            )

            print(
                body
            )


            if not body:

                return "EVENT_RECEIVED", 200


            if body.get(
                "object"
            ) != "whatsapp_business_account":

                return "EVENT_RECEIVED", 200


            # -------------------------------------------------
            # قراءة Events
            # -------------------------------------------------

            for entry in body.get(
                "entry",
                []
            ):

                for change in entry.get(
                    "changes",
                    []
                ):

                    value = change.get(
                        "value",
                        {}
                    )


                    messages = value.get(
                        "messages",
                        []
                    )


                    # -------------------------------------------------
                    # Status / delivery events
                    # -------------------------------------------------

                    if not messages:

                        print(
                            "Webhook event contains no messages."
                        )

                        continue


                    # -------------------------------------------------
                    # معالجة الرسائل
                    # -------------------------------------------------

                    for msg in messages:

                        sender_phone = msg.get(
                            "from"
                        )

                        message_type = msg.get(
                            "type"
                        )


                        print(
                            f"Message received from: "
                            f"{sender_phone}"
                        )

                        print(
                            f"Message type: "
                            f"{message_type}"
                        )


                        # -------------------------------------------------
                        # الرسائل النصية
                        # -------------------------------------------------

                        if message_type == "text":

                            user_text = (
                                msg.get(
                                    "text",
                                    {}
                                )
                                .get(
                                    "body",
                                    ""
                                )
                                .strip()
                            )


                            if not user_text:

                                continue


                            print(
                                f"User message: "
                                f"{user_text}"
                            )


                            # -------------------------------------------------
                            # رسالة الانتظار
                            # -------------------------------------------------

                            send_whatsapp_message(
                                sender_phone,
                                "⏳ جاري البحث والتحليل..."
                            )


                            # -------------------------------------------------
                            # AI
                            # -------------------------------------------------

                            final_answer = ask_ai(
                                user_text
                            )


                            # -------------------------------------------------
                            # إرسال الإجابة
                            # -------------------------------------------------

                            send_whatsapp_message(
                                sender_phone,
                                final_answer
                            )


                        else:

                            send_whatsapp_message(
                                sender_phone,
                                "⚠️ عذرًا، أستقبل الرسائل النصية فقط حاليًا."
                            )


            return "EVENT_RECEIVED", 200


        except Exception as e:

            print(
                "======================================"
            )

            print(
                f"Webhook Error: {e}"
            )

            print(
                "======================================"
            )

            # نرجع 200 إلى Meta حتى لا تعيد إرسال الحدث
            return "EVENT_RECEIVED", 200


# =========================================================
# Home
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return (
        "Dairy Nutrition AI Bot is Active 🚀",
        200
    )


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
