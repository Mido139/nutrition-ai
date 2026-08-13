import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
import hashlib
import datetime
from PIL import Image
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# ==========================================
# --- إعداد واجهة الموقع ---
# ==========================================
st.set_page_config(page_title="Dairy Cattle AI | مساعد تغذية الأبقار", page_icon="🐄", layout="centered")

st.markdown('''
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
    hr {
        margin: 0.5em 0;
    }
</style>
''', unsafe_allow_html=True)

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
        "suspended_err": "🚫 حسابك موقوف حالياً من قبل الإدارة.",
        "reg_err_pass": "❌ كلمتا المرور غير متطابقتين.",
        "reg_err_exists": "❌ هذا البريد الإلكتروني مسجل بالفعل.",
        "reg_succ": "✅ تم إرسال طلبك للإدارة! لن تتمكن من الدخول حتى تتم الموافقة عليه.",
        "logout_btn": "🚪 تسجيل الخروج",
        "main_title": "🐄 مساعد تغذية الأبقار الحلوب",
        "main_desc": "أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.",
        "sidebar_title": "💬 سجل المحادثات",
        "admin_title": "🛠️ إدارة الحسابات",
        "admin_pending": "⏳ بانتظار الموافقة",
        "admin_approved": "🟢 الحسابات النشطة",
        "admin_suspended": "🔴 الحسابات الموقوفة",
        "no_users": "لا يوجد حسابات هنا.",
        "approve_btn": "✅ قبول",
        "suspend_btn": "⛔ إيقاف",
        "reactivate_btn": "✅ تفعيل",
        "delete_btn": "🗑️ حذف",
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
        "lang_rule": "7. تطابق اللغة (Language Matching): يجب أن ترد على المستخدم بنفس لغة سؤاله تماماً.",
        "delete_title": "إدارة المحادثات",
        "delete_current_chat": "🗑️ مسح هذه المحادثة",
        "delete_all_chats": "🗑️ مسح كل المحادثات"
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
        "suspended_err": "🚫 Your account is currently suspended by the Admin.",
        "reg_err_pass": "❌ Passwords do not match.",
        "reg_err_exists": "❌ Email is already registered.",
        "reg_succ": "✅ Request sent to Admin! You can login once approved.",
        "logout_btn": "🚪 Logout",
        "main_title": "🐄 Dairy Cattle Nutrition Assistant",
        "main_desc": "I am your AI assistant specialized exclusively in academic research for dairy cattle nutrition.",
        "sidebar_title": "💬 Chat History",
        "admin_title": "🛠️ Account Management",
        "admin_pending": "⏳ Pending Approval",
        "admin_approved": "🟢 Active Accounts",
        "admin_suspended": "🔴 Suspended Accounts",
        "no_users": "No accounts here.",
        "approve_btn": "✅ Approve",
        "suspend_btn": "⛔ Suspend",
        "reactivate_btn": "✅ Reactivate",
        "delete_btn": "🗑️ Delete",
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
        "lang_rule": "7. Language Matching: You MUST respond in the exact same language as the user's query.",
        "delete_title": "Chat Management",
        "delete_current_chat": "🗑️ Delete This Chat",
        "delete_all_chats": "🗑️ Delete All Chats"
    }
}

t = ui[st.session_state.lang]

with st.sidebar:
    lang_button_label = "🌐 Switch to English" if st.session_state.lang == "ar" else "🌐 التبديل للعربية"
    if st.button(lang_button_label, use_container_width=True):
        st.session_state.lang = "en" if st.session_state.lang == "ar" else "ar"
        st.rerun()
    st.write("---")

# ==========================================
# --- الاتصال بقاعدة بيانات TiDB Serverless (SQL) ---
# ==========================================
TIDB_URI = os.environ.get("TIDB_URI") or st.secrets.get("TIDB_URI", "")

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    email = Column(String(255), primary_key=True)
    name = Column(String(255))
    password = Column(String(255))
    status = Column(String(50))

class UserChats(Base):
    __tablename__ = 'user_chats'
    email = Column(String(255), primary_key=True)
    chats = Column(JSON, default=dict)

@st.cache_resource
def get_sessionmaker():
    if not TIDB_URI:
        return None
    try:
        engine = create_engine(TIDB_URI, pool_recycle=3600, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال بقاعدة البيانات: {e}")
        return None

Session = get_sessionmaker()

if not Session:
    st.error("⚠️ يرجى التأكد من إضافة رابط TIDB_URI في إعدادات البيئة.")
    st.stop()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cow.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    with Session() as session:
        users = session.query(User).all()
        return {u.email: {"name": u.name, "password": u.password, "status": u.status} for u in users}

def save_user(email, data):
    with Session() as session:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email)
            session.add(user)
        user.name = data.get("name")
        user.password = data.get("password")
        user.status = data.get("status")
        session.commit()

