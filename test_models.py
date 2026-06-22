import google.generativeai as genai
import os
import re
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

fallback_models = [
    'gemini-2.5-flash',
    'gemini-flash-latest',
    'gemini-3-flash-preview',
    'gemini-3.1-flash-lite'
]

working_model = None

for m in fallback_models:
    print(f'Testing {m}...')
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content('Say hello')
        print(f'SUCCESS with {m}: {response.text.strip()}')
        working_model = m
        break
    except Exception as e:
        print(f'FAILED with {m}: {e}')

audit_working = None
for m in ['gemini-3.1-pro-preview', 'gemini-2.5-pro', 'gemini-3-pro-preview', 'gemini-pro-latest']:
    print(f'Testing Audit {m}...')
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content('Say hello')
        print(f'SUCCESS with {m}: {response.text.strip()}')
        audit_working = m
        break
    except Exception as e:
        print(f'FAILED with {m}: {e}')

if working_model and audit_working:
    print(f'\nWriting Data model: {working_model} and Audit model: {audit_working} ...')

    with open('src/agent/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'gemini-\d\.\d-flash', working_model, content)
    content = re.sub(r'gemini-\d\.\d-pro-preview', audit_working, content)
    content = re.sub(r'gemini-\d\.\d-pro', audit_working, content)
    content = content.replace('gemini-pro', audit_working)
    with open('src/agent/app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    with open('src/skills/pii_redactor/scripts/data_simulator.py', 'r', encoding='utf-8') as f:
        sim = f.read()
    sim = re.sub(r'gemini-\d\.\d-flash', working_model, sim)
    with open('src/skills/pii_redactor/scripts/data_simulator.py', 'w', encoding='utf-8') as f:
        f.write(sim)

    for doc in ['WRITEUP.md', 'README.md']:
        with open(doc, 'r', encoding='utf-8') as f:
            d = f.read()
        d = re.sub(r'gemini-\d\.\d-flash', working_model, d)
        d = re.sub(r'gemini-\d\.\d-pro-preview', audit_working, d)
        d = re.sub(r'gemini-\d\.\d-pro', audit_working, d)
        with open(doc, 'w', encoding='utf-8') as f:
            f.write(d)

    print('Done replacing models!')
else:
    print('NO WORKING MODELS FOUND!')
