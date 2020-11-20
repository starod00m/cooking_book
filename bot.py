import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from cooking_book import CookingBook as book
from cooking_book import Recipes as book_recipes
from cooking_book import Categories as book_categories
from configparser import ConfigParser
from collections import namedtuple
import time

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
TOKEN = config['AUTH']['TOKEN']

'''Инициализирум бота'''
bot = telebot.TeleBot(TOKEN)

'''Стандартные кнопки'''
go_home = types.InlineKeyboardButton(text='----домой----', callback_data='go_home')
cancel = types.InlineKeyboardButton(text='----ОТМЕНА----', callback_data='go_home')


class BaseBot:

    def __init__(self, call, category=None, title=None):
        self.call = call
        self.user_data = self.get_user_data()
        self.id = self.user_data.user_id
        self.username = self.user_data.username
        self.message = self.user_data.message
        self.category = category
        self.recipe_title = title
        self.markup = types.InlineKeyboardMarkup()

    def home(self, msg):
        get_categories_button = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='get_categories')
        add_category_button = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
        get_all_recipes_button = types.InlineKeyboardButton(text='Все рецпты', callback_data='get_all_recipes')
        self.markup.add(get_categories_button, add_category_button)
        self.markup.add(get_all_recipes_button)
        user_data = self.get_user_data(msg)
        bot.send_message(user_data.user_id, text="Привет. Я твоя книга рецептов. Выбери действие:",
                         reply_markup=self.markup)

    def get_user_data(self, call=None):
        user_data = namedtuple('user_data', ['user_id', 'username', 'text', 'call_id', 'message'])
        call = self.call if call is None else call
        try:
            return user_data(call.from_user.id, call.from_user.username, call.message.text, call.id, call.message)
        except AttributeError:
            message = call
            return user_data(message.chat.id, message.chat.username, message.text, None, message)

    @staticmethod
    def send_notification(_id, response, timeout: float = 1):
        message = bot.send_message(_id, f'_{response.body}_', parse_mode='Markdown')
        time.sleep(timeout)
        bot.delete_message(message.chat.id, message.message_id)


class Categories(BaseBot):

    def get(self):
        response = book_categories(self.id, self.username).get()
        if response.status:
            for category in response.body:
                self.markup.add(
                    types.InlineKeyboardButton(text=category, callback_data='get_recipes_titles' + ':' + category))
            self.markup.add(go_home)
            bot.send_message(self.id, text="Ваши категории", reply_markup=self.markup)
        else:
            self.send_notification(self.id, response, timeout=0.8)
            self.home(self.message)

    def add(self):
        def __add(_call):
            _user_data = self.get_user_data(_call)
            response = book_categories(_user_data.user_id, _user_data.username).add(_user_data.text)
            self.send_notification(_user_data.user_id, response, timeout=1)
            self.home(_user_data.message)

        bot.send_message(self.id, 'Введи название категории')
        bot.register_next_step_handler(self.message, __add)

    def rename(self):
        def __rename(_call, _category):
            _user_data = self.get_user_data(_call)
            response = book_categories(_user_data.user_id, _user_data.username).rename(_category, _user_data.text)
            _category = _user_data.text if response.status else _category
            go_back = types.InlineKeyboardButton(text='----назад----',
                                                 callback_data='get_recipes_titles' + ':' + _category)
            self.markup.add(go_back, go_home)
            bot.send_message(_user_data.user_id, response.body, reply_markup=self.markup)

        bot.send_message(self.id, 'Введите новое имя категории')
        bot.register_next_step_handler(self.message, __rename, self.category)

    def confirm_delete(self):
        yes = types.InlineKeyboardButton(text='----да----', callback_data='delete_confirmed' + ':' + self.category)
        no = types.InlineKeyboardButton(text='----нет----', callback_data='get_recipes_titles' + ':' + self.category)
        self.markup.add(no, yes)
        bot.send_message(self.id, text=f'Вы уверены, что хотите удалить категорию "{self.category}"?',
                         reply_markup=self.markup)

    def delete(self):
        response = book_categories(self.id, self.username).delete(self.category)
        self.send_notification(self.id, response)
        routes(self.call, command='get_categories')


