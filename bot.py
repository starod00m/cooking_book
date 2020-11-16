import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from cooking_book import CookingBook as book
from cooking_book import Recipes
from cooking_book import Categories
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


def send_notification(user_data, response, timeout: float = 1):
    message = bot.send_message(user_data.user_id, f'_{response.body}_', parse_mode='Markdown')
    time.sleep(timeout)
    bot.delete_message(message.chat.id, message.message_id)


def get_categories(call):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    response = Categories(user_data.user_id, user_data.username).get()
    if response.status:
        for category in response.body:
            markup.add(types.InlineKeyboardButton(text=category, callback_data='get_recipes_titles' + ':' + category))
        markup.add(go_home)
        bot.send_message(user_data.user_id, text="Ваши категории", reply_markup=markup)
    else:
        send_notification(user_data, response, timeout=0.8)
        # bot.answer_callback_query(callback_query_id=user_data.call_id, text=response.body)
        home(user_data.message)


def add_category(call):
    def __add_category(_call):
        _user_data = get_user_data(_call)
        response = Categories(_user_data.user_id, _user_data.username).add(_user_data.text)
        send_notification(_user_data, response, timeout=1)
        home(_user_data.message)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    # markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введи название категории', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __add_category)


def rename_category(call, category):
    def __rename_category(_call, _category):
        _user_data = get_user_data(_call)
        _markup = types.InlineKeyboardMarkup(2)
        response = Categories(_user_data.user_id, _user_data.username).rename(_category, _user_data.text)
        _category = _user_data.text if response.status else _category
        go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_recipes_titles' + ':' + _category)
        _markup.add(go_back, go_home)
        bot.send_message(_user_data.user_id, response.body, reply_markup=_markup)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    # markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введите новое имя категории', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __rename_category, category)


def confirm_delete(call, category):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(2)
    yes = types.InlineKeyboardButton(text='----да----', callback_data='delete_confirmed' + ':' + category)
    no = types.InlineKeyboardButton(text='----нет----', callback_data='get_recipes_titles' + ':' + category)
    markup.add(no, yes)
    bot.send_message(user_data.user_id, text=f'Вы уверены, что хотите удалить категорию "{category}"?',
                     reply_markup=markup)


def delete_category(call, category):
    user_data = get_user_data(call)
    response = Categories(user_data.user_id, user_data.username).delete(category)
    send_notification(user_data, response)
    routes(call, command='get_categories')


def get_recipes(call, category):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(3)
    response = Recipes(user_data.user_id, user_data.username).get_titles(category)
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


def get_recipe(call, category, title):
    user_data = get_user_data(call)
    response = Recipes(user_data.user_id, user_data.username).get(category, title)
    markup = types.InlineKeyboardMarkup(2)
    go_back = types.InlineKeyboardButton(text='----назад----', callback_data='get_recipes_titles' + ':' + category)
    markup.add(go_back, go_home)
    bot.send_message(user_data.user_id, f'*{title}*', parse_mode='Markdown')
    bot.send_message(user_data.user_id, response.body, reply_markup=markup)


def add_recipe(call, category):
    def __add_recipe_title(_call, _category):
        _user_data = get_user_data(_call)
        title = _user_data.text
        bot.send_message(_user_data.user_id, 'Введи текст рецепта')
        bot.register_next_step_handler(_user_data.message, __add_recipe_body, _category, title)

    def __add_recipe_body(_call, _category, title):
        _user_data = get_user_data(_call)
        response = Recipes(_user_data.user_id, _user_data.username).add(_category, title, _user_data.text)
        send_notification(_user_data, response)
        routes(_call, command='get_recipes_titles', category=_category)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    # markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введи название рецепта', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __add_recipe_title, category)


def home(msg):
    markup = types.InlineKeyboardMarkup(2)
    get_categories_button = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='get_categories')
    add_category_button = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
    markup.add(get_categories_button, add_category_button)
    user_data = get_user_data(msg)
    bot.send_message(user_data.user_id, text="Привет. Я твоя книга рецептов. Выбери действие:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(msg):
    user_data = get_user_data(msg)
    book(user_data.user_id, user_data.username).create_book()
    home(msg)


@bot.callback_query_handler(lambda call: True)
def routes(call, command=None, category=None):
    # print(call.data)
    if command is None:
        command = call.data.split(':')[0]
        try:
            category = call.data.split(':')[1]
        except IndexError:
            pass

    if command == 'go_home':
        home(call)

    elif command == 'get_categories':
        get_categories(call)

    elif command == 'add_category':
        add_category(call)

    elif command == 'rename_category':
        rename_category(call, category)

    elif command == 'delete_category':
        confirm_delete(call, category)

    elif command == 'delete_confirmed':
        delete_category(call, category)

    elif command == 'get_recipes_titles':
        get_recipes(call, category)

    elif command == 'get_recipe':
        recipe_title = call.data.split(':')[2]
        get_recipe(call, category, recipe_title)

    elif command == 'add_recipe':
        add_recipe(call, category)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except (ApiTelegramException, AttributeError):
        pass


if __name__ == '__main__':
    bot.polling(none_stop=True)
