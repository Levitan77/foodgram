from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class LimitPageNumberPagination(PageNumberPagination):
    page_size = settings.PAGINATION_SIZE
    page_size_query_param = settings.PAGE_SIZE_QUERY_PARAM_NAME
