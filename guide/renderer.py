GUIDE_STYLE = """
body { font-family: var(--guide-font), "Segoe UI", Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background: #f9f9f9; color: #333; display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 220px; background: #2c3e50; color: white; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; flex-shrink: 0; }
.sidebar h2 { color: #ecf0f1; font-size: 1.2em; margin-top: 0; border-bottom: 2px solid #34495e; padding-bottom: 10px; }
.nav-link { color: #bdc3c7; text-decoration: none; padding: 8px 0; display: block; transition: color 0.3s; font-size: 0.95em; }
.nav-link:hover { color: #ffffff; font-weight: bold; }
.main-content { flex-grow: 1; padding: 20px 40px; overflow-y: auto; scroll-behavior: smooth; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 0; }
h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding: 10px; background: linear-gradient(to right, #f0f4f8, #ffffff); border-radius: 3px; }
h3 { color: #2980b9; margin-top: 20px; }
.shortcut { background: #3498db; color: white; padding: 2px 6px; border-radius: 4px; font-family: "Consolas", monospace; font-size: 0.9em; font-weight: bold; }
.feature { background: linear-gradient(to right, #e8f5e9, #f1fdf3); padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #4caf50; }
.tip { background: linear-gradient(to right, #fff3cd, #fffaf0); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ff9800; }
.warning { background: linear-gradient(to right, #ffebee, #fff5f6); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #f44336; }
.warning strong { color: #c0392b; }
ul { padding-left: 20px; }
li { margin: 6px 0; }
code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: "Consolas", monospace; border: 1px solid #ddd; color: #e74c3c; }
table { width: 100%; border-collapse: collapse; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-radius: 5px; overflow: hidden; }
th, td { border: none; border-bottom: 1px solid #e8e8e8; padding: 10px; text-align: left; }
th { background: linear-gradient(135deg, #3498db 0%, #5dade2 100%); color: white; font-weight: 600; }
tr:nth-child(even) { background: #fafbfc; }
tr:hover { background: #f0f7ff; }
"""


def render_page(lang, sidebar_html, body_html):
    font = '"Microsoft YaHei", "Segoe UI", Arial, sans-serif' if lang == "cn" else '"Segoe UI", Arial, sans-serif'
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        :root {{ --guide-font: {font}; }}
        {GUIDE_STYLE}
    </style>
</head>
<body>
    <div class="sidebar">{sidebar_html}</div>
    <div class="main-content">{body_html}</div>
</body>
</html>
"""
