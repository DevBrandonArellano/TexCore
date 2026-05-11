from rest_framework.pagination import PageNumberPagination

class OptionalPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('no_paginate') == 'true':
            return None
        return super().paginate_queryset(queryset, request, view)
