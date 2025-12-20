from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class DynamicPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data, message=None):
        return Response({
            "status": True,   # keeping consistent with your success_response format
            "pagination": {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "data": data,
            "message": message,
        })


class PaginationMixin:
    pagination_class = DynamicPageNumberPagination
    paginator = None  

    def paginate_queryset(self, queryset, request, view=None):
        if self.paginator is None:
            self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data, message=None):
        assert self.paginator is not None, "paginate_queryset() must be called first"
        return self.paginator.get_paginated_response(data, message=message)