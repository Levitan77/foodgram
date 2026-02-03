from django.urls import include, path
from rest_framework import routers

from api.views import (IngredientViewSet, RecipeViewSet, ShortLinkRedirectView,
                       TagViewSet, UserViewSet)

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path(
        's/<str:code>/',
        ShortLinkRedirectView.as_view(),
        name='short-link'
    ),
]
