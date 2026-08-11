import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os
from PIL import Image  # مكتبة معالجة الصور

# إعداد واجهة الموقع
st.set_page_config(page_title="مساعد تغذية الأبقار الحلوب", page_icon="🐄", layout="centered")

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
    /* تنسيق لتقليل المسافة بين زر رفع الصورة وشريط الكتابة */
    .stFileUploader {
        padding-bottom: 0rem;
        margin-bottom: -1rem;
    }
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.title("🐄 مساعد تغذية الأبقار الحلوب")
st.write("مرحباً بك! أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.")

# --- جزء سحب المفاتيح ---
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
        # عرض الصورة في المحادثة إذا كانت موجودة (تم التحديث هنا)
        if "image" in message and message["image"] is not None:
            st.image(message["image"], use_container_width=True)

# دالة المعالجة الأساسية
def process_query(query, img=None):
    # حفظ الرسالة والصورة في الذاكرة
    st.session_state.messages.append({"role": "user", "content": query, "image": img})
    
    with st.chat_message("user"):
        st.markdown(query)
        # تم التحديث هنا أيضاً
        if img:
            st.image(img, caption="الصورة المرفقة", use_container_width=True)

    with st.chat_message("assistant"):
        with st.spinner("جاري مسح قواعد البيانات العلمية وتحليل المعطيات..."):
            try:
                # 1. تخصيص محرك البحث
                scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية OR journal OR pubmed OR sciencedirect OR ncbi)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=8)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"مرجع رقم [{index + 1}]:\n- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                # 2. إعداد Gemini بقوانين صارمة للحصر في الأبقار الحلوب فقط
                genai.configure(api_key=gemini_api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار متخصص *حصرياً* في تغذية، فسيولوجيا هضم، وإدارة الأبقار الحلوب (Dairy Cattle) فقط.
                    مهمتك هي تقديم إجابات علمية وبيولوجية دقيقة وشاملة من خلال الدمج بين مصدرين أساسيين:
                    أولاً: المرجع الأكاديمي الأساسي الدائم (Nutrient Requirements of Dairy Cattle - NASEM): https://www.ncbi.nlm.nih.gov/books/NBK600603/
                    ثانياً: "مجموعة الأبحاث والمصادر العلمية المتاحة من البحث الحي" المرفقة أدناه.
                    
                    التزم بالقوانين التالية بصرامة شديدة:
                    1. التخصص الحصري (أهم قانون): يُحظر عليك تماماً الإجابة على أي أسئلة تتعلق بحيوانات أخرى (مثل الأغنام، الماعز، عجول التسمين غير الحلوب، الدواجن، الخيول) أو أي مواضيع خارج نطاق الأبقار الحلوب. إذا كان السؤال لا يخص الأبقار الحلوب، اعتذر بلباقة وقل بوضوح: "عذراً، تخصصي يقتصر حصرياً على تغذية وإدارة الأبقار الحلوب، ولا يمكنني تقديم معلومات حول هذا الموضوع."
                    2. تحليل الصور: إذا أرفق المستخدم صورة، قم بفحصها بعناية شديدة (مثلاً: حدد درجة حالة الجسم BCS بناءً على الزوايا والعظام الظاهرة، أو قيم درجة الروث، أو جودة العلف) وقدم تقييماً علمياً دقيقاً بناءً على قواعد الأبقار الحلوب.
                    3. الشمول والدقة: اجمع المعلومات من المرجع الثابت ومن الأبحاث الحية لتقديم إجابة متكاملة تخص الأبقار الحلوب. اذكر الأرقام، النسب المئوية، معدلات الأيض، والبيانات الدقيقة.
                    4. التوثيق الأكاديمي: يجب توثيق كل معلومة داخل النص. إذا استخدمت معلومات من مرجع NASEM استخدم الرمز [NASEM]، وإذا استخدمت معلومات من الأبحاث المرفقة استخدم رقم المرجع مثل [1] أو [2].
                    5. منع التأليف نهائياً: إذا لم تجد إجابة علمية دقيقة، قل بوضوح: "لا توفر المراجع الحالية بيانات علمية دقيقة للإجابة على هذا السؤال".
                    6. قسم المراجع: في نهاية الإجابة، قم بعمل قسم "المراجع العلمية" واذكر فيها روابط الأبحاث التي اعتمدت عليها فعلياً، بالإضافة إلى رابط NASEM الثابت إذا تم استخدامه.
                    
                    سؤال المستخدم: {query}
                    
                    الأبحاث والمصادر العلمية المتاحة من البحث الحي:
                    {context}
                    """
                    
                    # دمج النص مع الصورة (إذا وجدت) لإرسالها للنموذج
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

# --- منطقة الإدخال السفلية (الصورة + النص) ---
st.write("---") # فاصل مرئي بسيط
uploaded_file = st.file_uploader("📷 إرفاق صورة للتحليل (اختياري)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img_to_analyze = Image.open(uploaded_file)
    st.success("✅ تم إرفاق الصورة. اكتب سؤالك في الشريط بالأسفل واضغط Enter.")
else:
    img_to_analyze = None

user_input = st.chat_input("اسأل عن الحميات، المكونات، أو ارفع صورة واسأل عنها...")
if user_input:
    process_query(user_input, img=img_to_analyze)
