from kivy.app import App
from kivy.uix.label import Label

class ScamShieldApp(App):
    def build(self):
        return Label(text="ScamShield Mobile is running")

if __name__ == "__main__":
    ScamShieldApp().run()
