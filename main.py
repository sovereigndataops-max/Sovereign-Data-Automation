print("App Launching")
from kivy.app import App
from kivy.uix.label import Label

class SundayApp(App):
    def  build(self):
          return Label(text='Sunday App Live')

  if__name__ == '__main__':
    SundayApp().run()
