from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
import sqlite3
import pandas as pd
from fuzzywuzzy import process
from kivy.utils import get_color_from_hex 
import requests
from openai import OpenAI

def get_closest_match(input_ingredient, known_ingredients, threshold=80):
    match, score = process.extractOne(input_ingredient, known_ingredients)
    if score >= threshold:
        return match
    else:
        return None

class HomeScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class NameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = sqlite3.connect('/Users/cenk/Python/Food/foods.db')
        self.df = pd.read_sql('SELECT * FROM epi_r', self.conn)

    def search_food(self):
        title_keyword = self.ids.title_input.text.strip()
        
        if not title_keyword:
            return

        recipes = self.df[self.df['title'].str.contains(title_keyword, case=False, na=False)]
        recipes = recipes[['title', 'rating']]

        if recipes.empty:
            return
        else:
            app = App.get_running_app()
            app.name.clear()
            app.rating.clear()
            app.name.extend(recipes['title'].tolist())
            app.rating.extend(recipes['rating'].tolist())
            app.change_screen("recipe_screen")


class IngredientsScreen(Screen):
    ingredients = []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = sqlite3.connect('/Users/cenk/Python/Food/foods.db')
        self.df = pd.read_sql('SELECT * FROM epi_r', self.conn)
        self.known_ingredients = self.df.columns.tolist()

    def add_ingredient(self, name):
        if name.strip():
            if name in self.ingredients:
                return
            matched_ingredient = get_closest_match(name, self.known_ingredients)
            if matched_ingredient and matched_ingredient != name:
                self.ids.add.text = f"Did you mean: {matched_ingredient}?"     
            else:
                self.ingredients.append(matched_ingredient if matched_ingredient else name)
                self.ids.ingredients_text.text = " , ".join(self.ingredients)
                self.ids.add.text = ""

    def delete_ingredient(self, name):
        if name in self.ingredients:
            self.ingredients.remove(name)
            self.ids.ingredients_text.text = " , ".join(self.ingredients)
        self.ids.delete.text = ""

    def search_recipes(self):
        if not self.ingredients:
            return
        
        recipes = self.df[(self.df[self.ingredients] == 1).all(axis=1)]
        recipes = recipes[['title', 'rating']]
        
        if recipes.empty:
            return
        else:
            app = App.get_running_app()
            app.name.clear()
            app.rating.clear()
            app.name.extend(recipes['title'].tolist())
            app.rating.extend(recipes['rating'].tolist())
            app.change_screen("recipe_screen")

class RecipeScreen(Screen):
    def on_enter(self):
        self.ids.scroll_box.clear_widgets()
        app = App.get_running_app()
        max_buttons = 20

        for i in range(min(max_buttons, len(app.name))):
            title = app.name[i]
            rating = app.rating[i]
            hex_color = "#E9967A" if (i % 2 == 0) else "#D77A61"

            button = Button(
                text=f"{title} (Rating: {rating})",
                size_hint_y=None,
                height=100,
                background_normal="",
                background_color=get_color_from_hex(hex_color)
            )
            button.bind(on_release=lambda btn, title=title: self.on_button_click(title))
            self.ids.scroll_box.add_widget(button)

    def on_button_click(self, recipe_title):
        access_key = 'unsplash api access key'
        search_term = f'{recipe_title}'
        url = f'https://api.unsplash.com/search/photos?query={search_term}&client_id={access_key}'

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                image_url = data['results'][0]['urls']['regular']
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    with open('downloaded_image.jpg', 'wb') as f:
                        f.write(image_response.content)

        app = App.get_running_app()
        app.title = recipe_title
        app.change_screen("recipe_text_screen")

        recipe_text_screen = app.root.ids.recipe_text_screen
        recipe_text_screen.ids.recipe_image.source = 'downloaded_image.jpg'
        recipe_text_screen.ids.recipe_image.reload()
        
class RecipeTextScreen(Screen):
    def on_enter(self):
        client = OpenAI(api_key="OpenAi api access key")
        app = App.get_running_app()

        for i in range(1):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"give me recipe of {app.title} dont give ingredients"}
                    ],
                    max_tokens=500
                )
                recipe_text = response.choices[0].message.content
                self.ids.recipe_description.text = recipe_text
                break
            except Exception as e:
                print(f"An error occurred: {e}")

Gui = Builder.load_file('main.kv')

class MainApp(App):
    name = []
    rating = []
    title = ''

    def build(self):
        return Gui

    def change_screen(self, screen_name):
        screen_manager = self.root.ids['screen_manager']
        screen_manager.current = screen_name

MainApp().run()
