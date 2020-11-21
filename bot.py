import time
from collections import namedtuple
from configparser import ConfigParser
from cooking_book import Categories as book_categories
from cooking_book import CookingBook as book
from cooking_book import Recipes as book_recipes


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

    def home(self):
        get_categories_button = self.button(text='Выбрать категорию', callback_data='get_categories')
        add_category_button = self.button(text='Добавить категорию', callback_data='add_category')
        get_all_recipes_button = self.button(text='Все рецпты', callback_data='get_all_recipes')
        self.markup.add(get_categories_button, add_category_button)
        self.markup.add(get_all_recipes_button)
        bot.send_message(self.id, text="Привет. Я твоя книга рецептов. Выбери действие:",
                         reply_markup=self.markup)

    def get_user_data(self, call=None):
        user_data = namedtuple('user_data', ['user_id', 'username', 'text', 'call_id', 'message'])
        call = self.call if call is None else call
        try:
            return user_data(call.from_user.id, call.from_user.username, call.message.text, call.id, call.message)
        except AttributeError:
            message = call
            return user_data(message.chat.id, message.chat.username, message.text, None, message)

    def send_notification(self, response, timeout: float = 1):
        message = bot.send_message(self.id, f'_{response.body}_', parse_mode='Markdown')
        time.sleep(timeout)
        bot.delete_message(message.chat.id, message.message_id)

    @staticmethod
    def button(text, callback_data):
        return types.InlineKeyboardButton(text=text, callback_data=callback_data)


class Categories(BaseBot):

    def get(self):
        response = book_categories(self.id, self.username).get()
        if response.status:
            for category in response.body:
                self.markup.add(
                    self.button(text=category, callback_data='get_from_category' + ':' + category))
            self.markup.add(go_home)
            bot.send_message(self.id, text="*Ваши категории*", reply_markup=self.markup, parse_mode='Markdown')
        else:
            self.send_notification(response, timeout=0.8)
            self.home()

    def add(self):
        def __add(message):
            _user_data = self.get_user_data(message)
            response = book_categories(_user_data.user_id, _user_data.username).add(_user_data.text)
            self.send_notification(response, timeout=1)
            self.home()

        bot.send_message(self.id, 'Введи название категории')
        bot.register_next_step_handler(self.message, __add)

    def rename(self):
        def __rename(message, _category):
            _user_data = self.get_user_data(message)
            response = book_categories(_user_data.user_id, _user_data.username).rename(_category, _user_data.text)
            _category = _user_data.text if response.status else _category
            go_back = self.button(text='----назад----',
                                  callback_data='get_from_category' + ':' + _category)
            self.markup.add(go_back, go_home)
            bot.send_message(_user_data.user_id, response.body, reply_markup=self.markup)

        bot.send_message(self.id, 'Введите новое имя категории')
        bot.register_next_step_handler(self.message, __rename, self.category)

    def confirm_delete(self):
        yes = self.button(text='----да----', callback_data='delete_confirmed' + ':' + self.category)
        no = self.button(text='----нет----', callback_data='get_from_category' + ':' + self.category)
        self.markup.add(no, yes)
        bot.send_message(self.id, text=f'Вы уверены, что хотите удалить категорию "{self.category}"?',
                         reply_markup=self.markup)

    def delete(self):
        response = book_categories(self.id, self.username).delete(self.category)
        self.send_notification(response)
        routes(self.call, command='get_categories')


