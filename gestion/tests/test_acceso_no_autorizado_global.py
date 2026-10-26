"""
Pruebas de acceso no autorizado sobre todas las rutas de la API (RNF-02, OWASP API1 y API2).

La tesis afirma que el 100 % de las funcionalidades requieren autenticación y que la
autorización por objeto (API1) y la autenticación (API2) están mitigadas. Estas pruebas no
eligen endpoints a mano: recorren el resolver de Django, así que una ruta nueva queda
cubierta sin escribir nada.

- Anónimo: cada ruta fuera de la lista blanca pública responde 401/403 a GET y a POST.
- Objeto de otra sede: se crean datos solo en la sede B y, por cada ruta de detalle de un
  ViewSet, un usuario de cada rol acotado a la sede A pide, modifica y borra el objeto ajeno.
  Ninguna respuesta puede ser 2xx, y el objeto debe seguir intacto.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): anónimo / autenticado de otra sede, por cada rol.
- Caja blanca (CB-D): recorrido de todas las rutas del resolver.
"""

import importlib.util
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import PagoCliente
from gestion.permissions import GRUPOS_TODAS_LAS_SEDES
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    ClienteFactory,
    ComponenteMezclaOPFactory,
    ConsumoLoteDetalleFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    DetallePedidoFactory,
    DetallePlanProduccionFactory,
    FormulaColorFactory,
    LineaProduccionFactory,
    LoteProduccionFactory,
    MaquinaFactory,
    OperacionProduccionFactory,
    OrdenProduccionFactory,
    ParoMaquinaFactory,
    PedidoVentaFactory,
    PlanProduccionFactory,
    ProcesoTintoreriaFactory,
    ProductoFactory,
    ProveedorFactory,
    SedeFactory,
    StockBodegaFactory,
)

_ruta = Path(settings.BASE_DIR) / "scripts" / "auditar_permisos_backend.py"
_spec = importlib.util.spec_from_file_location("auditar_permisos_backend", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
auditoria = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditoria)

ROLES = (
    "operario",
    "bodeguero",
    "vendedor",
    "jefe_area",
    "jefe_planta",
    "admin_sede",
    "ejecutivo",
    "admin_sistemas",
    "despacho",
    "empaquetado",
    "tintorero",
)
# Los que ven todas las sedes por diseño (gestion/permissions.py) no entran en la prueba de IDOR.
ROLES_DE_UNA_SEDE = tuple(r for r in ROLES if r not in GRUPOS_TODAS_LAS_SEDES)


def _filas_por_modelo():
    return {m: set(m._default_manager.values_list("pk", flat=True)) for m in apps.get_models()}


def _modelo_de(cls):
    """Modelo de un ViewSet: el de `queryset` o, si solo define `get_queryset()`, el del serializer."""
    queryset = getattr(cls, "queryset", None)
    if queryset is not None:
        return queryset.model
    serializer = getattr(cls, "serializer_class", None)
    return getattr(getattr(serializer, "Meta", None), "model", None)


def _sin_globales(modelo, pks):
    """Quita los ítems de catálogo sin sede: son globales y visibles en todas las sedes por diseño."""
    if pks and any(f.name == "sede" for f in modelo._meta.get_fields()):
        return pks - set(modelo._default_manager.filter(pk__in=pks, sede__isnull=True).values_list("pk", flat=True))
    return pks


class AnonimoEnTodasLasRutasTestCase(TestCase):
    """Cada ruta no pública rechaza al anónimo antes de tocar datos (RNF-02, API2)."""

    def test_rutas_dado_anonimo_cuando_get_o_post_entonces_401_o_403(self):
        client = APIClient()
        aceptadas = []
        for fila in auditoria.auditar():
            if fila["ruta"] in auditoria.RUTAS_PUBLICAS:
                continue
            url = auditoria.url_de_prueba(fila["ruta"])
            for metodo in ("get", "post"):
                codigo = getattr(client, metodo)(url, {}, format="json").status_code
                if codigo not in (401, 403, 405):
                    aceptadas.append(f"{metodo.upper()} {url} → {codigo}")
        self.assertEqual(aceptadas, [])


