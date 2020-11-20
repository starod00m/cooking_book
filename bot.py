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


def get_user_data(call):
    user_data = namedtuple('user_data', ['user_id', 'username', 'text', 'call_id', 'message'])
    try:
        return user_data(call.from_user.id, call.from_user.username, call.message.text, call.id, call.message)
    except AttributeError:
        message = call
        return user_data(message.chat.id, message.chat.username, message.text, None, message)


def send_notification(id, response, timeout: float = 1):
    message = bot.send_message(id, f'_{response.body}_', parse_mode='Markdown')
    time.sleep(timeout)
    bot.delete_message(message.chat.id, message.message_id)

class Categories:

    def __init__(self, call, category=None):
        self.call = call
        self.user_data = get_user_data(call)
        self.id = self.user_data.user_id
        self.username = self.user_data.username
        self.message = self.user_data.message
        self.category = category
        self.markup = types.InlineKeyboardMarkup()

    def get(self):
        response = book_categories(self.id, self.username).get()
        if response.status:
            for category in response.body:
                self.markup.add(types.InlineKeyboardButton(text=category, callback_data='get_recipes_titles' + ':' + category))
            self.markup.add(go_home)
            bot.send_message(self.id, text="Ваши категории", reply_markup=self.markup)
        else:
            send_notification(self.id, response, timeout=0.8)
            home(self.message)


    def add(self):
        def __add(_call):
            _user_data = get_user_data(_call)
            response = book_categories(_user_data.user_id, _user_data.username).add(_user_data.text)
            send_notification(_user_data.user_id, response, timeout=1)
            home(_user_data.message)

        bot.send_message(self.id, 'Введи название категории')
        bot.register_next_step_handler(self.message, __add)


    def rename(self):
        def __rename(_call, _category):
            _user_data = get_user_data(_call)
            response = book_categories(_user_data.user_id, _user_data.username).rename(_category, _user_data.text)
            _category = _user_data.text if response.status else _category
            go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_recipes_titles' + ':' + _category)
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
        send_notification(self.id, response)
        routes(self.call, command='get_categories')


def get_recipes(call, category):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(3)
    response = book_recipes(user_data.user_id, user_data.username).get_titles(category)
    add_recipe_button = types.InlineKeyboardButton(text='----добавить рецепт----',
                                                   callback_data='add_recipe' + ':' + category)
    go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_categories')
    rename_category_button = types.InlineKeyboardButton(text='----переименовать----    ',
                                                        callback_data='rename_category' + ':' + category)
    delete_category_button = types.InlineKeyboardButton(text='----удалить----',
                                                        callback_data='delete_category' + ':' + category)

    if response.status:
        for recipe_title in response.body:
            markup.add(types.InlineKeyboardButton(text=recipe_title, callback_data='get_recipe' + ':'
                                                                                   + category + ':' + recipe_title))
        markup.add(add_recipe_button)
        markup.add(rename_category_button, delete_category_button)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, f'*Рецпты в категории "{category}"*', parse_mode='Markdown',
                         reply_markup=markup)
    else:
        markup.add(add_recipe_button)
        markup.add(rename_category_button, delete_category_button)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, f'_{response.body}_', parse_mode='Markdown', reply_markup=markup)


def get_all_recipes(call):
    user_data = get_user_data(call)
    response = book_recipes(user_data.user_id, user_data.username).get_all()
    markup = types.InlineKeyboardMarkup(1)
    for recipe in response.body:
        recipe_title = recipe.split('(')[0].strip()
        category = recipe.split('"')[1].strip()
        markup.add(types.InlineKeyboardButton(recipe, callback_data='get_recipe' + ':' + category + ':' + recipe_title))
    markup.add(go_home)
    bot.send_message(user_data.user_id, text='*Все рецепты*', parse_mode='Markdown', reply_markup=markup)


def get_recipe(call, category, title):
    user_data = get_user_data(call)
    response = book_recipes(user_data.user_id, user_data.username).get(category, title)
    markup = types.InlineKeyboardMarkup(2)
    go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_recipes_titles' + ':' + category)
    markup.add(types.InlineKeyboardButton(text='----переименовать----',
                                          callback_data='rename_recipe' + ':' + category + ':' + title))
    markup.add(go_back, go_home)
    bot.send_message(user_data.user_id, f'*{title}*\n\n{response.body}', reply_markup=markup, parse_mode='Markdown')


def add_recipe(call, category):
    def __add_recipe_title(_call, _category):
        _user_data = get_user_data(_call)
        title = _user_data.text
        bot.send_message(_user_data.user_id, 'Введи текст рецепта')
        bot.register_next_step_handler(_user_data.message, __add_recipe_body, _category, title)

    def __add_recipe_body(_call, _category, title):
        _user_data = get_user_data(_call)
        response = book_recipes(_user_data.user_id, _user_data.username).add(_category, title, _user_data.text)
        send_notification(user_data.user_id, response)
        routes(_call, command='get_recipes_titles', category=_category)

    user_data = get_user_data(call)
    bot.send_message(user_data.user_id, 'Введи название рецепта')
    bot.register_next_step_handler(user_data.message, __add_recipe_title, category)


def rename_recipe(call, category, old_title):
    def __rename_recipe(_call):
        _user_data = get_user_data(_call)
        new_title = _user_data.text
        _response = book_recipes(user_data.user_id, user_data.username).rename(category, old_title, new_title)
        recipe = new_title if _response.status else old_title
        send_notification(user_data.user_id, response=_response)
        routes(_call, command='get_recipe', category=category, recipe=recipe)

    user_data = get_user_data(call)
    bot.send_message(user_data.user_id, 'Введите новое имя рецепта')
    bot.register_next_step_handler(user_data.message, __rename_recipe)


def home(msg):
    markup = types.InlineKeyboardMarkup(2)
    get_categories_button = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='get_categories')
    add_category_button = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
    get_all_recipes_button = types.InlineKeyboardButton(text='Все рецпты', callback_data='get_all_recipes')
    markup.add(get_categories_button, add_category_button)
    markup.add(get_all_recipes_button)
    user_data = get_user_data(msg)
    bot.send_message(user_data.user_id, text="Привет. Я твоя книга рецептов. Выбери действие:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(msg):
    user_data = get_user_data(msg)
    book(user_data.user_id, user_data.username).create_book()
    home(msg)


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
        home(call)

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
        get_recipes(call, category)

    elif command == 'get_all_recipes':
        get_all_recipes(call)

    elif command == 'get_recipe':
        get_recipe(call, category, recipe)

    elif command == 'add_recipe':
        add_recipe(call, category)

    elif command == 'rename_recipe':
        rename_recipe(call, category, recipe)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except (ApiTelegramException, AttributeError):
        pass


if __name__ == '__main__':
    bot.polling(none_stop=True)
