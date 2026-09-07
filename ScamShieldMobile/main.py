import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.utils import get_color_from_hex

class ScamShieldApp(App):
def build(self):
# Set up a clean, professional dark gray background layout
self.window = BoxLayout(orientation='vertical', padding=30, spacing=20)

# Header Label
self.header = Label(
text="🚨 ScamShield Mobile Scanner 🚨",
font_size='24sp',
bold=True,
size_hint_y=None,
height=50
)
self.window.add_widget(self.header)

# Subtitle instructions
self.sub_label = Label(
text="Paste a message, email, or link below to run a security scan:",
font_size='14sp',
size_hint_y=None,
height=30
)
self.window.add_widget(self.sub_label)

# Text Input box for user pasting messages
self.user_input = TextInput(
hint_text="Paste suspicious text here...",
multiline=True,
font_size='16sp',
background_color=get_color_from_hex('#FFFFFF')
)
self.window.add_widget(self.user_input)

# Scan Execution Button
self.scan_btn = Button(
text="RUN SECURITY SCAN",
font_size='18sp',
bold=True,
background_color=get_color_from_hex('#007BFF'),
size_hint_y=None,
height=60
)
self.scan_btn.bind(on_press=self.analyze_text)
self.window.add_widget(self.scan_btn)

# Dynamic Output Status Label
self.result_label = Label(
text="System status: Ready to scan",
font_size='16sp',
size_hint_y=None,
height=50
)
self.window.add_widget(self.result_label)

return self.window

def analyze_text(self, instance):
text = self.user_input.text.strip()
if not text:
self.result_label.text = "⚠️ Please paste text to analyze."
return

# Your custom RegEx security definitions we verified on LinkedIn!
scam_patterns = [
r'(?i)telegram.me', r'(?i)t.me/', r'(?i)whatsapp.com',
r'(?i)crypto', r'(?i)investment', r'(?i)guaranteed profit',
r'(?i)verify your account', r'(?i)urgent action required'
 ]

detected = False
for pattern in scam_patterns:
if re.search(pattern, text):
detected = True
break

if detected:
self.result_label.text = "🚨 SCAM DETECTED: Flagged safety risks found!"
self.result_label.color = get_color_from_hex('#FF0000') # Flashes Red!
else:
self.result_label.text = "✅ SAFE: No obvious scam parameters detected."
self.result_label.color = get_color_from_hex('#00FF00') # Flashes Green!

if name == 'main':
ScamShieldApp().run()



