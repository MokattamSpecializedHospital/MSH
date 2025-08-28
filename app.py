import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json

# الآن نخبر فلاسك أن ملفات الواجهة الأمامية موجودة في نفس المكان (الجذر)
app = Flask(__name__, template_folder='.')
CORS(app)

# ... (باقي كود البايثون يبقى كما هو بدون أي تغيير)
# ... (CLINICS_LIST, recommend_clinic, serve_index)
