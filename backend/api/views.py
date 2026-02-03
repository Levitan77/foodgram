from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPageNumberPagination
from api.permissions import IsAuthorPermission
from api.serializers import (AvatarSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeCreateSerializer,
                             RecipeSerializer, ShoppingCartSerializer,
                             SubscriptionRecipesSerializer,
                             SubscriptionSerializer, TagSerializer,
                             UserSerializer)
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    pagination_class = LimitPageNumberPagination

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated],)
    def me(self, request):
        serializer = UserSerializer(
            request.user,
            context={'request': request},
        )
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=[permissions.IsAuthenticated],)
    def set_avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.avatar = serializer.validated_data['avatar']
            user.save()
            avatar_url = user.avatar.url if user.avatar else None
            if avatar_url and not avatar_url.startswith('http'):
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='subscribe',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()
        user = request.user
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        deleted, _ = user.subscriptions.filter(author=author).delete()
        if not deleted:
            return Response(
                {'errors': 'Вы еще не подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request):
        user = request.user
        authors = User.objects.filter(subscribers__user=user)

        page = self.paginate_queryset(authors)
        serializer = SubscriptionRecipesSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny, )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorPermission,
                          permissions.IsAuthenticatedOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeSerializer
        return RecipeCreateSerializer

    @action(
        detail=True,
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_url = request.build_absolute_uri(
            reverse('short-link', args=(recipe.id, ))
        )
        return Response({'short-link': short_url})

    def create_relation(self, request, model_serializer):
        recipe = self.get_object()
        serializer = model_serializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def delete_relation(self, objects):
        recipe = self.get_object()
        deleted, _ = objects.filter(recipe=recipe).delete()
        if not deleted:
            return Response(
                {'errors': 'Рецепт ранее не был добавлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, *args, **kwargs):
        if request.method == 'POST':
            return self.create_relation(request, FavoriteSerializer)
        return self.delete_relation(request.user.favorites)

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, *args, **kwargs):
        if request.method == 'POST':
            return self.create_relation(request, ShoppingCartSerializer)
        return self.delete_relation(request.user.shoppingcarts)

    def create_shopping_file(self, ingredients):
        text = 'Список покупок:\n'
        for ingredient in ingredients:
            name = ingredient.get('name')
            measurement_unit = ingredient.get('measurement_unit')
            amount = ingredient.get('amount')
            text += f'{name} - {amount} {measurement_unit}\n'
        response = HttpResponse(
            text,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )

        return response

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        shopping_cart = self.get_queryset()
        recipes = Recipe.objects.filter(id__in=shopping_cart.values('id'))
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipes.filter(shoppingcarts__user=request.user)
        ).values('recipe').values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(
            amount=Sum('amount')
        ).order_by('ingredient__name')

        file_response = self.create_shopping_file(ingredients)
        return file_response


class ShortLinkRedirectView(View):
    def get(self, request, code):
        get_object_or_404(Recipe, pk=code)
        return redirect('/recipes/{recipe.id}/')
