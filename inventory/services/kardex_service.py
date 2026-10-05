"""
Consulta del kárdex de un producto en una bodega — fuente única para la
pantalla (KardexBodegaAPIView) y el export Excel (reporting_data.get_kardex),
para que ambos no puedan discrepar en el saldo.

RNF-03 · TEX-22: todo el cálculo lo hace la base de datos, no Python fila a fila:
  - saldo inicial: un solo SUM(CASE ...) sobre los movimientos previos al rango;
  - saldo corrido: SUM(...) OVER (ORDER BY fecha, id ROWS UNBOUNDED PRECEDING).
    SQL Server evalúa la ventana ANTES de OFFSET/FETCH, así que cada página trae
    su saldo correcto leyendo solo sus filas: el costo por petición no crece con
    el historial de la bodega (índices idx_mov_destino_fecha_incl /
    idx_mov_origen_fecha_incl, V2/V4).

No se usa MovimientoInventario.saldo_resultante: es una foto del stock por lote
al momento del movimiento (una transferencia guarda un solo lado, el despacho
guarda 0 y las ediciones no recalculan los posteriores), no un saldo de kárdex.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Case, DecimalField, F, IntegerField, Max, Q, Sum, Value, When, Window
from django.db.models.expressions import RowRange
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from gestion.models import Bodega
from inventory.models import MovimientoInventario

_DECIMAL: "DecimalField[Decimal, Decimal]" = DecimalField(max_digits=12, decimal_places=3)
_CERO = Value(Decimal('0'), output_field=_DECIMAL)

TIPOS_VALIDOS = ('entrada', 'salida')


class FiltroKardexInvalido(ValueError):
    """Filtro de kárdex mal formado (fecha o tipo). Las vistas lo traducen a 400
    con este mensaje; es subclase de ValueError por compatibilidad."""


def _a_fecha(valor, campo):
    """Acepta date o 'YYYY-MM-DD'; vacío -> None; inválido -> ValueError."""
    if valor in (None, ''):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        # parse_date devuelve None si no calza el formato, pero LANZA ValueError
        # si lo calza con una fecha imposible (p. ej. mes 13).
        fecha = parse_date(str(valor))
    except ValueError:
        fecha = None
    if fecha is None:
        raise FiltroKardexInvalido(f"{campo} debe tener formato YYYY-MM-DD.")
    return fecha


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


class KardexService:
    """
    Movimientos de una bodega (opcionalmente de un producto) con entrada,
    salida y — si hay producto — saldo corrido. Sin producto no hay saldo:
    sumar cantidades de productos distintos no tiene sentido físico.
    """

    def __init__(self, bodega_id, producto_id=None, fecha_inicio=None, fecha_fin=None,
                 proveedor_id=None, lote_id=None, lote_codigo=None, tipo=None):
        self.bodega_id = int(bodega_id)
        self.producto_id = int(producto_id) if producto_id not in (None, '', '0', 0) else None
        self.fecha_inicio = _a_fecha(fecha_inicio, 'fecha_inicio')
        self.fecha_fin = _a_fecha(fecha_fin, 'fecha_fin')
        self.proveedor_id = proveedor_id or None
        self.lote_id = lote_id or None
        self.lote_codigo = lote_codigo or None
        if tipo not in (None, '', 'all') and tipo not in TIPOS_VALIDOS:
            raise FiltroKardexInvalido("tipo debe ser 'entrada' o 'salida'.")
        self.tipo = tipo if tipo in TIPOS_VALIDOS else None

    # --- piezas de la consulta ---
    def _es_entrada(self):
        return Q(bodega_destino_id=self.bodega_id)

    def _cantidad_firmada(self):
        return Case(
            When(self._es_entrada(), then=F('cantidad')),
            default=-F('cantidad'),
            output_field=_DECIMAL,
        )

    def _base(self):
        """Movimientos de la bodega sin filtro de fechas (comparten saldo inicial y rango)."""
        filtro = Q(bodega_origen_id=self.bodega_id) | Q(bodega_destino_id=self.bodega_id)
        if self.producto_id:
            filtro &= Q(producto_id=self.producto_id)
        if self.proveedor_id:
            filtro &= Q(proveedor_id=self.proveedor_id)
        if self.lote_id:
            filtro &= Q(lote_id=self.lote_id)
        if self.lote_codigo:
            filtro &= Q(lote__codigo_lote=self.lote_codigo)
        return MovimientoInventario.objects.filter(filtro)

    # --- API pública ---
    def saldo_inicial(self):
        """Saldo acumulado antes de fecha_inicio (0 si no hay fecha); None sin producto.
        Se calcula una sola vez por instancia: lo usan las filas y la respuesta."""
        if not hasattr(self, '_saldo_inicial'):
            self._saldo_inicial = self._calcular_saldo_inicial()
        return self._saldo_inicial

    def _calcular_saldo_inicial(self):
        if not self.producto_id:
            return None
        if not self.fecha_inicio:
            return Decimal('0')
        return self._base().filter(fecha__lt=_inicio_del_dia(self.fecha_inicio)).aggregate(
            total=Coalesce(Sum(self._cantidad_firmada()), _CERO)
        )['total']

    def movimientos(self):
        """
        QuerySet de dicts en orden cronológico (fecha, id). Paginable con slice:
        el saldo corrido se calcula sobre todo el rango antes del OFFSET.
        Cada 'saldo' ya incluye saldo_inicial().
        """
        qs = self._base()
        if self.fecha_inicio:
            qs = qs.filter(fecha__gte=_inicio_del_dia(self.fecha_inicio))
        if self.fecha_fin:
            # Límite exclusivo del día siguiente: incluye todo fecha_fin y es sargable.
            qs = qs.filter(fecha__lt=_inicio_del_dia(self.fecha_fin + timedelta(days=1)))

        orden = [F('fecha').asc(), F('id').asc()]
        anotaciones = {
            'entrada': Case(When(self._es_entrada(), then=F('cantidad')), default=_CERO, output_field=_DECIMAL),
            'salida': Case(When(self._es_entrada(), then=_CERO), default=F('cantidad'), output_field=_DECIMAL),
        }
        if self.producto_id:
            anotaciones['saldo_rango'] = Window(
                expression=Sum(self._cantidad_firmada()),
                order_by=orden,
                frame=RowRange(start=None, end=0),
            )
        if self.tipo:
            # El filtro por tipo debe aplicarse DESPUÉS de la ventana, o el saldo
            # ignoraría los movimientos ocultos. Filtrar sobre una expresión de
            # ventana hace que Django envuelva la consulta (QUALIFY emulado con
            # subconsulta; mssql-django lo soporta), así que la dirección se
            # expresa como ventana de una sola fila (partición por id).
            anotaciones['direccion'] = Window(
                expression=Max(Case(When(self._es_entrada(), then=Value(1)), default=Value(-1),
                                    output_field=IntegerField())),
                partition_by=[F('id')],
            )

        qs = qs.annotate(**anotaciones)
        if self.tipo:
            qs = qs.filter(direccion=1 if self.tipo == 'entrada' else -1)

        campos = [
            'id', 'fecha', 'tipo_movimiento', 'documento_ref', 'cantidad', 'editado',
            'entrada', 'salida', 'producto_id',
        ]
        if self.producto_id:
            campos.append('saldo_rango')
        qs = qs.values(
            *campos,
            codigo_producto=F('producto__codigo'),
            descripcion_producto=F('producto__descripcion'),
            bodega_origen_nombre=F('bodega_origen__nombre'),
            bodega_destino_nombre=F('bodega_destino__nombre'),
            proveedor_nombre=F('proveedor__nombre'),
            lote_codigo=F('lote__codigo_lote'),
            usuario_username=F('usuario__username'),
            usuario_nombre=F('usuario__first_name'),
            usuario_apellido=F('usuario__last_name'),
        ).order_by(*orden)
        return _ConSaldo(qs, self.saldo_inicial()) if self.producto_id else qs


def _filtro_de_corte(valor):
    """Fecha 'YYYY-MM-DD' -> hasta el final de ese día local; fecha con hora
    (ISO 8601) -> hasta ese instante, inclusive. Inválida -> FiltroKardexInvalido."""
    texto = str(valor or '').strip()
    if 'T' in texto or ':' in texto:
        try:
            instante = parse_datetime(texto)
        except ValueError:
            instante = None
        if instante is None:
            raise FiltroKardexInvalido("fecha_corte debe tener formato YYYY-MM-DD o ISO 8601.")
        if timezone.is_naive(instante):
            instante = timezone.make_aware(instante)
        return Q(fecha__lte=instante)
    dia = _a_fecha(texto, 'fecha_corte')
    if dia is None:
        raise FiltroKardexInvalido("fecha_corte es requerida.")
    return Q(fecha__lt=_inicio_del_dia(dia + timedelta(days=1)))


def stock_a_fecha(producto_id, fecha_corte, bodegas=None, bodega_id=None, sede_id=None):
    """Saldo de un producto por bodega a una fecha de corte, calculado en SQL
    (entradas menos salidas por bodega) con el mismo criterio que el kárdex:
    entra en bodega_destino y sale de bodega_origen.

    `bodegas` acota a las bodegas que el usuario ve (None = todas): la
    contraparte de una transferencia hacia una bodega ajena no aparece.
    Tres consultas, sin importar cuántos movimientos haya.
    """
    base = MovimientoInventario.objects.filter(_filtro_de_corte(fecha_corte), producto_id=producto_id)

    def _por_bodega(campo):
        qs = base.filter(**{f'{campo}__isnull': False})
        if bodegas is not None:
            qs = qs.filter(**{f'{campo}__in': bodegas})
        if bodega_id:
            qs = qs.filter(**{f'{campo}_id': bodega_id})
        if sede_id:
            qs = qs.filter(**{f'{campo}__sede_id': sede_id})
        return dict(qs.order_by().values_list(f'{campo}_id').annotate(total=Sum('cantidad')))

    saldos = _por_bodega('bodega_destino')
    for bodega, salida in _por_bodega('bodega_origen').items():
        saldos[bodega] = saldos.get(bodega, Decimal('0')) - salida

    con_saldo = {b: s for b, s in saldos.items() if s != 0}
    filas = Bodega.objects.filter(pk__in=con_saldo).select_related('sede').order_by('sede__nombre', 'nombre')
    return [
        {'bodega_id': b.id, 'bodega': b.nombre, 'sede': b.sede.nombre if b.sede_id else None,
         'stock_calculado': con_saldo[b.id]}
        for b in filas
    ]


class _ConSaldo:
    """
    Envoltura mínima de un QuerySet de values() que suma el saldo inicial al
    saldo del rango al materializar cada fila. Soporta len(), iteración y slice
    (lo que usa el paginador de DRF), manteniendo la paginación en la base.
    """

    def __init__(self, qs, saldo_inicial):
        self._qs = qs
        self._saldo_inicial = saldo_inicial

    def _fila(self, fila):
        fila['saldo'] = self._saldo_inicial + fila.pop('saldo_rango')
        return fila

    def __iter__(self):
        return (self._fila(f) for f in self._qs)

    def __len__(self):
        return self._qs.count()

    def count(self):
        return self._qs.count()

    def __getitem__(self, indice):
        if isinstance(indice, slice):
            return [self._fila(f) for f in self._qs[indice]]
        return self._fila(self._qs[indice])
