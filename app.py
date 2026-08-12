import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
import json
import hashlib
from PIL import Image

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

ui = {
    "ar": {
        "auth_title": "🔐 بوابة الدخول",
        "auth_sub": "مرحباً بك في النظام الذكي لإدارة الأبقار الحلوب",
        "tab_login": "تسجيل الدخول",
        "tab_register": "إنشاء حساب جديد",
        "name_label": "👤 الاسم الكامل",
        "email_label": "📧 البريد الإلكتروني",
        "pass_label": "🔑 كلمة المرور",
        "pass_confirm_label": "🔑 تأكيد كلمة المرور",
        "login_btn": "تسجيل الدخول",
        "register_btn": "طلب إنشاء الحساب",
        "login_err": "❌ البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        "pending_err": "⏳ حسابك قيد المراجعة. يرجى انتظار موافقة الإدارة.",
        "reg_err_pass": "❌ كلمتا المرور غير متطابقتين.",
        "reg_err_exists": "❌ هذا البريد الإلكتروني مسجل بالفعل.",
        "reg_succ": "✅ تم إرسال طلبك للإدارة! لن تتمكن من الدخول حتى تتم الموافقة عليه.",
        "logout_btn": "🚪 تسجيل الخروج",
        "main_title": "🐄 مساعد تغذية الأبقار الحلوب",
        "main_desc": "أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.",
        "sidebar_title": "💬 سجل المحادثات",
        "admin_title": "🛠️ لوحة الإدارة",
        "no_pending": "لا توجد طلبات معلقة.",
        "approve_btn": "✅ قبول الحساب",
        "new_chat": "➕ محادثة جديدة",
        "your_chats": "📚 محادثاتك:",
        "chat_prefix": "المحادثة",
        "loading": "جاري مسح قواعد البيانات العلمية وتحليل المعطيات...",
        "ai_err": "عذراً، لم نتمكن من معالجة الإجابة حالياً.",
        "api_err": "لا توجد نماذج ذكاء اصطناعي متاحة.",
        "api_missing": "⚠️ لم يتم العثور على مفاتيح API.",
        "sys_err": "حدث خطأ أثناء المعالجة:",
        "sugg_1_btn": "كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟",
        "sugg_1_q": "كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟",
        "sugg_2_btn": "🌾 حلل مكون علف",
        "sugg_2_q": "ما هي طرق تحليل مكونات الأعلاف والتحقق من جودة العناصر الغذائية للأبقار؟",
        "sugg_3_btn": "📄 حلل نظامي الغذائي",
        "sugg_3_q": "ما هي أسس تحليل وتطوير النظم الغذائية للأبقار الحلوب؟",
        "sugg_4_btn": "🖼️ تحديد درجة (BCS)",
        "sugg_4_q": "اشرح كيفية تحديد درجة حالة الجسم (BCS) للأبقار الحلوب وأهميتها.",
        "sugg_5_btn": "💩 تحليل درجة الروث",
        "sugg_5_q": "كيف يمكن تقييم وتحليل درجات روث الأبقار لضبط التغذية؟",
        "upload_lbl": "📷 إرفاق صورة للتحليل (اختياري)",
        "upload_succ": "✅ تم إرفاق الصورة. اكتب سؤالك.",
        "chat_input": "اسأل عن الحميات، المكونات، أو ارفع صورة...",
        "img_caption": "الصورة المرفقة",
        "lang_rule": "7. تطابق اللغة (Language Matching): يجب أن ترد على المستخدم بنفس لغة سؤاله تماماً."
    },
    "en": {
        "auth_title": "🔐 Authentication Portal",
        "auth_sub": "Welcome to the Smart Dairy Cattle Management System",
        "tab_login": "Login",
        "tab_register": "Request Account",
        "name_label": "👤 Full Name",
        "email_label": "📧 Email",
        "pass_label": "🔑 Password",
        "pass_confirm_label": "🔑 Confirm Password",
        "login_btn": "Login",
        "register_btn": "Request Account",
        "login_err": "❌ Invalid email or password.",
        "pending_err": "⏳ Your account is pending admin approval.",
        "reg_err_pass": "❌ Passwords do not match.",
        "reg_err_exists": "❌ Email is already registered.",
        "reg_succ": "✅ Request sent to Admin! You can login once approved.",
        "logout_btn": "🚪 Logout",
        "main_title": "🐄 Dairy Cattle Nutrition Assistant",
        "main_desc": "I am your AI assistant specialized exclusively in academic research for dairy cattle nutrition.",
        "sidebar_title": "💬 Chat History",
        "admin_title": "🛠️ Admin Panel",
        "no_pending": "No pending requests.",
        "approve_btn": "✅ Approve Account",
        "new_chat": "➕ New Chat",
        "your_chats": "📚 Your Chats:",
        "chat_prefix": "Chat",
        "loading": "Analyzing data...",
        "ai_err": "Sorry, couldn't process the answer.",
        "api_err": "No AI models available.",
        "api_missing": "⚠️ API keys not found.",
        "sys_err": "Error:",
        "sugg_1_btn": "Diet for high-yielding cows?",
        "sugg_1_q": "How do I formulate a diet for high-yielding dairy cows?",
        "sugg_2_btn": "🌾 Analyze feed components",
        "sugg_2_q": "What are the methods for analyzing feed components for dairy cows?",
        "sugg_3_btn": "📄 Analyze diet plan",
        "sugg_3_q": "What are the principles of developing dairy cattle diets?",
        "sugg_4_btn": "🖼️ Determine BCS",
        "sugg_4_q": "Explain how to determine Body Condition Score (BCS) for dairy cows.",
        "sugg_5_btn": "💩 Analyze manure score",
        "sugg_5_q": "How to evaluate dairy cow manure scores?",
        "upload_lbl": "📷 Attach Image (Optional)",
        "upload_succ": "✅ Image attached. Type your question.",
        "chat_input": "Ask about diets, ingredients...",
        "img_caption": "Attached Image",
        "lang_rule": "7. Language Matching: You MUST respond in the exact same language as the user's query."
    }
}

