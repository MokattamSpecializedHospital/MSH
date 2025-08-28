import os
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import json

# القائمة الكاملة والمحدثة لمعرفات (IDs) العيادات (27 تخصص)
CLINICS_LIST = """
"الباطنة-العامة", "غدد-صماء-وسكر", "جهاز-هضمي-ومناظير", "باطنة-وقلب", "الجراحة-العامة",
"مناعة-وروماتيزم", "نساء-وتوليد", "أنف-وأذن-وحنجرة", "الصدر", "أمراض-الذكورة", "الجلدية",
"العظام", "المخ-والأعصاب-باطنة", "جراحة-المخ-والأعصاب", "المسالك-البولية", "الأوعية-الدموية",
"الأطفال", "الرمد", "تغذية-الأطفال", "مناعة-وحساسية-الأطفال", "القلب", "رسم-قلب-بالمجهود-وإيكو",
"جراحة-التجميل", "علاج-البواسير-والشرخ-بالليزر", "الأسنان", "السمعيات", "أمراض-الدم"
"""

class handler(BaseHTTPRequestHandler):
    
    def _send_response(self, status_code, data):
        """Helper function to send uniform JSON responses."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        """Handles pre-flight CORS requests from the browser."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handles the main logic of receiving symptoms and returning recommendations."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            symptoms = data.get('symptoms')

            if not symptoms:
                self._send_response(400, {"error": "Missing symptoms in request"})
                return
            
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("CRITICAL ERROR: GEMINI_API_KEY is not set in Vercel environment variables.")
                self._send_response(500, {"error": "Server configuration error."})
                return

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
            أنت مساعد طبي خبير ومحترف في مستشفى كبير. مهمتك هي تحليل شكوى المريض بدقة واقتراح أفضل عيادتين بحد أقصى من قائمة العيادات المتاحة.
            قائمة معرفات (IDs) العيادات المتاحة هي: [{CLINICS_LIST}]
            شكوى المريض: "{symptoms}"
            المطلوب منك:
            1.  حدد العيادة الأساسية الأكثر احتمالاً بناءً على الأعراض الرئيسية في الشكوى.
            2.  اشرح للمريض بلغة عربية بسيطة ومباشرة **لماذا** قمت بترشيح هذه العيادة (مثال: "بناءً على ذكرك لألم الصدر، فإن عيادة القلب هي الأنسب...").
            3.  إذا كان هناك احتمال آخر قوي، حدد عيادة ثانوية واشرح أيضاً لماذا قد تكون خياراً جيداً (مثال: "كاحتمال بديل، قد تكون هذه الأعراض مرتبطة بالجهاز التنفسي، لذا نرشح عيادة الصدر...").
            4.  إذا كانت الشكوى غامضة جداً (مثل "أنا متعب")، قم بترشيح "الباطنة-العامة" واشرح أن الفحص العام هو أفضل نقطة بداية.
            5.  ردك **يجب** أن يكون بصيغة JSON فقط، بدون أي نصوص أو علامات قبله أو بعده. يجب أن يكون على هذا الشكل بالضبط:
            {{
              "recommendations": [
                {{
                  "id": "ID_العيادة_الأساسية",
                  "reason": "شرح سبب اختيار العيادة الأساسية هنا."
                }},
                {{
                  "id": "ID_العيادة_الثانوية",
                  "reason": "شرح سبب اختيار العيادة الثانوية هنا."
                }}
              ]
            }}
            
            إذا كانت هناك توصية واحدة فقط، أعد القائمة بعنصر واحد. إذا كانت الشكوى غير طبية تماماً، أعد قائمة فارغة.
            """
            
            response = model.generate_content(prompt)
            
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
            try:
                json_response = json.loads(cleaned_text)
            except json.JSONDecodeError:
                print(f"WARNING: Gemini returned a non-JSON response: {cleaned_text}")
                json_response = {"recommendations": []}

            self._send_response(200, json_response)

        except Exception as e:
            print(f"CRITICAL ERROR: An exception occurred: {str(e)}")
            self._send_response(500, {"error": "An internal server error occurred. Please check the logs."})
