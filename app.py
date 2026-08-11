import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
from PIL import Image

# إعداد واجهة الموقع
st.set_page_config(page_title="مساعد تغذية الأبقار الحلوب", page_icon="🐄", layout="wide")

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
    .stFileUploader { padding-bottom: 0rem; margin-bottom: -1rem; }
</style>
""", unsafe_allow_html=True)

# --- جزء سحب المفاتيح ---
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error("⚠️ لم يتم العثور على مفاتيح API. يرجى التأكد من إضافتها.")
    st.stop()

# --- إعداد الذاكرة المؤقتة للمحادثات المتعددة ---
if "chats" not in st.session_state:
    st.session_state.chats = {"محادثة 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "محادثة 1"
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 1

# --- الشريط الجانبي (Sidebar) للمحادثات القديمة ---
with st.sidebar:
    st.title("💬 سجل المحادثات")
    
    # زر محادثة جديدة
    if st.button("➕ محادثة جديدة", key="new_chat"):
        st.session_state.chat_counter += 1
        new_chat_name = f"محادثة {st.session_state.chat_counter}"
        st.session_state.chats[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        st.rerun()
        
    st.write("---")
    
    # قائمة المحادثات القديمة
    st.write("📚 محادثاتك:")
    for chat_name in list(st.session_state.chats.keys()):
        # إذا كانت المحادثة هي المفتوحة حالياً، نميزها
        if chat_name == st.session_state.current_chat:
            st.button(f"🟢 {chat_name}", key=f"btn_{chat_name}", disabled=True)
        else:
            if st.button(f"⚪ {chat_name}", key=f"btn_{chat_name}"):
                st.session_state.current_chat = chat_name
                st.rerun()

# --- الواجهة الرئيسية ---
st.title("🐄 مساعد تغذية الأبقار الحلوب")
st.write(f"مرحباً بك! أنت الآن في: **{st.session_state.current_chat}**")

# جلب رسائل المحادثة الحالية
current_messages = st.session_state.chats[st.session_state.current_chat]

# عرض الرسائل السابقة في المحادثة الحالية
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

# دالة المعالجة الأساسية
def process_query(query, img=None):
    # إضافة الرسالة للمحادثة الحالية
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": query, "image": img})
    
    with st.chat_message("user"):
        st.markdown(query)
        if img:
            st.image(img, caption="الصورة المرفقة", use_container_width=True)

    with st.chat_message("assistant"):
        with st.spinner("جاري مسح قواعد البيانات العلمية..."):
            try:
                scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية OR journal OR pubmed OR sciencedirect OR ncbi)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=5)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"مرجع رقم [{index + 1}]:\n- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار متخصص *حصرياً* في الأبقار الحلوب (Dairy Cattle).
                    المرجع الأساسي: https://www.ncbi.nlm.nih.gov/books/NBK600603/
                    قوانين:
                    1. يُحظر الإجابة عن حيوانات أخرى.
                    2. حلل الصور المرفقة بدقة وفقاً للأبقار الحلوب.
                    3. وثق كل معلومة برقم المرجع [1] أو [NASEM].
                    
                    سؤال المستخدم: {query}
                    المراجع الحية: {context}
                    """
                    contents_to_send = [prompt]
                    if img:
                        contents_to_send.append(img)
                        
                    answer = None
                    for model_name in ["models/gemini-1.5-pro-latest", "models/gemini-pro"] + available_models:
                        try:
                            model = genai.GenerativeModel(model_name)
                            answer = model.generate_content(contents_to_send)
                            break
                        except: continue
                    
                    if answer:
                        st.markdown(answer.text)
                        # حفظ الإجابة في المحادثة الحالية
                        st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": answer.text})
                    else:
                        st.error("لم نتمكن من معالجة الإجابة.")
                else:
                    st.error("لا توجد نماذج متاحة.")
            except Exception as e:
                st.error(f"حدث خطأ: {e}")

# أزرار الاقتراحات السريعة (تظهر فقط إذا كانت المحادثة الحالية فارغة)
if len(current_messages) == 0:
    st.write("") 
    col1, col2 = st.columns(2)
    with col2:
        if st.button("كيف أضع نظاماً غذائياً للأبقار الحلوب؟"):
            process_query("كيف أضع نظاماً غذائياً للأبقار الحلوب عالية الإنتاج؟")
    with col1:
        if st.button("🖼️ حلل صورة بقرة لتحديد BCS"):
            process_query("اشرح كيفية تحديد درجة حالة الجسم (BCS) للأبقار الحلوب وأهميتها.")

# --- منطقة الإدخال السفلية ---
st.write("---")
uploaded_file = st.file_uploader("📷 إرفاق صورة للتحليل (اختياري)", type=["jpg", "jpeg", "png"])
img_to_analyze = Image.open(uploaded_file) if uploaded_file else None

user_input = st.chat_input("اسأل عن الحميات، المكونات، أو ارفع صورة واسأل عنها...")
if user_input:
    process_query(user_input, img=img_to_analyze)
