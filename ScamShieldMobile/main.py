import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
#(pattern, label shown when matched)
#\b word boundaries on short terms so innocent words
#like "love", "very" or "farm" are never flagged.
SCAM_PATTERNS = [
    (r'https?://[^\s]+', 'suspicious link'),
    (r'telegram\.me', 'telegram link'),
    (r't\.me/', 'telegram link'),
    (r'whatsapp\.com', 'whatsapp link'),
    (r'\bbvn\b', 'BVN request'),
    (r'account block', 'account-block threat'),
    (r'\bcongratulations\b', 'prize lure'),
    (r'\btransfer\w*\b', 'money transfer'),
    (r'\bcrypto\w*\b', 'crypto'),
    (r'\binvestment\b', 'investment'),
    (r'guaranteed profit', 'guaranteed profit'),
    (r'verify your account', 'verify-your-account'),
    (r'urgent action required', 'urgent action'),
    (r'\bbts\b', 'BTS mention'),
    (r'\bjin\b', 'BTS member name'),
    (r'\bsuga\b', 'BTS member name'),
    (r'j-hope', 'BTS member name'),
    (r'\bhobi\b', 'BTS member name'),
    (r'\brm\b', 'BTS member name'),
    (r'\bnamjoon\b', 'BTS member name'),
    (r'\bjoon\b', 'BTS member name'),
    (r'\bjimin\b', 'BTS member name'),
    (r'\bv\b', 'BTS member name'),
    (r'\btae\b', 'BTS member name'),
    (r'\bjungkook\b', 'BTS member name'),
    (r'\bhybe\b', 'HYBE mention'),
    (r'\bsouth\s+korea\b', 'South Korea mention'),
    (r'\bseoul\b', 'Seoul mention'),
]
class ScamShieldApp(App):
    def build(self):
        # Set up a clean, vertical box layout with standard spacing
        self.window = BoxLayout(orientation='vertical', padding=30, spacing=20)

        # Header Label
        self.header = Label(
            text="🚨 ScamShield Mobile Scanner 🚨",
            font_size='24sp',
            bold=True
        )
        self.window.add_widget(self.header)
    
        # Subtitle instructions
        self.sub_label = Label(
            text="Paste a message or link below to run a security scan:",
            font_size='14sp'
        )
        self.window.add_widget(self.sub_label)
    
        # Text Input box for user pasting messages
        self.user_input = TextInput(
            hint_text="Paste suspicious text here...",
            multiline=True,
            font_size='16sp'
        )
        self.window.add_widget(self.user_input)
    
        # Scan Execution Button
        self.scan_btn = Button(
            text="RUN SECURITY SCAN",
            font_size='18sp',
            bold=True
        )
        self.scan_btn.bind(on_press=self.analyze_text)
        self.window.add_widget(self.scan_btn)
    
        # Dynamic Output Status Label
        self.result_label = Label(
            text="System status: Ready to scan",
            font_size='16sp'
        )
        self.window.add_widget(self.result_label)
    
        return self.window
    
    def analyze_text(self, instance):
        text = self.user_input.text.strip()
        if not text:
            self.result_label.text = "⚠️ Please paste text to analyze."
            return
    
        hits = []
        for pattern, label in SCAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if label not in hits:
                    hits.append(label)
    
        if hits:
            self.result_label.text = "🚨 SCAM DETECTED: " + ", ".join(hits)
        else:
            self.result_label.text = "✅ SAFE: No obvious scam parameters detected."

if __name__ == '__main__':
    ScamShieldApp().run()




