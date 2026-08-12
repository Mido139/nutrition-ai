import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
import json
from PIL import Image  # مكتبة معالجة الصور

# إعداد واجهة الموقع
st.set_page_config(page_title="Dairy Cattle AI | مساعد تغذية الأبقار", page_icon="🐄", layout="centered")

# --- تنسيق CSS مخصص ---
st.markdown("""
<style>
    div[data-testid="stButton"] button {
        border-radius: 20px;
        border: 1px solid #d3d3d3;
        background-color: transparent;
        color: #333;
        padding: 0.5rem 1rem;
        width: 100%;
        transition: all 0.3s;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
        background-color: #f9f9f9;
    }
    .stFileUploader {
        padding-bottom: 0rem;
        margin-bottom: -1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- نظام اللغات والترجمة ---
if "lang" not in st.session_state:
    st.session_state.lang = "ar"

# قاموس النصوص
ui = {
    "ar": {
        "login_title": "🔐 تسجيل الدخول",
        "login_sub": "مرحباً بك في النظام الذكي لإدارة الأبقار الحلوب",
        "email_label": "📧 البريد الإلكتروني",
        "pass_label": "🔑 كلمة المرور",
        "login_btn": "تسجيل الدخول",
        "login_err": "❌ البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        "logout_btn": "🚪 تسجيل الخروج",
        "main_title": "🐄 مساعد تغذية الأبقار الحلوب",
        "main_desc": "مرحباً بك! أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.",
        "sidebar_title": "💬 سجل المحادثات",
        "new_chat": "➕ محادثة جديدة",
        "your_chats": "📚 محادثاتك:",
        "chat_prefix": "المحادثة",
        "loading": "جاري مسح قواعد البيانات العلمية وتحليل المعطيات...",
        "ai_err": "عذراً، لم نتمكن من معالجة الإجابة حالياً عبر النماذج المتاحة.",
        "api_err": "لا توجد نماذج ذكاء اصطناعي متاحة في مفتاحك.",
        "api_missing": "⚠️ لم يتم العثور على مفاتيح API. يرجى التأكد من إضافتها.",
        "sys_err": "حدث خطأ أثناء المعالجة:",
        "sugg_1_btn": "كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟",
        "sugg_1_q": "كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟",
        "sugg_2_btn": "🌾 حلل مكون علف وتحقق من جودة العناصر الغذائية",
        "sugg_2_q": "ما هي طرق تحليل مكونات الأعلاف والتحقق من جودة العناصر الغذائية للأبقار؟",
        "sugg_3_btn": "📄 حلل ملف نظامي الغذائي واقترح تحسينات",
        "sugg_3_q": "ما هي أسس تحليل وتطوير النظم الغذائية للأبقار الحلوب؟",
        "sugg_4_btn": "🖼️ حلل صورة بقرة لتحديد درجة حالة الجسم (BCS)",
        "sugg_4_q": "اشرح كيفية تحديد درجة حالة الجسم (BCS) للأبقار الحلوب وأهميتها.",
        "sugg_5_btn": "💩 حلل صورة الروث لتحديد درجة الروث",
        "sugg_5_q": "كيف يمكن تقييم وتحليل درجات روث الأبقار لضبط التغذية؟",
        "upload_lbl": "📷 إرفاق صورة للتحليل (اختياري)",
        "upload_succ": "✅ تم إرفاق الصورة. اكتب سؤالك في الشريط بالأسفل واضغط Enter.",
        "chat_input": "اسأل عن الحميات، المكونات، أو ارفع صورة واسأل عنها...",
        "img_caption": "الصورة المرفقة",
        "lang_rule": "7. تطابق اللغة (Language Matching): يجب أن ترد على المستخدم بنفس لغة سؤاله تماماً. (إذا سأل باللغة الإنجليزية أجب باللغة الإنجليزية، وإذا سأل بالعربية أجب بالعربية)."
    },
    "en": {
        "login_title": "🔐 Login",
        "login_sub": "Welcome to the Smart Dairy Cattle Management System",
        "email_label": "📧 Email",
        "pass_label": "🔑 Password",
        "login_btn": "Login",
        "login_err": "❌ Invalid email or password.",
        "logout_btn": "🚪 Logout",
        "main_title": "🐄 Dairy Cattle Nutrition Assistant",
        "main_desc": "Welcome! I am your AI assistant specialized exclusively in academic research for dairy cattle nutrition.",
        "sidebar_title": "💬 Chat History",
        "new_chat": "➕ New Chat",
        "your_chats": "📚 Your Chats:",
        "chat_prefix": "Chat",
        "loading": "Scanning scientific databases and analyzing data...",
        "ai_err": "Sorry, we couldn't process the answer via available models right now.",
        "api_err": "No AI models available for your API key.",
        "api_missing": "⚠️ API keys not found. Please ensure they are added.",
        "sys_err": "Error during processing:",
        "sugg_1_btn": "How to formulate a diet for high-yielding dairy cows?",
        "sugg_1_q": "How do I formulate a diet for high-yielding dairy cows?",
        "sugg_2_btn": "🌾 Analyze feed components and verify nutrient quality",
        "sugg_2_q": "What are the methods for analyzing feed components and verifying nutrient quality for dairy cows?",
        "sugg_3_btn": "📄 Analyze my diet plan and suggest improvements",
        "sugg_3_q": "What are the principles of analyzing and developing dairy cattle diets?",
        "sugg_4_btn": "🖼️ Analyze cow image to determine BCS",
        "sugg_4_q": "Explain how to determine Body Condition Score (BCS) for dairy cows and its importance.",
        "sugg_5_btn": "💩 Analyze manure image for scoring",
        "sugg_5_q": "How to evaluate and analyze dairy cow manure scores to adjust nutrition?",
        "upload_lbl": "📷 Attach Image for Analysis (Optional)",
        "upload_succ": "✅ Image attached. Type your question below and press Enter.",
        "chat_input": "Ask about diets, ingredients, or upload an image...",
        "img_caption": "Attached Image",
        "lang_rule": "7. Language Matching: You MUST respond in the exact same language as the user's query. (If they ask in English, answer in English. If they ask in Arabic, answer in Arabic)."
    }
}

t = ui[st.session_state.lang]

# --- زر تبديل اللغة (Language Toggle) ---
with st.sidebar:
    lang_button_label = "🌐 Switch to English" if st.session_state.lang == "ar" else "🌐 التبديل للعربية"
    if st.button(lang_button_label, use_container_width=True):
        st.session_state.lang = "en" if st.session_state.lang == "ar" else "ar"
        st.rerun()
    st.write("---")

# --- نظام تسجيل الدخول ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown(f"<h1 style='text-align: center;'>{t['login_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>{t['login_sub']}</p>", unsafe_allow_html=True)
    
    CORRECT_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cow.com")
    CORRECT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input(t['email_label'])
            password = st.text_input(t['pass_label'], type="password")
            submit_button = st.form_submit_button(t['login_btn'], use_container_width=True)

            if submit_button:
                if email == CORRECT_EMAIL and password == CORRECT_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error(t['login_err'])
    st.stop()

# ==========================================
# --- الواجهة الرئيسية للموقع ---
# ==========================================

HISTORY_FILE = "chats_history.json"

def load_chats():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {f"{t['chat_prefix']} 1": []}

def save_chats(chats_dict):
    chats_to_save = {}
    for chat_name, msgs in chats_dict.items():
        clean_msgs = []
        for msg in msgs:
            clean_msgs.append({"role": msg.get("role"), "content": msg.get("content")})
        chats_to_save[chat_name] = clean_msgs
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chats_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

# عنوان التطبيق
st.title(t['main_title'])
st.write(t['main_desc'])

# زر تسجيل الخروج
with st.sidebar:
    if st.button(t['logout_btn'], use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.write("---")

# مفاتيح الـ API
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error(t['api_missing'])
    st.stop()

# إعداد الذاكرة
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
if "current_chat" not in st.session_state:
    st.session_state.current_chat = list(st.session_state.chats.keys())[-1] if st.session_state.chats else f"{t['chat_prefix']} 1"
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = len(st.session_state.chats) if st.session_state.chats else 1

# إدارة المحادثات في الشريط الجانبي
with st.sidebar:
    st.header(t['sidebar_title'])
    
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.chat_counter += 1
        new_chat_name = f"{t['chat_prefix']} {st.session_state.chat_counter}"
        st.session_state.chats[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        save_chats(st.session_state.chats)
        st.rerun()
        
    st.write("---")
    st.write(t['your_chats'])
    
    for chat_name in list(st.session_state.chats.keys()):
        if chat_name == st.session_state.current_chat:
            st.button(f"🟢 {chat_name}", key=f"btn_{chat_name}", disabled=True, use_container_width=True)
        else:
            if st.button(f"⚪ {chat_name}", key=f"btn_{chat_name}", use_container_width=True):
                st.session_state.current_chat = chat_name
                st.rerun()

current_messages = st.session_state.chats[st.session_state.current_chat]

for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

# دالة المعالجة الأساسية
def process_query(query, img=None):
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": query, "image": img})
    save_chats(st.session_state.chats)
    
    with st.chat_message("user"):
        st.markdown(query)
        if img:
            st.image(img, caption=t['img_caption'], use_container_width=True)

    with st.chat_message("assistant"):
        with st.spinner(t['loading']):
            try:
                scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية OR journal OR pubmed OR sciencedirect OR ncbi)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=8)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"Source [{index + 1}]:\n- Title: {result['title']}\n- URL: {result['url']}\n- Info: {result['content']}\n\n"
                
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار متخصص *حصرياً* في تغذية، فسيولوجيا هضم، وإدارة الأبقار الحلوب (Dairy Cattle) فقط.
                    مهمتك هي تقديم إجابات علمية وبيولوجية دقيقة وشاملة من خلال الدمج بين مصدرين أساسيين:
                    أولاً: المرجع الأكاديمي الأساسي الدائم (Nutrient Requirements of Dairy Cattle - NASEM): https://www.ncbi.nlm.nih.gov/books/NBK600603/
                    ثانياً: "مجموعة الأبحاث والمصادر العلمية المتاحة من البحث الحي" المرفقة أدناه.
                    
                    التزم بالقوانين التالية بصرامة شديدة:
                    1. التخصص الحصري: يُحظر عليك تماماً الإجابة على أي أسئلة تتعلق بحيوانات أخرى. إذا كان السؤال لا يخص الأبقار الحلوب، اعتذر بلباقة.
                    2. تحليل الصور: إذا أرفق المستخدم صورة، قم بفحصها بعناية شديدة وقدم تقييماً علمياً دقيقاً بناءً على قواعد الأبقار الحلوب.
                    3. الشمول والدقة: اجمع المعلومات من المرجع الثابت ومن الأبحاث الحية لتقديم إجابة متكاملة تخص الأبقار الحلوب.
                    4. التوثيق الأكاديمي: يجب توثيق كل معلومة داخل النص [NASEM] أو [1].
                    5. منع التأليف نهائياً: إذا لم تجد إجابة علمية دقيقة، قل بوضوح: "لا توفر المراجع الحالية بيانات علمية دقيقة للإجابة على هذا السؤال".
                    6. قسم المراجع: في نهاية الإجابة، قم بعمل قسم "المراجع العلمية" واذكر فيها الروابط المعتمدة.
                    {t['lang_rule']}
                    
                    سؤال المستخدم: {query}
                    
                    الأبحاث والمصادر العلمية المتاحة من البحث الحي:
                    {context}
                    """
                    
                    contents_to_send = [prompt]
                    if img:
                        contents_to_send.append(img)
                        
                    answer = None
                    preferred_models = ["models/gemini-1.5-pro-latest", "models/gemini-pro"]
                    models_to_try = preferred_models + [m for m in available_models if m not in preferred_models]

                    for model_name in models_to_try:
                        try:
                            model = genai.GenerativeModel(model_name)
                            answer = model.generate_content(contents_to_send)
                            break
                        except Exception:
                            continue
                    
                    if answer:
                        st.markdown(answer.text)
                        st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": answer.text})
                        save_chats(st.session_state.chats)
                    else:
                        st.error(t['ai_err'])
                else:
                    st.error(t['api_err'])
                    
            except Exception as e:
                st.error(f"{t['sys_err']} {e}")

# أزرار الاقتراحات السريعة
if len(current_messages) == 0:
    st.write("") 
    col1, col2 = st.columns(2)
    
    with col2:
        if st.button(t['sugg_1_btn']):
            process_query(t['sugg_1_q'])
        if st.button(t['sugg_2_btn']):
            process_query(t['sugg_2_q'])
            
    with col1:
        if st.button(t['sugg_3_btn']):
            process_query(t['sugg_3_q'])
        if st.button(t['sugg_4_btn']):
            process_query(t['sugg_4_q'])

    col3, col4, col5 = st.columns([1, 2, 1])
    with col4:
        if st.button(t['sugg_5_btn']):
            process_query(t['sugg_5_q'])

# --- منطقة الإدخال السفلية ---
st.write("---")
uploaded_file = st.file_uploader(t['upload_lbl'], type=["jpg", "jpeg", "png"])

if uploaded_file:
    img_to_analyze = Image.open(uploaded_file)
    st.success(t['upload_succ'])
else:
    img_to_analyze = None

user_input = st.chat_input(t['chat_input'])
if user_input:
    process_query(user_input, img=img_to_analyze)
