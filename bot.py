import telebot
from telebot import types
from cooking_book import CookingBook as book
from configparser import ConfigParser

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
TOKEN = config['AUTH']['TOKEN']

'''Инициализирум бота'''
bot = telebot.TeleBot(TOKEN)

'''Стандартные кнопки'''
go_home = types.InlineKeyboardButton(text='----ДОМОЙ----', callback_data='go_home')
cancel = types.InlineKeyboardButton(text='----ОТМЕНА----', callback_data='go_home')


def get_user_data(msg):
    return msg.chat.id, msg.chat.username


def get_categories(msg):
    markup = types.InlineKeyboardMarkup(1)
    user_id, username = get_user_data(msg)
    response = book(user_id, username).get_categories()
    if response.status:
        for category in response.body:
            markup.add(types.InlineKeyboardButton(text=category, callback_data='get_recipes_titles' + ':' + category))
        bot.send_message(user_id, text="Ваши категории", reply_markup=markup)
    else:
        bot.send_message(user_id, response.body)
        home(msg)


def add_category(msg):
    def __add_category(msg):
        user_id, username = get_user_data(msg)
        response = book(user_id, username).add_category(msg.text)
        bot.send_message(user_id, response.body)
        home(msg)

    user_id, username = get_user_data(msg)
    markup = types.InlineKeyboardMarkup(1)
    markup.add(cancel)
    bot.send_message(user_id, 'Введи название категории', reply_markup=markup)
    bot.register_next_step_handler(msg, __add_category)


def get_recipes(msg, category):
    markup = types.InlineKeyboardMarkup(2)
    user_id, username = get_user_data(msg)
    response = book(user_id, username).get_recipes_titles(category)
    add_recipe = types.InlineKeyboardButton(text='----ДОБАВИТЬ РЕЦЕПТ----',
                                            callback_data='add_recipe' + ':' + category)
    if response.status:
        for recipe_title in response.body:
            markup.add(types.InlineKeyboardButton(text=recipe_title, callback_data='get_recipe' + ':'
                                                                                   + category + ':' + recipe_title))
        markup.add(add_recipe, go_home)
        bot.send_message(user_id, f'Рецпты в категории "{category}"', reply_markup=markup)
    else:
        markup.add(add_recipe, go_home)
        bot.send_message(user_id, response.body, reply_markup=markup)


def get_recipe(msg, category, title):
    user_id, username = get_user_data(msg)
    response = book(user_id, username).get_recipe(category, title)
    markup = types.InlineKeyboardMarkup(2)
    go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_recipes_titles' + ':' + category)
    markup.add(go_back, go_home)
    bot.send_message(user_id, f'*{title}*', parse_mode='Markdown')
    bot.send_message(user_id, response.body, reply_markup=markup)


def add_recipe(msg, category):
    def __add_recipe_title(msg, category):
        user_id, username = get_user_data(msg)
        title = msg.text
        bot.send_message(user_id, 'Введи текст рецепта')
        bot.register_next_step_handler(msg, __add_recipe_body, category, title)

    def __add_recipe_body(msg, category, title):
        user_id, username = get_user_data(msg)
        response = book(user_id, username).add_recipe(category, title, msg.text)
        markup = types.InlineKeyboardMarkup(2)
        go_back = types.InlineKeyboardButton(text='----НАЗАД----', callback_data='get_recipes_titles' + ':' + category)
        markup.add(go_back, go_home)
        bot.send_message(user_id, response.body, reply_markup=markup)

    user_id, username = get_user_data(msg)
    markup = types.InlineKeyboardMarkup(1)
    markup.add(cancel)
    bot.send_message(user_id, 'Введи название рецепта', reply_markup=markup)
    bot.register_next_step_handler(msg, __add_recipe_title, category)


@bot.message_handler(commands=['start'])
def home(msg):
    markup = types.InlineKeyboardMarkup(2)
    get_categories = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='get_categories')
    add_category = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
    markup.add(get_categories, add_category)
    bot.send_message(msg.chat.id, text="Привет. Я твоя книга рецептов. Выбери действие:", reply_markup=markup)


@bot.callback_query_handler(lambda call: True)
def routes(call):
    print(call.data)
    msg = call.message
    command = call.data.split(':')[0]

    if command == 'go_home':
        home(msg)

    elif command == 'get_categories':
        get_categories(msg)

    elif command == 'add_category':
        add_category(msg)

    elif command == 'get_recipes_titles':
        category = call.data.split(':')[1]
        get_recipes(msg, category)

    elif command == 'get_recipe':
        category = call.data.split(':')[1]
        recipe_title = call.data.split(':')[2]
        get_recipe(msg, category, recipe_title)

    elif command == 'add_recipe':
        category = call.data.split(':')[1]
        add_recipe(msg, category)

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)


if __name__ == '__main__':
    bot.polling(none_stop=True)
