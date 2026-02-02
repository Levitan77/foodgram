from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsAuthorPermission
from .serializers import (AvatarSerializer, CustomUserSerializer,
                          FavoriteSerializer, IngredientSerializer,
                          RecipeCreateSerializer, RecipeSerializer,
                          RecipeShortSerializer, ShoppingCartSerializer,
                          SubscriptionRecipesSerializer,
                          SubscriptionSerializer, TagSerializer)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    pagination_class = CustomPageNumberPagination

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated],)
    def me(self, request):
        serializer = CustomUserSerializer(
            request.user,
            context={'request': request},
        )
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=[permissions.IsAuthenticated],)
    def set_avatar(self, request):
        user = request.user

        if request.method == "PUT":
            serializer = AvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.avatar = serializer.validated_data["avatar"]
            user.save()
            avatar_url = user.avatar.url if user.avatar else None
            if avatar_url and not avatar_url.startswith("http"):
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

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
        subscription = user.subscriptions.filter(author=author)
        if request.method == 'POST':
            if subscription.exists():
                return Response(
                    {'errors': 'Вы уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

        if not subscription.exists():
            return Response(
                {'errors': 'Вы еще не подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
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
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    @action(
        detail=True,
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        domain = request.get_host()
        return Response({
            'short-link': f'https://{domain}/s/{recipe.id}'
        })

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, *args, **kwargs):
        recipe = self.get_object()
        user = request.user
        favorite = user.favorites.filter(recipe=recipe)
        if request.method == 'POST':
            if favorite.exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = FavoriteSerializer(
                data={'user': request.user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                RecipeShortSerializer(
                    recipe, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        if not favorite.exists():
            return Response(
                {'errors': 'Рецепта нет в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, *args, **kwargs):
        recipe = self.get_object()
        user = request.user
        shopping_cart = user.shoppingcart.filter(recipe=recipe)
        if request.method == 'POST':
            if shopping_cart.exists():
                return Response(
                    {'errors': 'Рецепт уже в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = ShoppingCartSerializer(
                data={'user': request.user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                RecipeShortSerializer(
                    recipe, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        if not shopping_cart.exists():
            return Response(
                {'errors': 'Рецепта нет в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )
        shopping_cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        shopping_cart = self.get_queryset()
        recipes = Recipe.objects.filter(id__in=shopping_cart.values('id'))
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipes.filter(in_shoppingcart__user=request.user)
        ).values('recipe').values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(
            amount=Sum('amount')
        ).order_by('ingredient__name')

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
