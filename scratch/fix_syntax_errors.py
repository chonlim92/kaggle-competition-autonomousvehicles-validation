with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: line 1171
text = text.replace('"secure validation audit pipeline."\n                    , show_copy_button=True),', '"secure validation audit pipeline."\n                    ),\n                    show_copy_button=True,')

# Fix 2: line 1184
text = text.replace('                    interactive=False,\n                , show_copy_button=True)', '                    interactive=False,\n                    show_copy_button=True)')

# Fix 3: line 1232
text = text.replace('"Example (from Tab 1, show_copy_button=True):\\n\\n"', '"Example (from Tab 1):\\n\\n"')

# Fix 4: line 1258
text = text.replace('            elem_classes=["status-banner"],\n        , show_copy_button=True)', '            elem_classes=["status-banner"],\n            show_copy_button=True)')

# Fix 5: line 1267
text = text.replace('"[ ✅ SECURITY CLEARED — This text only is forwarded to gemini-2.5-pro ]"\n            , show_copy_button=True),', '"[ ✅ SECURITY CLEARED — This text only is forwarded to gemini-2.5-pro ]"\n            ),\n            show_copy_button=True,')

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Fixed syntax errors.')