def delete_user(email):
    with Session() as session:
        user = session.query(User).filter_by(email=email).first()
        if user:
            session.delete(user)
            session.commit()

def load_user_chats(email):
    with Session() as session:
        uc = session.query(UserChats).filter_by(email=email).first()
        if uc and uc.chats:
            raw_chats = dict(uc.chats)
            processed_chats = {}
            changed = False
            now = datetime.datetime.now()
            
            for c_name, c_data in raw_chats.items():
                if isinstance(c_data, list):
                    processed_chats[c_name] = {"updated_at": now.isoformat(), "messages": c_data}
                    changed = True
                elif isinstance(c_data, dict):
                    updated_at_str = c_data.get("updated_at", now.isoformat())
                    try:
                        updated_at = datetime.datetime.fromisoformat(updated_at_str)
                    except ValueError:
                        updated_at = now
                    
                    if (now - updated_at).days > 30:
                        changed = True
                    else:
                        processed_chats[c_name] = c_data
            
            if changed:
                uc.chats = processed_chats
                session.commit()
            return processed_chats
        return {}

def save_user_chats(email, chats_dict):
    with Session() as session:
        uc = session.query(UserChats).filter_by(email=email).first()
        if not uc:
            uc = UserChats(email=email, chats=chats_dict)
            session.add(uc)
        else:
            uc.chats = dict(chats_dict)
        session.commit()

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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs([t['tab_login'], t['tab_register']])
        
        with tab1:
            with st.form("login_form"):
                log_email = st.text_input(t['email_label'])
                log_pass = st.text_input(t['pass_label'], type="password")
                btn_login = st.form_submit_button(t['login_btn'], use_container_width=True)
                
                if btn_login:
                    hashed_pass = hash_password(log_pass)
                    
                    if log_email == ADMIN_EMAIL and log_pass == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.user_email = log_email
                        st.session_state.user_name = "المدير (Admin)"
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        users_db = load_users()
                        if log_email in users_db and users_db[log_email]["password"] == hashed_pass:
                            user_status = users_db[log_email].get("status")
                            if user_status == "approved":
                                st.session_state.logged_in = True
                                st.session_state.user_email = log_email
                                st.session_state.user_name = users_db[log_email]["name"]
                                st.session_state.is_admin = False
                                st.rerun()
                            elif user_status == "pending":
                                st.warning(t['pending_err'])
                            elif user_status == "suspended":
                                st.error(t['suspended_err'])
                        else:
                            st.error(t['login_err'])
                        
        with tab2:
            with st.form("register_form"):
                reg_name = st.text_input(t['name_label'])
                reg_email = st.text_input(t['email_label'])
                reg_pass = st.text_input(t['pass_label'], type="password")
                reg_pass_conf = st.text_input(t['pass_confirm_label'], type="password")
                btn_register = st.form_submit_button(t['register_btn'], use_container_width=True)
                
                if btn_register:
                    users_db = load_users()
                    if reg_pass != reg_pass_conf:
                        st.error(t['reg_err_pass'])
                    elif reg_email in users_db or reg_email == ADMIN_EMAIL:
                        st.error(t['reg_err_exists'])
                    elif reg_email and reg_pass and reg_name:
                        save_user(reg_email, {
                            "name": reg_name,
                            "password": hash_password(reg_pass),
                            "status": "pending" 
                        })
                        st.success(t['reg_succ'])
    st.stop()

