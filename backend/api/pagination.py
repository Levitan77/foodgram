from rest_framework.pagination import PageNumberPagination

from api.constants import PAGE_SIZE_QUERY_PARAM_NAME, PAGINATION_SIZE


class LimitPageNumberPagination(PageNumberPagination):
    page_size = PAGINATION_SIZE
    page_size_query_param = PAGE_SIZE_QUERY_PARAM_NAME
