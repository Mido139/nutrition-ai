import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import os

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
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.title("🐄 مساعد تغذية الأبقار الحلوب")
st.write("مرحباً بك! أنا مساعدك الذكي المتخصص حصرياً في الأبحاث الأكاديمية لتغذية وإدارة الأبقار الحلوب.")

# --- جزء سحب المفاتيح (متوافق مع الاستضافة السحابية والاستخدام المحلي) ---
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or st.secrets["TAVILY_API_KEY"]
except Exception:
    st.error("⚠️ لم يتم العثور على مفاتيح API. يرجى التأكد من إضافتها في إعدادات الاستضافة أو ملف الأسرار.")
    st.stop()

# إعداد مفتاح جوجل بشكل عام لكي نتمكن من رفع الملفات
genai.configure(api_key=gemini_api_key)

# --- دالة رفع الكتاب للذاكرة (تعمل مرة واحدة فقط لتسريع الموقع) ---
@st.cache_resource(show_spinner=False)
def load_nasem_book():
    book_path = "nasem.pdf"
    if os.path.exists(book_path):
        try:
            # يتم رفع الكتاب لخوادم Gemini لمعالجته
            uploaded_file = genai.upload_file(book_path, display_name="NASEM Dairy Cattle Book")
            return uploaded_file
        except Exception as e:
            st.error(f"⚠️ حدث خطأ أثناء قراءة ملف PDF: {e}")
            return None
    return None

with st.spinner("جاري تهيئة النظام وقراءة كتاب NASEM الأساسي..."):
    nasem_file = load_nasem_book()

if nasem_file:
    st.success("✅ تم تحميل وقراءة كتاب NASEM الأساسي بنجاح، النظام جاهز للتحليل الدقيق!")
else:
    st.warning("⚠️ لم يتم العثور على ملف 'nasem.pdf' في مجلد المشروع. سيتم الاعتماد على البحث الحي في الإنترنت فقط.")

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
        with st.spinner("جاري تحليل الكتاب ومسح قواعد البيانات العلمية..."):
            try:
                # 1. تخصيص محرك البحث ليجلب الأبحاث الخاصة بالأبقار الحلوب فقط
                scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية OR journal OR pubmed OR sciencedirect OR ncbi)"
                tavily_client = TavilyClient(api_key=tavily_api_key)
                
                search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=8)
                
                context = ""
                for index, result in enumerate(search_response.get("results", [])):
                    context += f"مرجع رقم [{index + 1}]:\n- العنوان: {result['title']}\n- الرابط: {result['url']}\n- المعلومات: {result['content']}\n\n"
                
                # 2. إعداد Gemini بقوانين صارمة للحصر في الأبقار الحلوب فقط
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
                
                if available_models:
                    prompt = f"""
                    أنت باحث أكاديمي خبير ومستشار متخصص *حصرياً* في تغذية، فسيولوجيا هضم، وإدارة الأبقار الحلوب (Dairy Cattle) فقط.
                    مهمتك هي تقديم إجابات علمية وبيولوجية دقيقة وشاملة من خلال الدمج بين مصدرين أساسيين:
                    أولاً: كتاب (Nutrient Requirements of Dairy Cattle - NASEM) المرفق كملف كامل مع هذا الطلب (إن وجد).
                    ثانياً: "مجموعة الأبحاث والمصادر العلمية المتاحة من البحث الحي" المرفقة أدناه.
                    
                    التزم بالقوانين التالية بصرامة شديدة:
                    1. التخصص الحصري (أهم قانون): يُحظر عليك تماماً الإجابة على أي أسئلة تتعلق بحيوانات أخرى (مثل الأغنام، الماعز، عجول التسمين غير الحلوب، الدواجن، الخيول) أو أي مواضيع خارج نطاق الأبقار الحلوب. إذا كان السؤال لا يخص الأبقار الحلوب، اعتذر بلباقة وقل بوضوح: "عذراً، تخصصي يقتصر حصرياً على تغذية وإدارة الأبقار الحلوب، ولا يمكنني تقديم معلومات حول هذا الموضوع."
                    2. الشمول والدقة: استخرج المعادلات، النسب المئوية، ومعدلات الأيض مباشرة من ملف كتاب NASEM المرفق إن وجدت، وادعمها بالأبحاث الحديثة المرفقة أدناه لتقديم إجابة متكاملة تخص الأبقار الحلوب.
                    3. التوثيق الأكاديمي: يجب توثيق كل معلومة داخل النص. إذا استخدمت معلومات من ملف كتاب NASEM استخدم الرمز [NASEM, رقم الصفحة إن أمكن]، وإذا استخدمت معلومات من الأبحاث المرفقة استخدم رقم المرجع مثل [1] أو [2].
                    4. منع التأليف نهائياً: إذا لم تجد إجابة علمية دقيقة في الرابط الثابت أو في الأبحاث المرفقة، قل بوضوح: "لا توفر المراجع الحالية بيانات علمية دقيقة للإجابة على هذا السؤال".
                    5. قسم المراجع: في نهاية الإجابة، قم بعمل قسم "المراجع العلمية" واذكر فيها روابط الأبحاث التي اعتمدت عليها فعلياً، بالإضافة إلى الإشارة لكتاب NASEM إذا تم استخدامه.
                    
                    سؤال المستخدم: {query}
                    
                    الأبحاث والمصادر العلمية المتاحة من البحث الحي:
                    {context}
                    """
                    
                    answer = None
                    # استخدام نماذج 1.5 لأنها قادرة على قراءة المستندات والملفات المرفقة
                    preferred_models = ["models/gemini-1.5-pro-latest", "models/gemini-1.5-flash-latest", "models/gemini-1.5-pro", "models/gemini-1.5-flash"]
                    models_to_try = [m for m in preferred_models if m in available_models] + [m for m in available_models if m not in preferred_models]

                    # تجهيز المحتوى للإرسال: النص + ملف الكتاب (إن وجد)
                    contents_to_send = [prompt]
                    if nasem_file:
                        contents_to_send.append(nasem_file)

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
                        st.error("عذراً، لم نتمكن من معالجة الإجابة حالياً عبر النماذج المتاحة. (تأكد من أن حجم الكتاب يتناسب مع حصة API الخاصة بك).")
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