# ==========================================
# --- الواجهة الرئيسية ---
# ==========================================
if st.session_state.is_admin:
    with st.sidebar:
        st.header(t['admin_title'])
        users_db = load_users()
        
        st.subheader(t['admin_pending'])
        pending_users = {e: d for e, d in users_db.items() if d.get("status") == "pending"}
        if pending_users:
            for p_email, p_data in pending_users.items():
                st.write(f"👤 {p_data['name']} \n({p_email})")
                c1, c2 = st.columns(2)
                if c1.button(t['approve_btn'], key=f"app_{p_email}", use_container_width=True):
                    p_data["status"] = "approved"
                    save_user(p_email, p_data)
                    st.rerun()
                if c2.button(t['delete_btn'], key=f"del_p_{p_email}", use_container_width=True):
                    delete_user(p_email)
                    st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info(t['no_users'])

        st.subheader(t['admin_approved'])
        approved_users = {e: d for e, d in users_db.items() if d.get("status") == "approved"}
        if approved_users:
            for a_email, a_data in approved_users.items():
                st.write(f"🟢 {a_data['name']} \n({a_email})")
                c1, c2 = st.columns(2)
                if c1.button(t['suspend_btn'], key=f"sus_{a_email}", use_container_width=True):
                    a_data["status"] = "suspended"
                    save_user(a_email, a_data)
                    st.rerun()
                if c2.button(t['delete_btn'], key=f"del_a_{a_email}", use_container_width=True):
                    delete_user(a_email)
                    st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info(t['no_users'])

        st.subheader(t['admin_suspended'])
        suspended_users = {e: d for e, d in users_db.items() if d.get("status") == "suspended"}
        if suspended_users:
            for s_email, s_data in suspended_users.items():
                st.write(f"🔴 {s_data['name']} \n({s_email})")
                c1, c2 = st.columns(2)
                if c1.button(t['reactivate_btn'], key=f"react_{s_email}", use_container_width=True):
                    s_data["status"] = "approved"
                    save_user(s_email, s_data)
                    st.rerun()
                if c2.button(t['delete_btn'], key=f"del_s_{s_email}", use_container_width=True):
                    delete_user(s_email)
                    st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info(t['no_users'])
            
        st.write("---")

user_email = st.session_state.user_email
user_chats = load_user_chats(user_email)

if not user_chats:
    now_str = datetime.datetime.now().isoformat()
    user_chats = {f"{t['chat_prefix']} 1": {"updated_at": now_str, "messages": []}}
    save_user_chats(user_email, user_chats)

st.title(t['main_title'])
st.write(f"👋 أهلاً بك، **{st.session_state.user_name}**! {t['main_desc']}")

with st.sidebar:
    if st.button(t['logout_btn'], use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.write("---")

try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error(t['api_missing'])
    st.stop()

if "current_chat" not in st.session_state or st.session_state.current_chat not in user_chats:
    st.session_state.current_chat = list(user_chats.keys())[-1] if user_chats else f"{t['chat_prefix']} 1"

if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = len(user_chats) if user_chats else 1

with st.sidebar:
    st.header(t['sidebar_title'])
    
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.chat_counter += 1
        new_chat_name = f"{t['chat_prefix']} {st.session_state.chat_counter}"
        now_str = datetime.datetime.now().isoformat()
        user_chats[new_chat_name] = {"updated_at": now_str, "messages": []}
        save_user_chats(user_email, user_chats)
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
                
    st.write("---")
    st.markdown(f"**⚙️ {t.get('delete_title', 'إدارة المحادثات')}**")
    
    if st.button(t['delete_current_chat'], use_container_width=True):
        if len(user_chats) > 1:
            del user_chats[st.session_state.current_chat]
            st.session_state.current_chat = list(user_chats.keys())[-1]
        else:
            now_str = datetime.datetime.now().isoformat()
            user_chats = {f"{t['chat_prefix']} 1": {"updated_at": now_str, "messages": []}}
            st.session_state.current_chat = f"{t['chat_prefix']} 1"
            st.session_state.chat_counter = 1
        save_user_chats(user_email, user_chats)
        st.rerun()

    if st.button(t['delete_all_chats'], use_container_width=True):
        now_str = datetime.datetime.now().isoformat()
        user_chats = {f"{t['chat_prefix']} 1": {"updated_at": now_str, "messages": []}}
        st.session_state.current_chat = f"{t['chat_prefix']} 1"
        st.session_state.chat_counter = 1
        save_user_chats(user_email, user_chats)
        st.rerun()

chat_data = user_chats[st.session_state.current_chat]
if isinstance(chat_data, list):
    current_messages = chat_data
else:
    current_messages = chat_data.get("messages", [])

for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

def process_query(query, img=None):
    now_str = datetime.datetime.now().isoformat()
    if isinstance(user_chats[st.session_state.current_chat], list):
        user_chats[st.session_state.current_chat] = {"updated_at": now_str, "messages": user_chats[st.session_state.current_chat]}
    
    user_chats[st.session_state.current_chat]["messages"].append({"role": "user", "content": query, "image": img})
    user_chats[st.session_state.current_chat]["updated_at"] = now_str
    save_user_chats(user_email, user_chats)
    
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
                    prompt = f'''
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
                    '''
                    
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
                        user_chats[st.session_state.current_chat]["messages"].append({"role": "assistant", "content": answer.text})
                        user_chats[st.session_state.current_chat]["updated_at"] = now_str
                        save_user_chats(user_email, user_chats)
                    else:
                        st.error(t['ai_err'])
                else:
                    st.error(t['api_err'])
                    
            except Exception as e:
                st.error(f"{t['sys_err']} {e}")

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
