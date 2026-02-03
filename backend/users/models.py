from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator()

    email = models.EmailField(
        verbose_name='Email',
        max_length=settings.EMAIL_FIELD_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=settings.FIRST_NAME_FIELD_LENGTH,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=settings.LAST_NAME_FIELD_LENGTH,
    )
    username = models.CharField(
        verbose_name='Имя пользователя',
        max_length=settings.USERNAME_FIELD_LENGTH,
        validators=[username_validator],
        unique=True,
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['username']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на самого себя')
