import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        file_path = 'data/ingredients.json'

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)
                ingredients = [
                    Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    for item in ingredients_data
                ]
                Ingredient.objects.bulk_create(
                    ingredients
                )
        except FileNotFoundError:
            self.stderr.write('Файл не найден')
