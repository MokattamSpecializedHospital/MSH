import os
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import json
import base64

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
        """Handles routing for different API endpoints."""
        if self.path == '/api/recommend':
            self.handle_symptoms_recommendation()
        elif self.path == '/api/analyze':
            self.handle_report_analysis()
        else:
            self._send_response(404, {"error": "Endpoint not found"})

    def handle_symptoms_recommendation(self):
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
            2.  اشرح للمريض بلغة عربية بسيطة ومباشرة **لماذا** قمت بترشيح هذه العيادة.
            3.  إذا كان هناك احتمال آخر قوي، حدد عيادة ثانوية واشرح أيضاً لماذا قد تكون خياراً جيداً.
            4.  إذا كانت الشكوى غامضة جداً (مثل "أنا متعب")، قم بترشيح "الباطنة-العامة" واشرح أن الفحص العام هو أفضل نقطة بداية.
            5.  ردك **يجب** أن يكون بصيغة JSON فقط، بدون أي نصوص أو علامات قبله أو بعده. يجب أن يكون على هذا الشكل بالضبط:
            {{
              "recommendations": [
                {{ "id": "ID_العيادة", "reason": "شرح سبب الاختيار." }}
              ]
            }}
            """
            
            response = model.generate_content(prompt)
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
            json_response = json.loads(cleaned_text)
            self._send_response(200, json_response)

        except Exception as e:
            self._send_response(500, {"error": f"An internal server error occurred: {str(e)}"})

    def handle_report_analysis(self):
        """Handles receiving medical report images and returning an AI-based analysis."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            images_data = data.get('images')
            user_notes = data.get('notes', '')

            if not images_data:
                self._send_response(400, {"error": "Missing images in request"})
                return
            
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                self._send_response(500, {"error": "Server configuration error."})
                return

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Prepare image parts for the model
            image_parts = []
            for img in images_data:
                image_parts.append({
                    "mime_type": img["mime_type"],
                    "data": img["data"] 
                })

            prompt = f"""
            أنت مساعد طبي ذكي ومحلل تقارير طبية في مستشفى مرموق. مهمتك هي تحليل صور التقارير الطبية (تحاليل دم، أشعة، إلخ) التي يرفعها المريض وتقديم إرشادات أولية واضحة.
            قائمة معرفات (IDs) العيادات المتاحة هي: [{CLINICS_LIST}]
            ملاحظات المريض الإضافية: "{user_notes if user_notes else 'لا يوجد'}"

            المطلوب منك تحليل الصور المرفقة وتقديم رد بصيغة JSON فقط، بدون أي نصوص أو علامات قبله أو بعده، ويحتوي على الحقول التالية:
            1.  `interpretation`: (String) شرح مبسط جداً وواضح لما يظهر في التقرير. تجنب المصطلحات المعقدة. ركز على المؤشرات الرئيسية إن وجدت (مثال: "يُظهر التقرير ارتفاعاً طفيفاً في كريات الدم البيضاء، مما قد يشير إلى وجود التهاب."). **لا تقدم تشخيصاً نهائياً أبداً.**
            2.  `temporary_advice`: (Array of strings) قائمة نصائح عامة ومؤقتة يمكن للمريض اتباعها حتى زيارة الطبيب. يجب أن تكون نصائح آمنة (مثال: "الحصول على قسط كافٍ من الراحة"، "شرب كميات كافية من السوائل"، "تجنب المجهود البدني الشاق").
            3.  `recommendations`: (Array of objects) قائمة تحتوي على **عيادة واحدة فقط** هي الأنسب للحالة. يجب أن يحتوي كل عنصر على:
                - `id`: معرف (ID) العيادة من القائمة المتاحة.
                - `reason`: (String) شرح بسيط ومباشر لسبب اختيار هذه العيادة (مثال: "بناءً على نتائج تحليل وظائف الكلى، نوصي بالتوجه لعيادة أمراض الكلى لمتابعة الحالة.").

            مثال على الرد المطلوب:
            {{
              "interpretation": "يظهر تحليل الدم الكامل ارتفاعاً في مستوى السكر التراكمي، مما قد يشير إلى وجود مرض السكري أو حالة ما قبل السكري.",
              "temporary_advice": [
                "يُنصح بتجنب السكريات والحلويات.",
                "الحرص على شرب الماء بكميات كافية.",
                "مراقبة أي أعراض جديدة مثل العطش الشديد أو كثرة التبول."
              ],
              "recommendations": [
                {{
                  "id": "غدد-صماء-وسكر",
                  "reason": "بسبب ارتفاع مستوى السكر في الدم، فإن عيادة الغدد الصماء والسكري هي الجهة المختصة لمتابعة وتقييم الحالة بشكل دقيق."
                }}
              ]
            }}
            
            **مهم جداً:** إذا كانت الصور غير واضحة أو لا تحتوي على معلومات طبية، أعد رداً مناسباً في حقل `interpretation` مثل "الصور المرفقة غير واضحة أو لا تحتوي على معلومات طبية يمكن تحليلها." واترك الحقول الأخرى فارغة.
            """
            
            # Create the content array with the prompt and images
            content = [prompt] + image_parts
            
            response = model.generate_content(content)
            
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
            json_response = json.loads(cleaned_text)
            self._send_response(200, json_response)

        except Exception as e:
            self._send_response(500, {"error": f"An internal server error occurred: {str(e)}"})