class Recipes(BaseBot):

    def get_from_category(self):
        response = book_recipes(self.id, self.username).get_titles(self.category)
        add_recipe_button = self.button(text='----добавить рецепт----',
                                        callback_data='add_recipe' + ':' + self.category)
        go_back = self.button(text='----назад----', callback_data='get_categories')
        rename_category_button = self.button(text='----переименовать----    ',
                                             callback_data='rename_category' + ':' + self.category)
        delete_category_button = self.button(text='----удалить----',
                                             callback_data='delete_category' + ':' + self.category)

        if response.status:
            for recipe_title in response.body:
                self.markup.add(self.button(
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
            self.markup.add(self.button(recipe,
                                        callback_data='get_recipe' + ':' + category + ':' + recipe_title))
        self.markup.add(go_home)
        bot.send_message(self.id, text='*Все рецепты*', parse_mode='Markdown', reply_markup=self.markup)

    def get(self):
        response = book_recipes(self.id, self.username).get(self.category, self.recipe_title)
        go_back = self.button(text='----назад----',
                              callback_data='get_from_category' + ':' + self.category)
        rename = self.button(text='----переименовать----',
                             callback_data='rename_recipe' + ':' + self.category + ':' + self.recipe_title)
        edit = self.button(text='----редактировать----',
                           callback_data='edit_recipe' + ':' + self.category + ':' + self.recipe_title)
        delete = self.button(text='----удалить----',
                             callback_data='delete_recipe' + ':' + self.category + ':' + self.recipe_title)
        self.markup.add(rename, delete)
        self.markup.add(edit)
        self.markup.add(go_back, go_home)
        bot.send_message(self.id, f'*{self.recipe_title}*\n\n{response.body}',
                         reply_markup=self.markup, parse_mode='Markdown')

    def add(self):
        def __add_recipe_title(_call):
            _user_data = self.get_user_data(_call)
            title = _user_data.text
            bot.send_message(self.id, 'Введи текст рецепта')
            bot.register_next_step_handler(_user_data.message, __add_recipe_body, title)

        def __add_recipe_body(_call, title):
            _user_data = self.get_user_data(_call)
            response = book_recipes(self.id, self.username).add(self.category, title, _user_data.text)
            self.send_notification(response)
            routes(_call, command='get_from_category', category=self.category)

        bot.send_message(self.id, 'Введите название рецепта')
        bot.register_next_step_handler(self.message, __add_recipe_title)

    def rename(self):
        def __rename_recipe(message):
            _user_data = self.get_user_data(message)
            new_title = _user_data.text
            _response = book_recipes(self.id, self.username).rename(self.category, self.recipe_title, new_title)
            recipe = new_title if _response.status else self.recipe_title
            self.send_notification(_response)
            routes(message, command='get_recipe', category=self.category, recipe=recipe)

        bot.send_message(self.id, 'Введите новое имя рецепта')
        bot.register_next_step_handler(self.message, __rename_recipe)

    def edit(self):
        def __edit(message):
            user_data = self.get_user_data(message)
            response = book_recipes(self.id, self.username).edit(self.category, self.recipe_title, user_data.text)
            self.send_notification(response)
            routes(message, command='get_recipe', category=self.category, recipe=self.recipe_title)

        recipe = book_recipes(self.id, self.username).get(self.category, self.recipe_title).body
        bot.send_message(self.id, text=recipe)
        bot.send_message(self.id, text='Введите текст рецпета')
        bot.register_next_step_handler(self.message, __edit)

    def delete(self):
        response = book_recipes(self.id, self.username).delete(self.category, self.recipe_title)
        self.send_notification(response)
        routes(self.call, command='get_from_category', category=self.category)

    def confirm_delete(self):
        yes = self.button(text='----да----',
                          callback_data='delete_confirmed' + ':' + self.category + ':' + self.recipe_title)
        no = self.button(text='----нет----',
                         callback_data='get_recipe' + ':' + self.category + ':' + self.recipe_title)
        self.markup.add(no, yes)
        bot.send_message(self.id, text=f'Вы уверены, что хотите удалить рецепт "{self.recipe_title}"?',
                         reply_markup=self.markup)


if __name__ == '__main__':
    import telebot
    from telebot import types
    from telebot.apihelper import ApiTelegramException

    '''Читаем env.ini'''
    config = ConfigParser()
    config.read('env.ini')
    TOKEN = config['AUTH']['TOKEN']

    '''Инициализирум бота'''
    bot = telebot.TeleBot(TOKEN)

    '''Стандартные кнопки'''
    go_home = BaseBot.button(text='----домой----', callback_data='go_home')


    @bot.message_handler(commands=['start'])
    def start(msg):
        user_data = BaseBot(msg).get_user_data()
        book(user_data.user_id, user_data.username).create_book()
        BaseBot(msg).home()


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
            BaseBot(call).home()

        elif command == 'get_categories':
            Categories(call).get()

        elif command == 'add_category':
            Categories(call).add()

        elif command == 'rename_category':
            Categories(call, category).rename()

        elif command == 'delete_category':
            Categories(call, category).confirm_delete()

        elif command == 'delete_confirmed':
            if recipe is not None:
                Recipes(call, category, recipe).delete()
            else:
                Categories(call, category).delete()

        elif command == 'get_from_category':
            Recipes(call, category).get_from_category()

        elif command == 'get_all_recipes':
            Recipes(call).get_all()

        elif command == 'get_recipe':
            Recipes(call, category, recipe).get()

        elif command == 'add_recipe':
            Recipes(call, category).add()

        elif command == 'rename_recipe':
            Recipes(call, category, recipe).rename()

        elif command == 'edit_recipe':
            Recipes(call, category, recipe).edit()

        elif command == 'delete_recipe':
            Recipes(call, category, recipe).confirm_delete()

        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except (ApiTelegramException, AttributeError):
            pass


    bot.polling(none_stop=True)
