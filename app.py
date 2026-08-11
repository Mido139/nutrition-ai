import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
import json
from PIL import Image  # مكتبة معالجة الصور

# إعداد واجهة الموقع
st.set_page_config(page_title="مساعد تغذية الأبقار الحلوب", page_icon="🐄", layout="centered")

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

# --- نظام تسجيل الدخول ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 تسجيل الدخول</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>مرحباً بك في النظام الذكي لإدارة الأبقار الحلوب</p>", unsafe_allow_html=True)
    
    CORRECT_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cow.com")
    CORRECT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("📧 البريد الإلكتروني")
            password = st.text_input("🔑 كلمة المرور", type="password")
            submit_button = st.form_submit_button("تسجيل الدخول", use_container_width=True)

            if submit_button:
                if email == CORRECT_EMAIL and password == CORRECT_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ البريد الإلكتروني أو كلمة المرور غير صحيحة.")
    st.stop()

# ==========================================
# --- الواجهة الرئيسية للموقع ---
# ==========================================

# --- دوال حفظ واسترجاع المحادثات محلياً (JSON) ---
HISTORY_FILE = "chats_history.json"

def load_chats():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"المحادثة 1": []}

def save_chats(chats_dict):
    chats_to_save = {}
    for chat_name, msgs in chats_dict.items():
        clean_msgs = []
        for msg in msgs:
            # نستثني كائن الصورة لأنه لا يمكن حفظه كنص في JSON
            clean_msgs.append({"role": msg.get("role"), "content": msg.get("content")})
        chats_to_save[chat_name] = clean_msgs
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chats_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving chats: {e}")

# عنوان التطبيق
st.title("🐄 مساعد تغذية الأبقار الحلوب")
st.write("مرحباً بك! أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.")

# زر لتسجيل الخروج في الأعلى
with st.sidebar:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.write("---")

# --- جزء سحب المفاتيح ---
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error("⚠️ لم يتم العثور على مفاتيح API. يرجى التأكد من إضافتها.")
    st.stop()

# --- إعداد الذاكرة من الملف المحلي ---
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
if "current_chat" not in st.session_state:
    # فتح آخر محادثة مسجلة أو المحادثة 1
    st.session_state.current_chat = list(st.session_state.chats.keys())[-1] if st.session_state.chats else "المحادثة 1"
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = len(st.session_state.chats) if st.session_state.chats else 1