t = ui[st.session_state.lang]

# --- زر تبديل اللغة ---
with st.sidebar:
    lang_button_label = "🌐 Switch to English" if st.session_state.lang == "ar" else "🌐 التبديل للعربية"
    if st.button(lang_button_label, use_container_width=True):
        st.session_state.lang = "en" if st.session_state.lang == "ar" else "ar"
        st.rerun()
    st.write("---")

# ==========================================
# --- نظام قواعد البيانات المحلية (Users & Chats) ---
# ==========================================
USERS_FILE = "users_db.json"
CHATS_FILE = "chats_history.json"

# إيميل وباسورد الإدارة الأساسي
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cow.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")

# دالة تشفير كلمة المرور
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users_dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, ensure_ascii=False, indent=4)

def load_all_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all_chats(all_chats_dict):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chats_dict, f, ensure_ascii=False, indent=4)

# ==========================================
# --- نظام تسجيل الدخول وإنشاء الحساب ---
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_name = ""
    st.session_state.is_admin = False

if not st.session_state.logged_in:
    st.markdown(f"<h1 style='text-align: center;'>{t['auth_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>{t['auth_sub']}</p>", unsafe_allow_html=True)
    
    users_db = load_users()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs([t['tab_login'], t['tab_register']])
        
        # تبويب تسجيل الدخول
        with tab1:
            with st.form("login_form"):
                log_email = st.text_input(t['email_label'])
                log_pass = st.text_input(t['pass_label'], type="password")
                btn_login = st.form_submit_button(t['login_btn'], use_container_width=True)
                
                if btn_login:
                    hashed_pass = hash_password(log_pass)
                    
                    # التحقق إذا كان المدير (Admin)
                    if log_email == ADMIN_EMAIL and log_pass == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.user_email = log_email
                        st.session_state.user_name = "المدير (Admin)"
                        st.session_state.is_admin = True
                        st.rerun()
                        
                    # التحقق من المستخدمين العاديين
                    elif log_email in users_db and users_db[log_email]["password"] == hashed_pass:
                        # التأكد من حالة الحساب (هل تم قبوله؟)
                        if users_db[log_email].get("status") == "approved":
                            st.session_state.logged_in = True
                            st.session_state.user_email = log_email
                            st.session_state.user_name = users_db[log_email]["name"]
                            st.session_state.is_admin = False
                            st.rerun()
                        else:
                            st.warning(t['pending_err']) # رسالة أن الحساب قيد المراجعة
                    else:
                        st.error(t['login_err'])
                        
        # تبويب إنشاء حساب جديد
        with tab2:
            with st.form("register_form"):
                reg_name = st.text_input(t['name_label'])
                reg_email = st.text_input(t['email_label'])
                reg_pass = st.text_input(t['pass_label'], type="password")
                reg_pass_conf = st.text_input(t['pass_confirm_label'], type="password")
                btn_register = st.form_submit_button(t['register_btn'], use_container_width=True)
                
                if btn_register:
                    if reg_pass != reg_pass_conf:
                        st.error(t['reg_err_pass'])
                    elif reg_email in users_db or reg_email == ADMIN_EMAIL:
                        st.error(t['reg_err_exists'])
                    elif reg_email and reg_pass and reg_name:
                        # إضافة المستخدم كـ "معلق" (pending)
                        users_db[reg_email] = {
                            "name": reg_name,
                            "password": hash_password(reg_pass),
                            "status": "pending" 
                        }
                        save_users(users_db)
                        st.success(t['reg_succ'])
    st.stop()

