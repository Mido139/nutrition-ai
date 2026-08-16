from flask import Flask, request
import requests
import os
import threading
import time
import random

from google import genai
from tavily import TavilyClient


# =========================================================
# Flask
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

GRAPH_API_VERSION = os.environ.get(
    "GRAPH_API_VERSION",
    "v19.0"
)


# =========================================================
# Gemini Models
# =========================================================

# الموديل الأساسي
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview"
]


# =========================================================
# Startup Logs
# =========================================================

print("")
print("========================================")
print("🐄 Dairy Nutrition WhatsApp Bot")
print("========================================")

print(
    f"WhatsApp Phone Number ID: "
    f"{PHONE_NUMBER_ID}"
)

print(
    f"Graph API Version: "
    f"{GRAPH_API_VERSION}"
)

print(
    f"Gemini Models: "
    f"{GEMINI_MODELS}"
)

print("========================================")


# =========================================================
# Gemini Client
# =========================================================

try:

    if not GEMINI_API_KEY:

        raise Exception(
            "GEMINI_API_KEY is missing"
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    print(
        "✅ Gemini client initialized"
    )

except Exception as e:

    client = None

    print(
        f"❌ Gemini initialization error: {e}"
    )


# =========================================================
# Tavily Client
# =========================================================

try:

    if not TAVILY_API_KEY:

        raise Exception(
            "TAVILY_API_KEY is missing"
        )

    tavily_client = TavilyClient(
        api_key=TAVILY_API_KEY
    )

    print(
        "✅ Tavily client initialized"
    )

except Exception as e:

    tavily_client = None

    print(
        f"❌ Tavily initialization error: {e}"
    )


# =========================================================
# Duplicate Message Protection
# =========================================================

processed_messages = set()

processed_messages_lock = threading.Lock()


def is_message_processed(message_id):

    with processed_messages_lock:

        if message_id in processed_messages:

            return True

        processed_messages.add(
            message_id
        )

        # منع الذاكرة من النمو بشكل مستمر
        if len(processed_messages) > 5000:

            old_ids = list(
                processed_messages
            )[:1000]

            for old_id in old_ids:

                processed_messages.discard(
                    old_id
                )

        return False


# =========================================================
# WhatsApp Send Message
# =========================================================

def send_whatsapp_message(
    to,
    text
):

    if not WHATSAPP_TOKEN:

        print(
            "❌ WHATSAPP_TOKEN is missing"
        )

        return False

    if not PHONE_NUMBER_ID:

        print(
            "❌ PHONE_NUMBER_ID is missing"
        )

        return False

    if not to:

        print(
            "❌ Recipient phone number missing"
        )

        return False

    if not text:

        print(
            "❌ Message text is empty"
        )

        return False


    # WhatsApp text size protection
    if len(text) > 4000:

        text = (
            text[:3950]
            + "\n\n"
            + "[تم اختصار الإجابة]"
        )


    url = (
        "https://graph.facebook.com/"
        + GRAPH_API_VERSION
        + "/"
        + PHONE_NUMBER_ID
        + "/messages"
    )


    headers = {

        "Authorization":
            f"Bearer {WHATSAPP_TOKEN}",

        "Content-Type":
            "application/json"
    }


    data = {

        "messaging_product":
            "whatsapp",

        "to":
            to,

        "type":
            "text",

        "text": {

            "body":
                text
        }
    }


    try:

        print("")
        print("----------------------------------------")
        print(
            f"📤 Sending WhatsApp message to "
            f"{to}"
        )


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

            print(
                "✅ WhatsApp message sent"
            )

            return True


        print(
            "❌ WhatsApp message failed"
        )

        return False


    except Exception as e:

        print(
            f"❌ WhatsApp send error: {e}"
        )

        return False


# =========================================================
# Tavily Search
# =========================================================

def search_scientific_sources(
    query
):

    if tavily_client is None:

        print(
            "⚠️ Tavily client unavailable"
        )

        return "", []


    try:

        scientific_query = (

            query

            + " AND "

            + "(dairy cattle OR dairy cows "
              "OR الأبقار الحلوب)"

            + " (scientific research "
              "OR academic study "
              "OR بحث علمي "
              "OR دراسة أكاديمية)"
        )


        print("")
        print(
            "🔎 Tavily query:"
        )

        print(
            scientific_query
        )


        search_response = (

            tavily_client.search(

                scientific_query,

                search_depth="advanced",

                max_results=3
            )
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

        references = []


        for index, result in enumerate(
            results
        ):

            title = result.get(
                "title",
                "Unknown"
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

                f"\n"
                f"===== Source {index + 1} =====\n"

                f"Title: {title}\n"

                f"URL: {url}\n"

                f"Information:\n{content}\n"
            )


            # حفظ بيانات المصدر الحقيقية
            # لا يتم توليدها بواسطة Gemini.
            if url:

                references.append({
                    "title": title,
                    "url": url
                })


        return context, references


    except Exception as e:

        print(
            f"❌ Tavily error: {e}"
        )

        return "", []



# =========================================================
# Gemini - Interactions API
# =========================================================

def ask_gemini(
    prompt
):

    if client is None:

        return (
            "⚠️ حدث خطأ في الاتصال "
            "بخدمة Gemini."
        )


    last_error = None


    for model_name in GEMINI_MODELS:

        try:

            print("")
            print("----------------------------------------")

            print(
                f"🤖 Gemini model: "
                f"{model_name}"
            )

            print(
                "🤖 API: Interactions API"
            )


            interaction = (

                client.interactions.create(

                    model=model_name,

                    input=prompt
                )
            )


            reply = (
                interaction.output_text
            )


            if reply:

                print(
                    "✅ Gemini response "
                    "received successfully"
                )

                return reply.strip()


            print(
                "⚠️ Gemini returned "
                "empty response"
            )


        except Exception as e:

            last_error = e

            error_text = str(e)


            print("")
            print(
                f"❌ Gemini error "
                f"({model_name}):"
            )

            print(
                error_text
            )


            # -------------------------------------------------
            # Model not available
            # -------------------------------------------------

            if (
                "404" in error_text
                or
                "NOT_FOUND" in error_text
            ):

                print(
                    "⚠️ Model unavailable."
                )

                print(
                    "➡️ Trying next model..."
                )

                continue


            # -------------------------------------------------
            # High demand / temporary unavailable
            # -------------------------------------------------

            if (
                "503" in error_text
                or
                "UNAVAILABLE" in error_text
            ):

                print(
                    "⚠️ Gemini temporarily "
                    "unavailable."
                )

                print(
                    "⏳ Waiting 2 seconds..."
                )

                time.sleep(2)

                continue


            # -------------------------------------------------
            # Rate limit
            # -------------------------------------------------

            if (
                "429" in error_text
                or
                "RESOURCE_EXHAUSTED"
                in error_text
            ):

                print(
                    "⚠️ Gemini rate limit."
                )

                print(
                    "⏳ Waiting 3 seconds..."
                )

                time.sleep(3)

                continue


            # -------------------------------------------------
            # Other errors
            # -------------------------------------------------

            print(
                "⚠️ Trying next Gemini model..."
            )


    # =====================================================
    # All Models Failed
    # =====================================================

    print("")
    print("----------------------------------------")

    print(
        "❌ All Gemini models failed"
    )

    print(
        f"Last error: {last_error}"
    )


    return (
        "⚠️ حدث خطأ مؤقت أثناء معالجة "
        "السؤال بالذكاء الاصطناعي.\n\n"
        "من فضلك حاول مرة أخرى بعد قليل."
    )


# =========================================================
# AI Processing
# =========================================================

def process_with_ai(
    query,
    progress_callback=None
):

    # =================================================
    # هوية المساعد
    # =================================================
    #
    # أسئلة الهوية يتم الرد عليها مباشرة بدون Tavily أو Gemini.
    # كل رد يذكر المطورين الثلاثة معًا:
    # المهندس محمد ناصر + المهندس محمد خيري + المهندس ياسين ممدوح.
    # ويتم اختيار صياغة مختلفة عشوائيًا في كل مرة.

    identity_triggers = [
        "انت مين",
        "إنت مين",
        "من انت",
        "من أنت",
        "مين انت",
        "مين أنت",
        "مين حضرتك",
        "حضرتك مين",
        "عرف نفسك",
        "عرفني بنفسك",
        "ممكن تعرفني بنفسك",
        "من قام ببرمجتك",
        "مين برمجك",
        "مين عملك",
        "مين طورك",
        "مين المطور",
        "مين المبرمج",
        "مين اللي برمجك",
        "مين اللي طورك",
        "who are you",
        "what are you",
        "who created you",
        "who programmed you"
    ]

    identity_responses = [
        (
            "أنا استشاري تغذية متخصص في تغذية وإدارة الأبقار الحلوب 🐄، "
            "وتم تطويري وبرمجتي بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح. "
            "وصُممت لمساعدتك في الحصول على معلومات وإرشادات علمية وعملية "
            "متخصصة في مجال تغذية وإدارة الأبقار الحلوب."
        ),
        (
            "أنا مساعد واستشاري متخصص في تغذية وإدارة الأبقار الحلوب. "
            "تمت برمجتي وتطويري بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح، "
            "وهدفي تقديم معلومات علمية وعملية موثوقة في مجال "
            "Dairy Cattle Nutrition & Management."
        ),
        (
            "ببساطة، أنا استشاري تغذية متخصص في الأبقار الحلوب 🐄. "
            "تم تصميمي وبرمجتي بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح، "
            "وأعمل على تقديم إجابات متخصصة حول تغذية وإدارة الأبقار الحلوب."
        ),
        (
            "أنا نظام استشاري متخصص في تغذية وإدارة الأبقار الحلوب. "
            "وراء تطويري وبرمجتي المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح، "
            "وقد تم تصميمي لتقديم إجابات علمية وعملية في مجال تخصصي."
        ),
        (
            "أهلاً بك 👋، أنا استشاري تغذية متخصص في تغذية وإدارة الأبقار الحلوب. "
            "تم تطويري وبرمجتي بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح، "
            "وتم تصميمي لمساعدتك في الموضوعات المتعلقة بتغذية وإدارة الأبقار الحلوب."
        ),
        (
            "أنا استشاري متخصص في مجال Dairy Cattle Nutrition & Management، "
            "أي تغذية وإدارة الأبقار الحلوب. "
            "تمت برمجتي وتطويري بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح، "
            "وأركز على تقديم معلومات علمية وعملية في مجال تخصصي."
        ),
        (
            "أنا مساعدك المتخصص في تغذية الأبقار الحلوب 🐄، "
            "وقد تم تطويري بواسطة المهندس محمد ناصر والمهندس محمد خيري "
            "والمهندس ياسين ممدوح. "
            "مهمتي مساعدتك بالمعلومات والإرشادات العلمية المتعلقة بتغذية وإدارة الأبقار الحلوب."
        ),
        (
            "أنا استشاري تغذية متخصص في تغذية وإدارة قطعان الأبقار الحلوب. "
            "تم إنشائي وتطويري وبرمجتي بواسطة المهندس محمد ناصر "
            "والمهندس محمد خيري والمهندس ياسين ممدوح، "
            "وتم تصميمي لتقديم المعرفة والإرشادات العلمية في مجال تغذية الأبقار الحلوب."
        )
    ]

    def normalize_identity_text(text):
        text = str(text).strip().lower()

        replacements = {
            "إ": "ا",
            "أ": "ا",
            "آ": "ا",
            "ى": "ي",
            "ة": "ه",
            "ـ": ""
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        for punctuation in [
            "؟", "?", "!", "،", ",", ".", ":",
            ";", "؛", "-", "_", '"', "'", "\n"
        ]:
            text = text.replace(punctuation, " ")

        return " ".join(text.split())

    normalized_query = normalize_identity_text(query)

    normalized_triggers = [
        normalize_identity_text(trigger)
        for trigger in identity_triggers
    ]

    is_identity_question = any(
        normalized_query == trigger
        or normalized_query.startswith(trigger + " ")
        for trigger in normalized_triggers
    )

    if is_identity_question and len(normalized_query) <= 120:

        identity_answer = random.choice(identity_responses)

        print("")
        print("========================================")
        print("🤖 Identity question detected")
        print("========================================")
        print(f"📝 Question: {query}")
        print(
            "👨‍💻 Developers: Engineer Mohamed Nasser + "
            "Engineer Mohamed Khairy + Engineer Yassin Mamdouh"
        )
        print("========================================")

        return identity_answer, []

    try:

        print("")
        print("========================================")
        print("🧠 Starting AI processing")
        print("========================================")

        print(
            f"📝 Question: {query}"
        )


        # =================================================
        # Tavily
        # =================================================

        context, references = search_scientific_sources(
            query
        )

        # -------------------------------------------------
        # تحديث المستخدم بعد انتهاء البحث
        # وقبل بدء تحليل Gemini
        # -------------------------------------------------

        if progress_callback:

            if references:

                progress_callback(
                    "📚 تم العثور على "
                    f"{len(references)} مراجع علمية مناسبة.\n"
                    "🧠 جاري تحليل المراجع وصياغة الإجابة..."
                )

            else:

                progress_callback(
                    "⚠️ لم يتم العثور على مراجع مناسبة حاليًا.\n"
                    "🧠 جاري تحليل السؤال وصياغة الإجابة..."
                )


        # =================================================
        # Prompt
        # =================================================

        prompt = f"""
أنت خبير متخصص في تغذية وإدارة الأبقار الحلوب
(Dairy Cattle Nutrition & Management).

مهمتك الإجابة على سؤال المستخدم باللغة العربية
بشكل علمي ودقيق وعملي.

اعتمد على مبادئ NASEM وتوصيات تغذية الأبقار
الحلوب، واستفد من نتائج البحث العلمي الموجودة
في السياق أدناه.

قواعد الإجابة:

1. أجب مباشرة على السؤال.
2. لا تكرر السؤال.
3. لا تكتب "جاري البحث".
4. لا ترسل أكثر من إجابة.
5. لا تخترع أرقامًا أو مراجع.
6. إذا كانت البيانات غير كافية، اذكر البيانات
   التي تحتاجها بوضوح.
7. استخدم نقاطًا وعناوين عند الحاجة.
8. اجعل الإجابة مناسبة للإرسال عبر WhatsApp.
9. لا تستخدم Markdown معقد جدًا.
10. لا تذكر أنك نموذج ذكاء اصطناعي.
11. لا تخترع أي مصدر أو مرجع.
12. إذا استخدمت معلومة من سياق البحث، حاول الإشارة إليها داخل النص بصيغة [1] أو [2] أو [3] حسب رقم المصدر.
13. لا تكتب قسم "المراجع" بنفسك؛ البرنامج سيضيف المراجع الحقيقية وروابطها تلقائيًا بعد إجابتك.
14. إذا لم يكن هناك مصدر مناسب في سياق البحث، صرّح بعدم توفر مصدر مناسب بدل اختراع مرجع.
15. إذا كان السؤال متعلقًا بتغذية الأبقار،
    اذكر العوامل المؤثرة المهمة مثل:
    - وزن الحيوان
    - إنتاج اللبن
    - نسبة الدهن
    - نسبة البروتين
    - مرحلة الإدرار
    - DMI
    - العمر
    - حالة الجسم
    - نوع وجودة العلف
    حسب ارتباطها بالسؤال.

السياق العلمي من البحث:

{context}


سؤال المستخدم:

{query}
"""


        # =================================================
        # Gemini
        # =================================================

        reply = ask_gemini(
            prompt
        )


        print("")
        print(
            "✅ AI processing finished"
        )


        return reply, references


    except Exception as e:

        print(
            f"❌ AI processing error: {e}"
        )


        return (
            "⚠️ حدث خطأ أثناء معالجة "
            "السؤال. حاول مرة أخرى.",
            []
        )


# =========================================================
# Identity Question Detection
# =========================================================

def is_identity_question_for_progress(
    query
):

    triggers = [
        "انت مين",
        "إنت مين",
        "من انت",
        "من أنت",
        "مين انت",
        "مين أنت",
        "مين حضرتك",
        "حضرتك مين",
        "عرف نفسك",
        "عرفني بنفسك",
        "من قام ببرمجتك",
        "مين برمجك",
        "مين عملك",
        "مين طورك",
        "مين المطور",
        "مين المبرمج",
        "مين اللي برمجك",
        "مين اللي طورك",
        "who are you",
        "what are you",
        "who created you",
        "who programmed you"
    ]

    value = str(query).strip().lower()

    for old, new in {
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ـ": ""
    }.items():

        value = value.replace(
            old,
            new
        )

    for punctuation in [
        "؟", "?", "!", "،", ",", ".", ":",
        ";", "؛", "-", "_", '"', "'"
    ]:

        value = value.replace(
            punctuation,
            " "
        )

    value = " ".join(
        value.split()
    )

    for trigger in triggers:

        trigger = trigger.lower()

        for old, new in {
            "إ": "ا",
            "أ": "ا",
            "آ": "ا",
            "ى": "ي",
            "ة": "ه",
            "ـ": ""
        }.items():

            trigger = trigger.replace(
                old,
                new
            )

        trigger = " ".join(
            trigger.split()
        )

        if (
            value == trigger
            or value.startswith(
                trigger + " "
            )
        ):

            return True

    return False


def append_references(
    reply,
    references
):

    if not references:

        return reply

    references_text = (
        "\n\n"
        "📚 المصادر والمراجع:\n"
    )

    for index, reference in enumerate(
        references,
        start=1
    ):

        title = reference.get(
            "title",
            "مصدر علمي"
        )

        url = reference.get(
            "url",
            ""
        )

        references_text += (
            f"{index}. {title}\n"
        )

        if url:

            references_text += (
                f"🔗 {url}\n"
            )

    return (
        reply.rstrip()
        + references_text
    )


# =========================================================
# Background Processing
# =========================================================

def process_message_background(
    sender_phone,
    msg_text
):

    try:

        print("")
        print(
            "🚀 Background AI thread started"
        )


        # =================================================
        # رسالة مؤقتة للمستخدم أثناء البحث والتحليل
        # لا نرسلها لأسئلة الهوية لأن هذه الأسئلة
        # لا تحتاج بحثًا علميًا.
        # =================================================

        if not is_identity_question_for_progress(
            msg_text
        ):

            send_whatsapp_message(

                sender_phone,

                "🔎 جاري البحث عن المراجع العلمية المناسبة لسؤالك...\n"
                "⏳ لحظات من فضلك."
            )


        # =================================================
        # معالجة السؤال
        # =================================================

        def send_progress(message):

            send_whatsapp_message(
                sender_phone,
                message
            )


        reply, references = process_with_ai(
            msg_text,
            progress_callback=send_progress
        )


        # =================================================
        # إضافة المصادر الحقيقية بعد الإجابة
        # =================================================

        final_reply = append_references(
            reply,
            references
        )


        # =================================================
        # إرسال الإجابة النهائية مرة واحدة
        # =================================================

        print("")
        print(
            f"📤 Sending final answer to "
            f"{sender_phone}"
        )


        send_whatsapp_message(

            sender_phone,

            final_reply
        )


        print(
            "✅ Background processing completed"
        )


    except Exception as e:

        print(
            f"❌ Background processing error: "
            f"{e}"
        )

        send_whatsapp_message(
            sender_phone,
            "⚠️ حدث خطأ أثناء معالجة السؤال. "
            "من فضلك حاول مرة أخرى."
        )


# =========================================================
# WhatsApp Webhook
# =========================================================

@app.route(
    "/webhook",
    methods=["GET", "POST"]
)
def webhook():


    # =====================================================
    # GET - Meta Verification
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


        print("")
        print(
            "🔐 WhatsApp Webhook verification"
        )


        if (

            mode == "subscribe"

            and

            token == VERIFY_TOKEN

        ):

            print(
                "✅ Webhook verification successful"
            )

            return challenge, 200


        print(
            "❌ Webhook verification failed"
        )


        return (
            "Forbidden",
            403
        )


    # =====================================================
    # POST - Receive Message
    # =====================================================

    if request.method == "POST":

        body = request.get_json(
            silent=True
        )


        print("")
        print("========================================")
        print(
            "📩 WhatsApp Webhook received"
        )
        print("========================================")


        if not body:

            print(
                "⚠️ Empty webhook body"
            )

            return (
                "EVENT_RECEIVED",
                200
            )


        print(
            body
        )


        # =================================================
        # Check Object
        # =================================================

        if (

            body.get("object")

            !=

            "whatsapp_business_account"

        ):

            print(
                "ℹ️ Not WhatsApp Business event"
            )

            return (
                "EVENT_RECEIVED",
                200
            )


        try:

            entry = body.get(
                "entry",
                []
            )


            if not entry:

                return (
                    "EVENT_RECEIVED",
                    200
                )


            changes = entry[0].get(
                "changes",
                []
            )


            if not changes:

                return (
                    "EVENT_RECEIVED",
                    200
                )


            value = changes[0].get(
                "value",
                {}
            )


            messages = value.get(
                "messages",
                []
            )


            # =================================================
            # Status / Other Webhook Event
            # =================================================

            if not messages:

                print(
                    "ℹ️ Event contains no messages"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


            # =================================================
            # Get Message
            # =================================================

            message_data = messages[0]


            message_id = message_data.get(
                "id"
            )


            if not message_id:

                print(
                    "⚠️ Message ID missing"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


            print(
                f"🆔 Message ID: "
                f"{message_id}"
            )


            # =================================================
            # Duplicate Protection
            # =================================================

            if is_message_processed(
                message_id
            ):

                print(
                    "⚠️ DUPLICATE MESSAGE "
                    "- IGNORED"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


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


            # =================================================
            # Text Messages Only
            # =================================================

            if message_type != "text":

                print(
                    "ℹ️ Non-text message "
                    "- ignored"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


            # =================================================
            # Sender
            # =================================================

            sender_phone = message_data.get(
                "from"
            )


            # =================================================
            # Text
            # =================================================

            msg_text = (

                message_data

                .get(
                    "text",
                    {}
                )

                .get(
                    "body",
                    ""
                )
            )


            if not sender_phone:

                print(
                    "❌ Sender phone missing"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


            if not msg_text:

                print(
                    "❌ Message text missing"
                )

                return (
                    "EVENT_RECEIVED",
                    200
                )


            print(
                f"👤 Message received from: "
                f"{sender_phone}"
            )


            print(
                f"💬 User message: "
                f"{msg_text}"
            )


            # =================================================
            # IMPORTANT
            #
            # Start AI in background.
            #
            # Return 200 immediately to Meta.
            # =================================================

            thread = threading.Thread(

                target=
                    process_message_background,

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
            # IMPORTANT
            # =================================================

            return (
                "EVENT_RECEIVED",
                200
            )


        except Exception as e:

            print(
                f"❌ Webhook error: {e}"
            )


            # مهم جدًا:
            # نرجع 200 إلى Meta
            # حتى لا تعيد نفس الرسالة

            return (
                "EVENT_RECEIVED",
                200
            )


    return (
        "EVENT_RECEIVED",
        200
    )


# =========================================================
# Health Check
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return (
        "Dairy Nutrition WhatsApp Bot "
        "is running ✅",
        200
    )


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


    print("")
    print("========================================")
    print(
        f"🚀 Server starting on port {port}"
    )
    print("========================================")


    app.run(

        host="0.0.0.0",

        port=port
    )
