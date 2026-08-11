import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os

# إعداد واجهة الموقع
st.set_page_config(page_title="مساعد التغذية الذكي", page_icon="🐄", layout="centered")

# --- تنسيق CSS مخصص لجعل الأزرار بيضاوية ---
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
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.title("🐄 مساعد التغذية الذكي")
st.write("مرحباً بك! أنا مساعدك الذكي المتخصص في تغذية الحيوان وإدارة المزارع.")

# --- جزء سحب المفاتيح (متوافق مع الاستضافة السحابية والاستخدام المحلي) ---
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error("⚠️ لم يتم العثور على مفاتيح API. يرجى التأكد من إضافتها في إعدادات الاستضافة أو ملف الأسرار.")
    st.stop()

# إعداد الذاكرة المؤقتة (Session State) لحفظ المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة في المحادثة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# دالة المعالجة الأساسية
def process_query(query):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("جاري البحث في المصادر العلمية..."):
            try:
                # 1. البحث في Tavily
                tavily_client = TavilyClient(api_key=tavily_api_key)
                search_response = tavily_client.search(query, search_depth="advanced", max_results=3)
                
                context = ""
                for result in search_response.get("results", []):
                    context += f"- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                # 2. إعداد Gemini
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت خبير واستشاري متخصص في تغذية الحيوان، وتحديداً الأبقار الحلوب وإدارة المزارع.
                    أجب على سؤال المستخدم بناءً على "نتائج البحث" المرفقة فقط.
                    قدم إجابة علمية، دقيقة، ومنظمة.
                    يجب إدراج المراجع المستخدمة كروابط في النهاية.
                    
                    السؤال: {query}
                    
                    المصادر المتاحة:
                    {context}
                    """
                    
                    answer = None
                    for model_name in available_models:
                        try:
                            model = genai.GenerativeModel(model_name)
                            answer = model.generate_content(prompt)
                            break
                        except Exception:
                            continue
                    
                    if answer:
                        st.markdown(answer.text)
                        st.session_state.messages.append({"role": "assistant", "content": answer.text})
                    else:
                        st.error("جميع نماذج الذكاء الاصطناعي مغلقة حالياً.")
                else:
                    st.error("لا توجد نماذج متاحة.")
                    
            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")

# أزرار الاقتراحات السريعة
if len(st.session_state.messages) == 0:
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

# شريط الإدخال السفلي
user_input = st.chat_input("اسأل عن الحميات، المكونات ــــ أو الصق حصة لتحليلها.")
if user_input:
    process_query(user_input)