# ==========================================
# --- الواجهة الرئيسية (بعد تسجيل الدخول) ---
# ==========================================

# --- لوحة تحكم الإدارة (تظهر فقط إذا كان الحساب هو الإدارة) ---
if st.session_state.is_admin:
    with st.sidebar:
        st.header(t['admin_title'])
        users_db = load_users()
        # جلب الحسابات المعلقة فقط
        pending_users = {email: data for email, data in users_db.items() if data.get("status") == "pending"}
        
        if pending_users:
            for p_email, p_data in pending_users.items():
                st.write(f"👤 {p_data['name']} \n({p_email})")
                if st.button(f"{t['approve_btn']}", key=f"approve_{p_email}", use_container_width=True):
                    users_db[p_email]["status"] = "approved"
                    save_users(users_db)
                    st.rerun()
                st.write("---")
        else:
            st.info(t['no_pending'])
        st.write("---")

# تحميل محادثات المستخدم الحالي فقط
all_chats_db = load_all_chats()
user_email = st.session_state.user_email

if user_email not in all_chats_db:
    all_chats_db[user_email] = {f"{t['chat_prefix']} 1": []}
    save_all_chats(all_chats_db)

user_chats = all_chats_db[user_email]

# عنوان التطبيق والترحيب بالمستخدم
st.title(t['main_title'])
st.write(f"👋 أهلاً بك، **{st.session_state.user_name}**! {t['main_desc']}")

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

# إعداد الذاكرة للمحادثة الحالية
if "current_chat" not in st.session_state or st.session_state.current_chat not in user_chats:
    st.session_state.current_chat = list(user_chats.keys())[-1] if user_chats else f"{t['chat_prefix']} 1"

if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = len(user_chats) if user_chats else 1

# إدارة المحادثات في الشريط الجانبي
with st.sidebar:
    st.header(t['sidebar_title'])
    
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.chat_counter += 1
        new_chat_name = f"{t['chat_prefix']} {st.session_state.chat_counter}"
        user_chats[new_chat_name] = []
        all_chats_db[user_email] = user_chats
        save_all_chats(all_chats_db)
        st.session_state.current_chat = new_chat_name
        st.rerun()
        
    st.write("---")
    st.write(t['your_chats'])
    
    for chat_name in list(user_chats.keys()):
        if chat_name == st.session_state.current_chat:
            st.button(f"🟢 {chat_name}", key=f"btn_{chat_name}", disabled=True, use_container_width=True)
        else:
            if st.button(f"⚪ {chat_name}", key=f"btn_{chat_name}", use_container_width=True):
                st.session_state.current_chat = chat_name
                st.rerun()

current_messages = user_chats[st.session_state.current_chat]

for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

# دالة المعالجة الأساسية
def process_query(query, img=None):
    user_chats[st.session_state.current_chat].append({"role": "user", "content": query, "image": img})
    all_chats_db[user_email] = user_chats
    save_all_chats(all_chats_db)
    
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
                        user_chats[st.session_state.current_chat].append({"role": "assistant", "content": answer.text})
                        all_chats_db[user_email] = user_chats
                        save_all_chats(all_chats_db)
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