# --- الشريط الجانبي (Sidebar) لإدارة المحادثات ---
with st.sidebar:
    st.header("💬 سجل المحادثات")
    
    # زر محادثة جديدة
    if st.button("➕ محادثة جديدة", use_container_width=True):
        st.session_state.chat_counter += 1
        new_chat_name = f"المحادثة {st.session_state.chat_counter}"
        st.session_state.chats[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        save_chats(st.session_state.chats) # حفظ التحديث فوراً
        st.rerun()
        
    st.write("---")
    st.write("📚 محادثاتك:")
    
    # قائمة الأزرار للمحادثات السابقة
    for chat_name in list(st.session_state.chats.keys()):
        if chat_name == st.session_state.current_chat:
            st.button(f"🟢 {chat_name}", key=f"btn_{chat_name}", disabled=True, use_container_width=True)
        else:
            if st.button(f"⚪ {chat_name}", key=f"btn_{chat_name}", use_container_width=True):
                st.session_state.current_chat = chat_name
                st.rerun()

# جلب رسائل المحادثة الحالية لعرضها
current_messages = st.session_state.chats[st.session_state.current_chat]

# عرض الرسائل
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

# دالة المعالجة الأساسية
def process_query(query, img=None):
    # إضافة الرسالة وحفظها فوراً
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": query, "image": img})
    save_chats(st.session_state.chats)
    
    with st.chat_message("user"):
        st.markdown(query)
        if img:
            st.image(img, caption="الصورة المرفقة", use_container_width=True)

    with st.chat_message("assistant"):
        with st.spinner("جاري مسح قواعد البيانات العلمية وتحليل المعطيات..."):
            try:
                scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية OR journal OR pubmed OR sciencedirect OR ncbi)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=8)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"مرجع رقم [{index + 1}]:\n- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار متخصص *حصرياً* في تغذية، فسيولوجيا هضم، وإدارة الأبقار الحلوب (Dairy Cattle) فقط.
                    مهمتك هي تقديم إجابات علمية وبيولوجية دقيقة وشاملة من خلال الدمج بين مصدرين أساسيين:
                    أولاً: المرجع الأكاديمي الأساسي الدائم (Nutrient Requirements of Dairy Cattle - NASEM): https://www.ncbi.nlm.nih.gov/books/NBK600603/
                    ثانياً: "مجموعة الأبحاث والمصادر العلمية المتاحة من البحث الحي" المرفقة أدناه.
                    
                    التزم بالقوانين التالية بصرامة شديدة:
                    1. التخصص الحصري (أهم قانون): يُحظر عليك تماماً الإجابة على أي أسئلة تتعلق بحيوانات أخرى (مثل الأغنام، الماعز، عجول التسمين غير الحلوب، الدواجن، الخيول) أو أي مواضيع خارج نطاق الأبقار الحلوب. إذا كان السؤال لا يخص الأبقار الحلوب، اعتذر بلباقة.
                    2. تحليل الصور: إذا أرفق المستخدم صورة، قم بفحصها بعناية شديدة وقدم تقييماً علمياً دقيقاً بناءً على قواعد الأبقار الحلوب.
                    3. الشمول والدقة: اجمع المعلومات من المرجع الثابت ومن الأبحاث الحية لتقديم إجابة متكاملة تخص الأبقار الحلوب.
                    4. التوثيق الأكاديمي: يجب توثيق كل معلومة داخل النص [NASEM] أو [1].
                    5. منع التأليف نهائياً: إذا لم تجد إجابة علمية دقيقة، قل بوضوح: "لا توفر المراجع الحالية بيانات علمية دقيقة للإجابة على هذا السؤال".
                    6. قسم المراجع: في نهاية الإجابة، قم بعمل قسم "المراجع العلمية" واذكر فيها الروابط المعتمدة.
                    
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
                        # إضافة الرد وحفظه فوراً
                        st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": answer.text})
                        save_chats(st.session_state.chats)
                    else:
                        st.error("عذراً، لم نتمكن من معالجة الإجابة حالياً عبر النماذج المتاحة.")
                else:
                    st.error("لا توجد نماذج ذكاء اصطناعي متاحة في مفتاحك.")
                    
            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")

# أزرار الاقتراحات السريعة
if len(current_messages) == 0:
    st.write("") 
    col1, col2 = st.columns(2)
    
    with col2:
        if st.button("كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟"):
            process_query("كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟")
        if st.button("🌾 حلل مكون علف وتحقق من جودة العناصر الغذائية"):
            process_query("ما هي طرق تحليل مكونات الأعلاف والتحقق من جودة العناصر الغذائية للأبقار؟")
            
    with col1:
        if st.button("📄 حلل ملف نظامي الغذائي واقترح تحسينات"):
            process_query("ما هي أسس تحليل وتطوير النظم الغذائية للأبقار الحلوب؟")
        if st.button("🖼️ حلل صورة بقرة لتحديد درجة حالة الجسم (BCS)"):
            process_query("اشرح كيفية تحديد درجة حالة الجسم (BCS) للأبقار الحلوب وأهميتها.")

    col3, col4, col5 = st.columns([1, 2, 1])
    with col4:
        if st.button("💩 حلل صورة الروث لتحديد درجة الروث"):
            process_query("كيف يمكن تقييم وتحليل درجات روث الأبقار لضبط التغذية؟")

# --- منطقة الإدخال السفلية ---
st.write("---")
uploaded_file = st.file_uploader("📷 إرفاق صورة للتحليل (اختياري)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img_to_analyze = Image.open(uploaded_file)
    st.success("✅ تم إرفاق الصورة. اكتب سؤالك في الشريط بالأسفل واضغط Enter.")
else:
    img_to_analyze = None

user_input = st.chat_input("اسأل عن الحميات، المكونات، أو ارفع صورة واسأل عنها...")
if user_input:
    process_query(user_input, img=img_to_analyze)
