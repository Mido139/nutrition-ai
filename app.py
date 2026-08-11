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
st.write("مرحباً بك! أنا مساعدك الذكي المتخصص في الأبحاث الأكاديمية لتغذية الحيوان وإدارة المزارع.")

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
        with st.spinner("جاري استخراج وتحليل الأبحاث من NCBI والمصادر العلمية..."):
            try:
                # 1. توجيه محرك البحث للتركيز على NCBI والمصادر الأكاديمية
                scientific_query = query + " (site:ncbi.nlm.nih.gov OR دراسة علمية OR بحث أكاديمي OR journal OR pubmed)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=5)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"مرجع رقم [{index + 1}]:\n- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                # 2. إعداد Gemini واعتماد كتاب NASEM كمرجع أساسي دائم
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار في تغذية الحيوان، وتحديداً في فسيولوجيا الهضم وإدارة الأبقار الحلوب والمجترات.
                    مهمتك هي تقديم إجابات علمية وبيولوجية دقيقة بناءً على مصدرين أساسيين:
                    أولاً: المرجع الأكاديمي الأساسي الدائم (Nutrient Requirements of Dairy Cattle - NASEM): https://www.ncbi.nlm.nih.gov/books/NBK600603/
                    ثانياً: "المراجع المتاحة من البحث الحي" المرفقة أدناه.
                    
                    التزم بالقوانين التالية بصرامة شديدة:
                    1. الدقة العلمية: تجنب النصائح السطحية والعامة. اذكر الأرقام، النسب المئوية، معدلات الأيض، والبيانات الدقيقة.
                    2. التوثيق الأكاديمي: يجب توثيق كل معلومة داخل النص. إذا استخدمت معلومات من المرجع الأساسي استخدم الرمز [NASEM]، وإذا استخدمت معلومات من البحث الحي استخدم رقم المرجع مثل [1].
                    3. منع التأليف نهائياً: إذا كانت المصادر المتاحة والمرجع الأساسي لا تحتوي على بيانات علمية كافية، قل بوضوح: "لا توفر المراجع الحالية بيانات علمية دقيقة للإجابة على هذا السؤال".
                    4. المراجع: في نهاية الإجابة، قم بعمل قسم "المراجع العلمية" واذكر فيها الروابط التي تم الاستناد إليها فعلياً (بما في ذلك رابط NASEM إذا تم استخدامه في الإجابة).
                    
                    سؤال المستخدم: {query}
                    
                    المراجع المتاحة من البحث الحي:
                    {context}
                    """
                    
                    answer = None
                    preferred_models = ["models/gemini-1.5-pro-latest", "models/gemini-pro"]
                    models_to_try = preferred_models + [m for m in available_models if m not in preferred_models]

                    for model_name in models_to_try:
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
                        st.error("عذراً، لم نتمكن من معالجة الإجابة حالياً عبر النماذج المتاحة.")
                else:
                    st.error("لا توجد نماذج ذكاء اصطناعي متاحة في مفتاحك.")
                    
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
