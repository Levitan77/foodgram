# Foodgram
[![Main foodgram workflow](https://github.com/Levitan77/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/Levitan77/foodgram/actions/workflows/main.yml)

## Описание

Проект foodgram представляет сайт для взаимодействия между поварами
Пользователи могут обмениваться рецептами

Проект состоит из четырех docker контейнеров: бэкенд, фронтенд, база данных, nginx

Работающий проект можно исследовать [тут](https://foodgram2026.ddns.net)
Документацию API можно посмотреть [тут](https://foodgram2026.ddns.net/api/docs/)

### Основной функционал

- Пользователи с возможностью авторизации
- Управление своими рецептами
- Управление избранным, корзиной, подписками
- Просмотр чужих рецептов
- Поддержка изображений

## Cтек использованных технологий

- Python 3.10
- Django 3.2.3
- DRF 3.12.4
- JWT
- SQLite/PostgreSQL
- Node.js 18
- React 17.0.2

## Установка

Для установки и запуска проекта выполните следующие действия:

### 1. Создайте на сервере папку foodgram/infra и добавьте в нее файл docker-compose.production.yml
```bash
mkdir foodgram
cd foodgram/
mkdir infra
cd infra/
```

### 2. Создайте в папке и заполните файл .env

```
POSTGRES_DB= Название базы данных
POSTGRES_USER= Имя пользователя базы данных
POSTGRES_PASSWORD= Пароль пользователя базы данных
DB_HOST=db
DB_PORT=5432
SECRET_KEY= Секретный ключ джанго
DEBUG= Режим работы джанго true или false
ALLOWED_HOSTS=localhost 127.0.0.1 или любой другой список хостов через пробел
```

### 3. Запустите проект
```bash
docker compose -f docker-compose.production.yml up -d
```

### 4. Выполните миграции и сбор статики в контейнерах, загрузка ингредиентов
```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
sudo docker compose -f docker-compose.production.yml exec backend python manage.py load_ingredients
```

### 5. Информация
Документацию Api можно посмотреть по адресу http://127.0.0.1/api/docs/

## Разработка

Для внесения изменений в проект выполните следующие действия:

### 1. Форкните репозиторий на свой аккаунт

### 2. В настройках репозитория заполните Action Secrets

DOCKER_USERNAME - логин пользователя dockerhub
DOCKER_PASSWORD - пароль пользователя dockerhub
HOST - адрес удаленного сервера
SSH_KEY - приватный ssh ключ для подключения к серверу
SSH_PASSPHRASE - парольная фраза для подключения к серверу
USER - имя пользователя на сервере
TELEGRAM_TOKEN - токен бота в телеграм для отправки сообщения об успешном деплое
TELEGRAM_TO - id чата бота с разработчиком

### 3. Добавьте свои наработки в файлы проекта

### 4. Создайте коммит и отправьте его на Github

В случае, если коммит выполнен в ветке main, запустится полный цикл выпуска проекта в продакшен
В противном случае github workflow выполнит только тестирование проекта по pep8 и по написанным тестам

## Автор

[Levitan77](https://github.com/Levitan77)