# -*- coding: utf-8 -*-

from configparser import ConfigParser
import json
import logging
from collections import namedtuple

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
BOOKS = config['DATA']['BOOKS']


def _get_book(path_to_book):
    try:
        with open(path_to_book, encoding='utf-8') as bf:
            book = json.load(bf)
            return book
    except FileNotFoundError:
        return {}

class CookingBook:

    def __init__(self, user_id, username):
        self.user_id = str(user_id)
        self.username = username
        self.path_to_book = BOOKS + self.user_id + '_' + self.username + '.json'
        self.book = _get_book(self.path_to_book)
        self.response = namedtuple('response', ['status', 'body'])
        logging.basicConfig(stream=open(f'logs/{self.user_id}_{self.username}.log', 'a', encoding='utf-8'),
                            format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    def __write_book(self, book):
        with open(self.path_to_book, 'w', encoding='utf-8') as bf:
            json.dump(book, bf, indent=4, ensure_ascii=False)
            return None

    '''Categories'''
    def add_category(self, category: str) -> namedtuple:
        if category not in self.book:
            self.book[category] = {}
            self.__write_book(self.book)
            logging.info(f'create category {category}')
            return self.response(True, 'Категория создана')
        else:
            logging.error(f'cannot create category {category}')
            return self.response(False, 'Категория с таким название уже существует')

    def get_categories(self) -> namedtuple:
        categories = [category for category in self.book]
        logging.info(f'get list of categories {categories}')
        if len(categories) != 0:
            return self.response(True, categories)
        else:
            return self.response(False, 'Категорий нет')


    def del_category(self, category: str) -> namedtuple:
        try:
            self.book.pop(category)
            self.__write_book(self.book)
            logging.info(f'del category {category}')
            return self.response(True, 'Категория удалена')
        except KeyError:
            logging.exception(f'cannot del category {category}')
            return self.response(False, 'Такой категории не существует')

    def rename_category(self, old_name, new_name) -> namedtuple:
        if old_name in self.book:
            if new_name not in self.book:
                old_category = self.book.pop(old_name)
                self.book[new_name] = old_category
                self.__write_book(self.book)
                logging.info(f'rename category {old_name} to {new_name}')
                return self.response(True, 'Категория переименована')
            else:
                logging.error(f'cannot rename category {old_name} to {new_name}.{new_name} exists ')
                return self.response(False, f'Категория с именем {new_name} уже существует')
        else:
            logging.error(f'cannot rename category {old_name} to {new_name}.{old_name} exists ')
            return self.response(False, f'Категория с именем {old_name} уже существует')

    '''Recipes'''
    def add_recipe(self, category, title, text) -> namedtuple:
        if title not in self.book[category]:
            self.book[category][title] = text
            self.__write_book(self.book)
            logging.info(f'add recipe {title} to category {category}')
            return self.response(True, 'Рецепт добавлен')
        else:
            return self.response(False, 'Рецепт с таким названием уже существует')

    def get_recipe(self, category, title) -> namedtuple:
        try:
            recipe = self.book[category][title]
            logging.info(f'get recipe {title} from category {category}')
            return self.response(True, recipe)
        except KeyError:
            logging.exception(f'cannot get recipe {title} from category {category}')
            return self.response(False, 'Рецепта с таким названием не существует')

    def get_recipes_titles(self, category) -> namedtuple:
        try:
            recipes = [title for title in self.book[category]]
            logging.info(f'get list of recipes {recipes}')
            if len(recipes) != 0:
                return self.response(True, recipes)
            else:
                return self.response(False, 'Рецпетов в категории нет')
        except KeyError:
            logging.exception(f'cannot get recipes from category {category}')
            return self.response(False, 'Такой категории не существует')