class ObjetoDeOtraSedeTestCase(TestCase):
    """Ningún rol de la sede A lee, modifica ni borra un objeto de la sede B (API1)."""

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        antes = _filas_por_modelo()
        cls.sede_b = sede = SedeFactory()
        area = AreaFactory(sede=sede)
        bodega = BodegaFactory(sede=sede)
        producto = ProductoFactory(sede=sede)
        cliente = ClienteFactory(sede=sede)
        maquina = MaquinaFactory(area=area)
        ParoMaquinaFactory(maquina=maquina)
        LineaProduccionFactory(area=area)
        orden = OrdenProduccionFactory(
            sede=sede,
            area=area,
            producto_entrada=producto,
            producto_salida=producto,
            bodega_entrada=bodega,
            bodega_salida=bodega,
        )
        lote = LoteProduccionFactory(orden_produccion=orden, maquina=maquina)
        origen = LoteProduccionFactory(orden_produccion=orden, maquina=maquina)
        ConsumoLoteDetalleFactory(lote_produccion=lote, lote_origen=origen)
        StockBodegaFactory(bodega=bodega, producto=producto)
        ProveedorFactory(sede=sede)
        FormulaColorFactory(sede=sede)
        ProcesoTintoreriaFactory(sede=sede)
        ComponenteMezclaOPFactory(orden=orden, producto=producto, bodega=bodega)
        PagoCliente.objects.create(cliente=cliente, monto=Decimal("10.00"), metodo_pago="transferencia", sede=sede)
        corrida = CorridaProduccionFactory(sede=sede, area=area)
        operario_b = CustomUserFactory(sede=sede, area=area, groups=["operario"])
        OperacionProduccionFactory(corrida=corrida, maquina=maquina, operario=operario_b)
        plan = PlanProduccionFactory(sede=sede, supervisor=operario_b)
        DetallePlanProduccionFactory(plan=plan)
        pedido = PedidoVentaFactory(cliente=cliente, sede=sede, vendedor_asignado=operario_b)
        DetallePedidoFactory(pedido_venta=pedido)
        despues = _filas_por_modelo()
        cls.ajenos = {m: _sin_globales(m, despues[m] - antes.get(m, set())) for m in despues}

        cls.sede_a = SedeFactory()
        cls.area_a = AreaFactory(sede=cls.sede_a)

    def _rutas_de_objeto(self):
        """(ruta, métodos, modelo, pk ajeno) por cada ruta de ViewSet sobre un objeto con datos de la sede B.

        Incluye el detalle (`clientes/<p>/`) y las acciones sobre un objeto
        (`pedidos-venta/<p>/anular/`): las dos resuelven el objeto con `get_object()`.
        """
        for ruta, vista in auditoria.rutas():
            if ruta.count("<p>") != 1 or not getattr(vista, "actions", None):
                continue
            modelo = _modelo_de(vista.cls)
            pks = sorted(self.ajenos.get(modelo, ()))
            if pks:
                yield ruta, sorted(vista.actions), modelo, pks[0]

    def test_objeto_dado_rol_de_otra_sede_cuando_lo_lee_modifica_borra_o_le_aplica_una_accion_entonces_no_lo_encuentra(
        self,
    ):
        rutas = list(self._rutas_de_objeto())
        self.assertGreaterEqual(len(rutas), 30, "la prueba debe cubrir las rutas de objeto con datos")
        accesos = []
        for rol in ROLES_DE_UNA_SEDE:
            client = APIClient()
            client.force_authenticate(CustomUserFactory(sede=self.sede_a, area=self.area_a, groups=[rol]))
            for ruta, metodos, modelo, pk in rutas:
                url = auditoria.url_de_prueba(ruta, str(pk))
                for metodo in metodos:
                    codigo = getattr(client, metodo)(url, {}, format="json").status_code
                    # 403 (sin rol) o 404 (fuera de su sede, igual que si no existiera). Un 400
                    # o un 2xx significan que la vista encontró el objeto de la otra sede.
                    if codigo not in (403, 404, 405):
                        accesos.append(f"{rol}: {metodo.upper()} {url} → {codigo}")
                if not modelo._default_manager.filter(pk=pk).exists():
                    accesos.append(f"{rol}: {url} borró el objeto de la otra sede")
        self.assertEqual(accesos, [])
