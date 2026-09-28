from rest_framework.pagination import PageNumberPagination


class PaginacionAcotada(PageNumberPagination):
    """
    Paginación de listados de movimientos (kárdex y /inventory/movimientos/).
    50 filas por defecto — igual que el PAGE_SIZE global —; el cliente elige
    su tamaño con page_size, con tope de 500 para no traer el historial entero
    de una bodega en una sola petición (RNF-03).
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500
