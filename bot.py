import telebot
from telebot import types
from cooking_book import CookingBook as book
from configparser import ConfigParser
from collections import namedtuple

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
TOKEN = config['AUTH']['TOKEN']

'''Инициализирум бота'''
bot = telebot.TeleBot(TOKEN)

'''Стандартные кнопки'''
go_home = types.InlineKeyboardButton(text='----ДОМОЙ----', callback_data='go_home')
cancel = types.InlineKeyboardButton(text='----ОТМЕНА----', callback_data='go_home')


def get_user_data(call):
    user_data = namedtuple('user_data', ['user_id', 'username', 'text', 'call_id', 'message'])
    try:
        return user_data(call.from_user.id, call.from_user.username, call.message.text, call.id, call.message)
    except AttributeError:
        message = call
        return user_data(message.chat.id, message.chat.username, message.text, None, message)


def get_categories(call):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    response = book(user_data.user_id, user_data.username).get_categories()
    if response.status:
        for category in response.body:
            markup.add(types.InlineKeyboardButton(text=category, callback_data='get_recipes_titles' + ':' + category))
        markup.add(go_home)
        bot.send_message(user_data.user_id, text="Ваши категории", reply_markup=markup)
    else:
        # markup.add(go_home)
        # bot.send_message(user_id, f'_{response.body}_', parse_mode='Markdown',reply_markup=markup)
        bot.answer_callback_query(callback_query_id=user_data.call_id, text=response.body)
        home(user_data.message)


def add_category(call):
    def __add_category(call):
        user_data = get_user_data(call)
        response = book(user_data.user_id, user_data.username).add_category(user_data.text)
        bot.send_message(user_data.user_id, response.body)
        home(user_data.message)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    # markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введи название категории', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __add_category)

def rename_category(call, category):

    def __rename_category(call, category):
        user_data = get_user_data(call)
        markup = types.InlineKeyboardMarkup(2)
        response = book(user_data.user_id, user_data.username).rename_category(category, user_data.text)
        category = user_data.text if response.status else category
        go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_recipes_titles' + ':' + category)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, response.body, reply_markup=markup)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    # markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введите новое имя категории', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __rename_category, category)


def get_recipes(call, category):
    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(3)
    response = book(user_data.user_id, user_data.username).get_recipes_titles(category)
    add_recipe = types.InlineKeyboardButton(text='----ДОБАВИТЬ РЕЦЕПТ----',
                                            callback_data='add_recipe' + ':' + category)
    go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_categories')
    rename = types.InlineKeyboardButton(text='----ПЕРЕИМЕНОВАТЬ----    ', callback_data='rename_category' + ':' + category)
    if response.status:
        for recipe_title in response.body:
            markup.add(types.InlineKeyboardButton(text=recipe_title, callback_data='get_recipe' + ':'
                                                                                   + category + ':' + recipe_title))
        markup.add(add_recipe)
        markup.add(rename)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, f'Рецпты в категории "{category}"', reply_markup=markup)
    else:
        markup.add(add_recipe)
        markup.add(rename)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, f'_{response.body}_',parse_mode='Markdown', reply_markup=markup)


def get_recipe(call, category, title):
    user_data = get_user_data(call)
    response = book(user_data.user_id, user_data.username).get_recipe(category, title)
    markup = types.InlineKeyboardMarkup(2)
    go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_recipes_titles' + ':' + category)
    markup.add(go_back, go_home)
    bot.send_message(user_data.user_id, f'*{title}*', parse_mode='Markdown')
    bot.send_message(user_data.user_id, response.body, reply_markup=markup)


def add_recipe(call, category):
    def __add_recipe_title(call, category):
        user_data = get_user_data(call)
        title = user_data.text
        bot.send_message(user_data.user_id, 'Введи текст рецепта')
        bot.register_next_step_handler(user_data.message, __add_recipe_body, category, title)

    def __add_recipe_body(call, category, title):
        user_data = get_user_data(call)
        response = book(user_data.user_id, user_data.username).add_recipe(category, title, user_data.text)
        markup = types.InlineKeyboardMarkup(2)
        go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_recipes_titles' + ':' + category)
        markup.add(go_back, go_home)
        bot.send_message(user_data.user_id, response.body, reply_markup=markup)

    user_data = get_user_data(call)
    markup = types.InlineKeyboardMarkup(1)
    markup.add(cancel)
    bot.send_message(user_data.user_id, 'Введи название рецепта', reply_markup=markup)
    bot.register_next_step_handler(user_data.message, __add_recipe_title, category)

def home(msg):
    markup = types.InlineKeyboardMarkup(2)
    get_categories = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='get_categories')
    add_category = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
    markup.add(get_categories, add_category)
    bot.send_message(msg.from_user.id, text="Привет. Я твоя книга рецептов. Выбери действие:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(msg):
    user_data = get_user_data(msg)
    book(user_data.user_id, user_data.username).create_book()
    home(msg)


@bot.callback_query_handler(lambda call: True)
def routes(call):
    print(call.data)
    command = call.data.split(':')[0]

    if command == 'go_home':
        home(call)

    elif command == 'get_categories':
        get_categories(call)

    elif command == 'add_category':
        add_category(call)

    elif command == 'rename_category':
        category = call.data.split(':')[1]
        rename_category(call, category)

    elif command == 'get_recipes_titles':
        category = call.data.split(':')[1]
        get_recipes(call, category)

    elif command == 'get_recipe':
        category = call.data.split(':')[1]
        recipe_title = call.data.split(':')[2]
        get_recipe(call, category, recipe_title)

    elif command == 'add_recipe':
        category = call.data.split(':')[1]
        add_recipe(call, category)

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)


if __name__ == '__main__':
    bot.polling(none_stop=True)
