"""
Pruebas de gestion/pagination.py — OptionalPagination.

Extiende PageNumberPagination para permitir desactivar la paginación vía el
query param `no_paginate=true` (usado por exportaciones que necesitan el
dataset completo).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): no_paginate ausente / 'true' / cualquier
  otro valor (paginación normal).
- Caja blanca: rama `return None` vs. delegación a la clase base.
"""
from django.test import TestCase, RequestFactory
from rest_framework.request import Request

from gestion.pagination import OptionalPagination
from gestion.tests.factories import ProductoFactory


class OptionalPaginationTestCase(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.paginator = OptionalPagination()
        for _ in range(3):
            ProductoFactory()
        self.queryset = ProductoFactory._meta.model.objects.all()

    def _drf_request(self, query_string=''):
        django_request = self.rf.get(f'/api/productos/?{query_string}')
        return Request(django_request)

    def test_paginate_dado_no_paginate_true_cuando_paginate_entonces_none(self):
        # Caja blanca: rama `no_paginate == 'true'` -> None (sin paginar)
        request = self._drf_request('no_paginate=true')
        result = self.paginator.paginate_queryset(self.queryset, request)
        self.assertIsNone(result)

    def test_paginate_dado_no_paginate_ausente_cuando_paginate_entonces_pagina(self):
        # EP: parámetro ausente -> delega a PageNumberPagination (pagina normal)
        request = self._drf_request('')
        result = self.paginator.paginate_queryset(self.queryset, request)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_paginate_dado_no_paginate_otro_valor_cuando_paginate_entonces_pagina(self):
        # EP: valor distinto de 'true' (ej. 'false') -> se comporta como paginación normal
        request = self._drf_request('no_paginate=false')
        result = self.paginator.paginate_queryset(self.queryset, request)
        self.assertIsNotNone(result)

    def test_page_size_query_param_y_max_page_size_configurados(self):
        self.assertEqual(self.paginator.page_size_query_param, 'page_size')
        self.assertEqual(self.paginator.max_page_size, 10000)
