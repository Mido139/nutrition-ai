from flask import Flask, request, jsonify
import requests
import os
from google import genai # التعديل الأول: المكتبة الجديدة
from tavily import TavilyClient

app = Flask(__name__)

# --- إعدادات البيئة ---
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = "DairyBot2026" # كلمة السر للربط مع ميتا

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# التعديل الثاني: تهيئة عميل الاتصال
client = genai.Client(api_key=GEMINI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# --- نقطة الاتصال (Webhook) ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # 1. التحقق من ميتا (Verification)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                return challenge, 200
            else:
                return 'Forbidden', 403
        return 'OK', 200

    # 2. استقبال الرسائل (Receiving Messages)
    elif request.method == 'POST':
        body = request.get_json()
        if body.get('object'):
            if body.get('entry') and body['entry'][0].get('changes') and body['entry'][0]['changes'][0].get('value').get('messages'):
                message_data = body['entry'][0]['changes'][0]['value']['messages'][0]
                sender_phone = message_data['from']
                msg_text = message_data['text']['body']
                
                # إرسال رسالة "جاري التفكير..."
                send_whatsapp_message(sender_phone, "⏳ جاري تحليل سؤالك وبحث المراجع العلمية...")
                
                # معالجة السؤال
                reply = process_with_ai(msg_text)
                
                # إرسال الإجابة النهائية
                send_whatsapp_message(sender_phone, reply)
                
            return 'EVENT_RECEIVED', 200
        else:
            return 'Not Found', 404

def process_with_ai(query):
    try:
        scientific_query = query + " AND (dairy cattle OR dairy cows OR الأبقار الحلوب) (بحث علمي OR دراسة أكاديمية)"
        search_response = tavily_client.search(scientific_query, search_depth="advanced", max_results=3)
        
        context = ""
        for index, result in enumerate(search_response.get("results", [])):
            context += f"Source [{index + 1}]:\n- Info: {result['content']}\n\n"
            
        prompt = f"""
        أنت مستشار خبير في تغذية وإدارة الأبقار الحلوب.
        أجب على سؤال المستخدم بناءً على المرجع الأساسي (NASEM) وهذا السياق:
        {context}
        
        سؤال المستخدم: {query}
        """
        
        # التعديل الثالث: استخدام الطريقة الجديدة لتوليد المحتوى
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        # طباعة الخطأ في سجلات السيرفر عشان لو حصلت مشكلة نقدر نتبعها
        print(f"Error in process_with_ai: {e}")
        return "⚠️ عذراً، لم أتمكن من جلب الإجابة الآن. حاول مرة أخرى."

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