class Recipes(BaseBot):

    def get_from_category(self):
        response = book_recipes(self.id, self.username).get_titles(self.category)
        add_recipe_button = types.InlineKeyboardButton(text='----добавить рецепт----',
                                                       callback_data='add_recipe' + ':' + self.category)
        go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_categories')
        rename_category_button = types.InlineKeyboardButton(text='----переименовать----    ',
                                                            callback_data='rename_category' + ':' + self.category)
        delete_category_button = types.InlineKeyboardButton(text='----удалить----',
                                                            callback_data='delete_category' + ':' + self.category)

        if response.status:
            for recipe_title in response.body:
                self.markup.add(types.InlineKeyboardButton(
                    text=recipe_title, callback_data='get_recipe' + ':' + self.category + ':' + recipe_title))
            self.markup.add(add_recipe_button)
            self.markup.add(rename_category_button, delete_category_button)
            self.markup.add(go_back, go_home)
            bot.send_message(self.id, f'*Рецпты в категории "{self.category}"*', parse_mode='Markdown',
                             reply_markup=self.markup)
        else:
            self.markup.add(add_recipe_button)
            self.markup.add(rename_category_button, delete_category_button)
            self.markup.add(go_back, go_home)
            bot.send_message(self.id, f'_{response.body}_', parse_mode='Markdown', reply_markup=self.markup)

    def get_all(self):
        response = book_recipes(self.id, self.username).get_all()
        for recipe in response.body:
            recipe_title = recipe.split('(')[0].strip()
            category = recipe.split('"')[1].strip()
            self.markup.add(types.InlineKeyboardButton(recipe,
                                                       callback_data='get_recipe' + ':' + category + ':' + recipe_title))
        self.markup.add(go_home)
        bot.send_message(self.id, text='*Все рецепты*', parse_mode='Markdown', reply_markup=self.markup)

    def get(self):
        response = book_recipes(self.id, self.username).get(self.category, self.recipe_title)
        go_back = types.InlineKeyboardButton(text='----назад----',
                                             callback_data='get_recipes_titles' + ':' + self.category)
        self.markup.add(types.InlineKeyboardButton(
            text='----переименовать----', callback_data='rename_recipe' + ':' + self.category + ':' + self.recipe_title))
        self.markup.add(go_back, go_home)
        bot.send_message(self.id, f'*{self.recipe_title}*\n\n{response.body}',
                         reply_markup=self.markup, parse_mode='Markdown')

    def add(self):
        def __add_recipe_title(_call):
            _user_data = self.get_user_data(_call)
            title = _user_data.text
            bot.send_message(self.id, 'Введи текст рецепта')
            bot.register_next_step_handler(_user_data.message, __add_recipe_body, self.category, title)

        def __add_recipe_body(_call, title):
            _user_data = self.get_user_data(_call)
            response = book_recipes(self.id, self.username).add(self.category, title, _user_data.text)
            self.send_notification(self.id, response)
            routes(_call, command='get_recipes_titles', category=self.category)

        bot.send_message(self.id, 'Введите название рецепта')
        bot.register_next_step_handler(self.message, __add_recipe_title)

    def rename(self):
        def __rename_recipe(_call):
            _user_data = self.get_user_data(_call)
            new_title = _user_data.text
            _response = book_recipes(self.id, self.username).rename(self.category, self.recipe_title, new_title)
            recipe = new_title if _response.status else self.recipe_title
            self.send_notification(self.id, response=_response)
            routes(_call, command='get_recipe', category=self.category, recipe=recipe)

        bot.send_message(self.id, 'Введите новое имя рецепта')
        bot.register_next_step_handler(self.message, __rename_recipe)


@bot.message_handler(commands=['start'])
def start(msg):
    user_data = BaseBot(msg).get_user_data()
    book(user_data.user_id, user_data.username).create_book()
    BaseBot(msg).home(msg)


@bot.callback_query_handler(lambda call: True)
def routes(call, command=None, category=None, recipe=None):
    # print(call.data)
    if command is None:
        command = call.data.split(':')[0]
        try:
            category = call.data.split(':')[1]
            recipe = call.data.split(':')[2]
        except IndexError:
            pass

    if command == 'go_home':
        BaseBot(call).home(call)

    elif command == 'get_categories':
        Categories(call).get()

    elif command == 'add_category':
        Categories(call).add()

    elif command == 'rename_category':
        Categories(call, category).rename()

    elif command == 'delete_category':
        Categories(call, category).confirm_delete()

    elif command == 'delete_confirmed':
        Categories(call, category).delete()

    elif command == 'get_recipes_titles':
        Recipes(call, category).get_from_category()

    elif command == 'get_all_recipes':
        Recipes(call).get_all()

    elif command == 'get_recipe':
        Recipes(call, category, recipe).get()

    elif command == 'add_recipe':
        Recipes(call, category).add()

    elif command == 'rename_recipe':
        Recipes(call, category, recipe).rename()

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except (ApiTelegramException, AttributeError):
        pass


if __name__ == '__main__':
    bot.polling(none_stop=True)
