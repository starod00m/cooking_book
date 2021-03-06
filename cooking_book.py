# -*- coding: utf-8 -*-

from configparser import ConfigParser
import json
import logging
from dataclasses import dataclass
from typing import Any

'''Читаем env.ini'''
config = ConfigParser()
config.read('env.ini')
BOOKS = config['DATA']['BOOKS']


@dataclass
class Response:
    status: bool
    body: Any = ''


CATEGORY_NOT_EXIST = Response(False, 'Такой категории не существует')
RECIPE_NOT_EXIST = Response(False, 'Рецепта с таким названием не существует')


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

    @staticmethod
    def _already_exist(_object, name):
        return Response(False, f'{_object} названием "{name}" уже существует')

    def _check_recipe_not_existing(self, category, title):
        if category not in self.book:
            return CATEGORY_NOT_EXIST
        elif title not in self.book[category]:
            return RECIPE_NOT_EXIST
        else:
            return Response(True)


class Categories(CookingBook):

    def add(self, category: str) -> Response:
        if category not in self.book:
            self.book[category] = {}
            self._write_book(self.book)
            logging.info(f'create category {category}')
            return Response(True, f'Категория "{category}" создана')
        else:
            logging.error(f'cannot create category {category}')
            return self._already_exist('Категория', category)

    def get(self) -> Response:
        categories = [category for category in self.book]
        logging.info(f'get list of categories {categories}')
        if len(categories) != 0:
            return Response(True, sorted(categories))
        else:
            return Response(False, 'Категорий нет')

    def delete(self, category: str) -> Response:
        try:
            self.book.pop(category)
            self._write_book(self.book)
            logging.info(f'del category {category}')
            return Response(True, f'Категория "{category}" удалена')
        except KeyError:
            logging.exception(f'cannot del category {category}')
            return CATEGORY_NOT_EXIST

    def rename(self, old_name, new_name) -> Response:
        if old_name in self.book:
            if new_name not in self.book:
                old_category = self.book.pop(old_name)
                self.book[new_name] = old_category
                self._write_book(self.book)
                logging.info(f'rename category {old_name} to {new_name}')
                return Response(True, f'Категория "{old_name}" переименована в "{new_name}"')
            else:
                logging.error(f'cannot rename category {old_name} to {new_name}.{new_name} exists ')
                return self._already_exist('Категория', new_name)
        else:
            logging.error(f'cannot rename category {old_name} to {new_name}.{old_name} exists ')
            return self._already_exist('Категория', old_name)


class Recipes(CookingBook):

    def add(self, category, title, text) -> Response:
        if title not in self.book[category]:
            self.book[category][title] = text
            self._write_book(self.book)
            logging.info(f'add recipe {title} to category {category}')
            return Response(True, f'Рецепт "{title}" добавлен')
        else:
            return self._already_exist('Рецепт', title)

    def get(self, category, title) -> Response:
        try:
            recipe = self.book[category][title]
            logging.info(f'get recipe {title} from category {category}')
            return Response(True, recipe)
        except KeyError:
            logging.exception(f'cannot get recipe {title} from category {category}')
            return RECIPE_NOT_EXIST

    def get_all(self) -> Response:
        recipes = list()
        for category in self.book:
            for recipe in self.book[category]:
                recipes.append(f'{recipe} ("{category}")')
        return Response(True, recipes)

    def get_titles(self, category) -> Response:
        try:
            recipes = [title for title in self.book[category]]
            logging.info(f'get list of recipes {recipes}')
            if len(recipes) != 0:
                return Response(True, sorted(recipes))
            else:
                return Response(False, f'В категории "{category}" пока нет рецептов')
        except KeyError:
            logging.exception(f'cannot get recipes from category {category}')
            return CATEGORY_NOT_EXIST

    def rename(self, category, old_recipe_title, new_recipe_title) -> Response:
        check_result = self._check_recipe_not_existing(category, old_recipe_title)
        if check_result.status:
            if new_recipe_title in self.book[category]:
                return self._already_exist('Рецепт', new_recipe_title)
            else:
                old_recipe = self.book[category].pop(old_recipe_title)
                self.book[category][new_recipe_title] = old_recipe
                self._write_book(self.book)
                return Response(True, f'Рецепт "{old_recipe_title}" переименован в "{new_recipe_title}"')
        else:
            return check_result

    def delete(self, category, title) -> Response:
        check_result = self._check_recipe_not_existing(category, title)
        if check_result.status:
            del self.book[category][title]
            self._write_book(self.book)
            return Response(True, f'Рецепт {title} удалён')
        else:
            return check_result

    def edit(self, category, title, new_recipe) -> Response:
        check_result = self._check_recipe_not_existing(category, title)
        if check_result.status:
            self.book[category][title] = new_recipe
            self._write_book(self.book)
            return Response(True, f'Рецепт "{title}" успешно отредактирован')
        else:
            return check_result
