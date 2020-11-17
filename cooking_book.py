# -*- coding: utf-8 -*-

from configparser import ConfigParser
import json
import logging
from collections import namedtuple

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
BOOKS = config['DATA']['BOOKS']

response = namedtuple('response', ['status', 'body'])
CATEGORY_NOT_EXIST = response(False, 'Такой категории не существует')
RECIPE_NOT_EXIST = response(False, 'Рецепта с таким названием не существует')


class CookingBook:

    def __init__(self, user_id, username):
        self.user_id = str(user_id)
        self.username = username
        self.path_to_book = BOOKS + self.user_id + '_' + self.username + '.json'
        self.book = self._get_book(self.path_to_book)
        logging.basicConfig(stream=open(f'logs/{self.user_id}_{self.username}.log', 'a', encoding='utf-8'),
                            format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    def create_book(self):
        self._write_book(self._get_book(self.path_to_book))

    @staticmethod
    def _get_book(path_to_book):
        try:
            with open(path_to_book, encoding='utf-8') as bf:
                book = json.load(bf)
            return book['book']
        except FileNotFoundError:
            return {}

    @staticmethod
    def _get_userfile(path_to_book):
        try:
            with open(path_to_book, encoding='utf-8') as bf:
                userfile = json.load(bf)
            return userfile
        except FileNotFoundError:
            return {"book": {}, "settings": {}}

    def _write_book(self, book):
        userfile = self._get_userfile(self.path_to_book)
        userfile['book'] = book
        with open(self.path_to_book, 'w', encoding='utf-8') as bf:
            json.dump(userfile, bf, indent=4, ensure_ascii=False)
            return None

    def _already_exist(self, object, name):
        return response(False, f'{object} названием {name} уже существует')


class Categories(CookingBook):

    def add(self, category: str) -> namedtuple:
        if category not in self.book:
            self.book[category] = {}
            self._write_book(self.book)
            logging.info(f'create category {category}')
            return response(True, f'Категория "{category}" создана')
        else:
            logging.error(f'cannot create category {category}')
            return self._already_exist('Категория', category)

    def get(self) -> namedtuple:
        categories = [category for category in self.book]
        logging.info(f'get list of categories {categories}')
        if len(categories) != 0:
            return response(True, sorted(categories))
        else:
            return response(False, 'Категорий нет')

    def delete(self, category: str) -> namedtuple:
        try:
            self.book.pop(category)
            self._write_book(self.book)
            logging.info(f'del category {category}')
            return response(True, f'Категория "{category}" удалена')
        except KeyError:
            logging.exception(f'cannot del category {category}')
            return CATEGORY_NOT_EXIST

    def rename(self, old_name, new_name) -> namedtuple:
        if old_name in self.book:
            if new_name not in self.book:
                old_category = self.book.pop(old_name)
                self.book[new_name] = old_category
                self._write_book(self.book)
                logging.info(f'rename category {old_name} to {new_name}')
                return response(True, f'Категория "{old_name}" переименована в "{new_name}"')
            else:
                logging.error(f'cannot rename category {old_name} to {new_name}.{new_name} exists ')
                return self._already_exist('Категория', new_name)
        else:
            logging.error(f'cannot rename category {old_name} to {new_name}.{old_name} exists ')
            return self._already_exist('Категория', old_name)


class Recipes(CookingBook):

    def add(self, category, title, text) -> namedtuple:
        if title not in self.book[category]:
            self.book[category][title] = text
            self._write_book(self.book)
            logging.info(f'add recipe {title} to category {category}')
            return response(True, f'Рецепт "{title}" добавлен')
        else:
            return self._already_exist('Рецепт', title)

    def get(self, category, title) -> namedtuple:
        try:
            recipe = self.book[category][title]
            logging.info(f'get recipe {title} from category {category}')
            return response(True, recipe)
        except KeyError:
            logging.exception(f'cannot get recipe {title} from category {category}')
            return RECIPE_NOT_EXIST

    def get_titles(self, category) -> namedtuple:
        try:
            recipes = [title for title in self.book[category]]
            logging.info(f'get list of recipes {recipes}')
            if len(recipes) != 0:
                return response(True, sorted(recipes))
            else:
                return response(False, 'Тут пока нет рецептов')
        except KeyError:
            logging.exception(f'cannot get recipes from category {category}')
            return CATEGORY_NOT_EXIST

    def rename(self, category, old_recpe_title, new_recipe_title) -> namedtuple:
        if category not in self.book:
            return CATEGORY_NOT_EXIST
        elif old_recpe_title not in self.book[category]:
            return RECIPE_NOT_EXIST
        elif new_recipe_title in self.book[category]:
            return self._already_exist('Рецепт', new_recipe_title)
        else:
            old_recipe = self.book[category].pop(old_recpe_title)
            self.book[category][new_recipe_title] = old_recipe
            self._write_book(self.book)
            return response(True, f'Рецепт "{old_recpe_title}" переименован в "{new_recipe_title}"')

    def delete(self, category, title):
        if category not in self.book:
            return CATEGORY_NOT_EXIST
        elif title not in self.book[category]:
            return RECIPE_NOT_EXIST
        else:
            del self.book[category][title]
            self._write_book(self.book)
            return response(True, f'Рецепт {title} удалён')


print(Recipes(151265204, 'starod00m').delete('Супы', 'F{F{F123{F{{F{F{'))
