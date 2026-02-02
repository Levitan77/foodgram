import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserCreateSerializer(DjoserUserCreateSerializer):

    class Meta():
        fields = ('email', 'username', 'first_name',
                  'last_name', 'password')

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'email': instance.email,
            'username': instance.username,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True, allow_null=True)

    class Meta(UserSerializer.Meta):
        fields = (
            'id',
            'avatar',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return Subscription.objects.filter(
            user=request.user, author=obj
        ).exists()


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, amount):
        if amount < 1:
            raise serializers.ValidationError(
                'Количество должно быть больше 0'
            )
        return amount


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source='ingredients_in_recipe',
        many=True
    )
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField(required=True, use_url=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'author',
            'image', 'is_favorited', 'is_in_shopping_cart',
            'name', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and user.favorites.filter(
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and user.shoppingcart.filter(
            recipe=obj
        ).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time'
        )

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Нужен хотя бы один тег')
        unique_tags = [tag.id for tag in value]
        if len(unique_tags) != len(set(unique_tags)):
            raise serializers.ValidationError('Теги не должны повторяться')
        return value

    def validate_image(self, value):
        if value is None:
            raise serializers.ValidationError('Нужно изображение')
        return value

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError('Нужен хотя бы один ингредиент')
        unique_ingredients = [ingredient['id'] for ingredient in ingredients]
        if len(unique_ingredients) != len(set(unique_ingredients)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться'
            )
        return ingredients

    def validate_cooking_time(self, cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0'
            )
        return cooking_time

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe_ingredients = []
        for ingredient in ingredients:
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient['id'],
                    amount=ingredient['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        self.validate_ingredients(ingredients)
        self.validate_tags(tags)
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        recipe_ingredients = []
        for ingredient in ingredients:
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=instance,
                    ingredient=ingredient['id'],
                    amount=ingredient['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')


class SubscriptionRecipesSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count',
        )
        read_only_fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'avatar', 'recipes',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            try:
                recipes = recipes[:int(limit)]
            except (ValueError, TypeError):
                pass
        return RecipeShortSerializer(
            recipes, many=True, context={'request': request}
        ).data


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )
        return data

    def to_representation(self, instance):
        return SubscriptionRecipesSerializer(
            instance.author,
            context={'request': self.context.get('request')}
        ).data
