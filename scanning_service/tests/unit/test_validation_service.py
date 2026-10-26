"""
Tests unitarios de LoteValidationService.
No requieren BD, HTTP ni FastAPI: solo dependen del Protocol ILoteRepository.
LoteValidationService recibe un mock que implementa ILoteRepository — sin sys.modules hacks.
Convención ISTQB: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
"""

from decimal import Decimal
from unittest.mock import MagicMock

from src.domain.models import AlcanceSede, Bodega, LoteProduccion, OrdenProduccion, Producto, StockBodega
from src.services.validation_service import LoteValidationService

# Usuario que ve todas las sedes: las pruebas de reglas de negocio no dependen del alcance.
TODAS = AlcanceSede(sede_id=None, ve_todas=True)

# ---------------------------------------------------------------------------
# Helpers para construir objetos mock del dominio
# ---------------------------------------------------------------------------


def _make_producto(id: int = 1, descripcion: str = "Hilo Nylon") -> MagicMock:
    p = MagicMock()
    p.id = id
    p.descripcion = descripcion
    return p


def _make_bodega(id: int = 10, nombre: str = "Bodega Central") -> MagicMock:
    b = MagicMock()
    b.id = id
    b.nombre = nombre
    return b


def _make_orden(producto=None) -> MagicMock:
    o = MagicMock()
    o.producto_salida = producto or _make_producto()
    return o


def _make_lote(codigo: str = "LOTE-00001", orden=None) -> MagicMock:
    lote = MagicMock()
    lote.id = 1
    lote.codigo_lote = codigo
    lote.orden_produccion = orden or _make_orden()
    return lote


def _make_stock(cantidad=50, bodega=None) -> MagicMock:
    s = MagicMock()
    s.cantidad = cantidad
    s.bodega = bodega or _make_bodega()
    return s


def _make_repo(lote=None, stock=None) -> MagicMock:
    """Mock de ILoteRepository con respuestas configurables."""
    repo = MagicMock()
    repo.get_lote_by_codigo.return_value = lote
    repo.get_stock_activo_por_lote.return_value = stock
    return repo


# ---------------------------------------------------------------------------
# EP Clase Inválida: lote no encontrado
# ---------------------------------------------------------------------------


class TestLoteValidationService_LoteNoEncontrado:
    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_retorna_invalido(self):
        service = LoteValidationService(_make_repo(lote=None))
        result = service.validate("LOTE-INEXISTENTE", TODAS)
        assert result.valid is False
        assert "no encontrado" in result.reason.lower()

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_consulta_repositorio_con_codigo(self):
        repo = _make_repo(lote=None)
        LoteValidationService(repo).validate("LOTE-ABC", TODAS)
        repo.get_lote_by_codigo.assert_called_once_with("LOTE-ABC", TODAS)

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_no_consulta_stock(self):
        repo = _make_repo(lote=None)
        LoteValidationService(repo).validate("LOTE-ABC", TODAS)
        repo.get_stock_activo_por_lote.assert_not_called()


# ---------------------------------------------------------------------------
# EP Clase Inválida: lote sin orden de producción
# ---------------------------------------------------------------------------


class TestLoteValidationService_LoteSinOrden:
    def test_validate_dado_lote_sin_orden_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        lote.orden_produccion = None
        result = LoteValidationService(_make_repo(lote=lote)).validate("LOTE-00001", TODAS)
        assert result.valid is False
        assert result.reason is not None

    def test_validate_dado_lote_sin_producto_en_orden_cuando_validar_entonces_retorna_invalido(self):
        orden = _make_orden()
        orden.producto = None
        lote = _make_lote(orden=orden)
        result = LoteValidationService(_make_repo(lote=lote)).validate("LOTE-00001", TODAS)
        assert result.valid is False

    def test_validate_dado_lote_sin_orden_cuando_validar_entonces_no_consulta_stock(self):
        lote = _make_lote()
        lote.orden_produccion = None
        repo = _make_repo(lote=lote)
        LoteValidationService(repo).validate("LOTE-00001", TODAS)
        repo.get_stock_activo_por_lote.assert_not_called()


# ---------------------------------------------------------------------------
# EP Clase Inválida: lote sin stock
# ---------------------------------------------------------------------------


class TestLoteValidationService_LoteSinStock:
    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        result = LoteValidationService(_make_repo(lote=lote, stock=None)).validate("LOTE-00001", TODAS)
        assert result.valid is False
        assert "stock" in result.reason.lower()

    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_consulta_stock_del_lote_correcto(self):
        lote = _make_lote()
        lote.id = 42
        repo = _make_repo(lote=lote, stock=None)
        LoteValidationService(repo).validate("LOTE-00001", TODAS)
        repo.get_stock_activo_por_lote.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# EP Clase Válida: lote con stock disponible
# ---------------------------------------------------------------------------


class TestLoteValidationService_LoteValido:
    def test_validate_dado_lote_con_stock_cuando_validar_entonces_retorna_valido(self):
        lote = _make_lote("LOTE-00001")
        stock = _make_stock(cantidad=25)
        result = LoteValidationService(_make_repo(lote=lote, stock=stock)).validate("LOTE-00001", TODAS)
        assert result.valid is True
        assert result.lote is not None

    def test_validate_dado_lote_valido_cuando_validar_entonces_codigo_en_respuesta(self):
        lote = _make_lote("LOTE-00001")
        result = LoteValidationService(_make_repo(lote=lote, stock=_make_stock())).validate("LOTE-00001", TODAS)
        assert result.lote.codigo == "LOTE-00001"

    def test_validate_dado_lote_valido_cuando_validar_entonces_retorna_nombre_bodega_correcto(self):
        bodega = _make_bodega(id=10, nombre="Bodega Sur")
        lote = _make_lote()
        result = LoteValidationService(_make_repo(lote=lote, stock=_make_stock(bodega=bodega))).validate(
            "LOTE-00001", TODAS
        )
        assert result.lote.bodega_nombre == "Bodega Sur"
        assert result.lote.bodega_id == 10

    def test_validate_dado_lote_valido_cuando_validar_entonces_retorna_datos_producto(self):
        producto = _make_producto(id=5, descripcion="Hilo Texturizado")
        orden = _make_orden(producto=producto)
        lote = _make_lote(orden=orden)
        result = LoteValidationService(_make_repo(lote=lote, stock=_make_stock())).validate("LOTE-00001", TODAS)
        assert result.lote.producto_id == 5
        assert result.lote.producto_nombre == "Hilo Texturizado"

    def test_validate_dado_lote_valido_cuando_validar_entonces_peso_es_string_de_cantidad(self):
        stock = _make_stock(cantidad=37.5)
        lote = _make_lote()
        result = LoteValidationService(_make_repo(lote=lote, stock=stock)).validate("LOTE-00001", TODAS)
        assert result.lote.peso == "37.5"

    def test_validate_dado_lote_valido_cuando_validar_entonces_lote_sin_razon(self):
        lote = _make_lote()
        result = LoteValidationService(_make_repo(lote=lote, stock=_make_stock())).validate("LOTE-00001", TODAS)
        assert result.reason is None


# ---------------------------------------------------------------------------
# P0: LoteValidationService contra el dominio REAL (no MagicMock)
#
# Los tests de arriba mockean el repositorio completo con MagicMock, que
# auto-crea cualquier atributo accedido sin importar si existe realmente en
# el dataclass — por eso no detectarían un drift entre el campo real de
# OrdenProduccion (src/domain/models.py, `producto_salida`) y el que lee
# validation_service.py. Esta clase usa un fake repository que retorna
# instancias reales de los dataclasses, así que un nombre de campo
# equivocado revienta con TypeError/AttributeError como reventaba en
# producción para todo lote que sí existía.
# ---------------------------------------------------------------------------


class _RealDomainRepo:
    """Fake de ILoteRepository que retorna dataclasses reales de domain.models."""

    def __init__(self, lote=None, stock=None):
        self._lote = lote
        self._stock = stock

    def get_lote_by_codigo(self, codigo: str, alcance: AlcanceSede):
        return self._lote

    def get_stock_activo_por_lote(self, lote_id: int):
        return self._stock


class TestLoteValidationService_ConDominioReal:
    def test_validate_dado_lote_real_con_stock_cuando_valida_entonces_retorna_valido(self):
        producto = Producto(id=5, descripcion="Hilo Nylon 40/1")
        orden = OrdenProduccion(id=1, estado="finalizada", producto_salida=producto)
        lote = LoteProduccion(id=1, codigo_lote="LOTE-00001", orden_produccion=orden)
        bodega = Bodega(id=10, nombre="Bodega Central")
        stock = StockBodega(id=1, cantidad=Decimal("25.500"), bodega=bodega)
        repo = _RealDomainRepo(lote=lote, stock=stock)

        result = LoteValidationService(repo).validate("LOTE-00001", TODAS)

        assert result.valid is True
        assert result.lote.producto_id == 5
        assert result.lote.producto_nombre == "Hilo Nylon 40/1"
        assert result.lote.bodega_id == 10
        assert result.lote.bodega_nombre == "Bodega Central"
        assert result.lote.peso == "25.500"


class TestLoteValidationService_ProductosDelLote:
    """Un lote con productos agregados a mano informa todos y su peso total."""

    def test_validate_dado_lote_con_varios_productos_cuando_valida_entonces_los_informa_con_su_total(self):
        from src.domain.models import LineaStock

        hilo = Producto(id=5, descripcion="Hilo Nylon 40/1")
        cono = Producto(id=6, descripcion="Cono")
        central = Bodega(id=10, nombre="Bodega Central")
        lote = LoteProduccion(
            id=1,
            codigo_lote="LOTE-00001",
            orden_produccion=OrdenProduccion(id=1, estado="finalizada", producto_salida=hilo),
            productos=[
                LineaStock(producto=hilo, cantidad=Decimal("25.500"), bodega=central),
                LineaStock(producto=cono, cantidad=Decimal("4.500"), bodega=central),
            ],
        )
        stock = StockBodega(id=1, cantidad=Decimal("25.500"), bodega=central)

        result = LoteValidationService(_RealDomainRepo(lote=lote, stock=stock)).validate("LOTE-00001", TODAS)

        assert result.lote.peso == "25.500"
        assert result.lote.peso_total == "30.000"
        assert [(p.producto_id, p.producto_nombre, p.peso, p.bodega_id) for p in result.lote.productos] == [
            (5, "Hilo Nylon 40/1", "25.500", 10),
            (6, "Cono", "4.500", 10),
        ]

    def test_validate_dado_lote_sin_detalle_de_productos_cuando_valida_entonces_campos_nuevos_vacios(self):
        producto = Producto(id=5, descripcion="Hilo")
        lote = LoteProduccion(
            id=1, codigo_lote="L-1", orden_produccion=OrdenProduccion(id=1, estado="x", producto_salida=producto)
        )
        stock = StockBodega(id=1, cantidad=Decimal("1.000"), bodega=Bodega(id=1, nombre="B"))

        result = LoteValidationService(_RealDomainRepo(lote=lote, stock=stock)).validate("L-1", TODAS)

        assert (result.lote.peso_total, result.lote.productos) == (None, [])


# ---------------------------------------------------------------------------
# OWASP API1: alcance por sede del usuario que escanea
# ---------------------------------------------------------------------------


class TestLoteValidationService_AlcanceSede:
    def test_validate_dado_sede_del_usuario_cuando_valida_entonces_la_pasa_al_repositorio(self):
        repo = _make_repo(lote=None)
        alcance = AlcanceSede(sede_id=3, ve_todas=False)
        LoteValidationService(repo).validate("LOTE-ABC", alcance)
        repo.get_lote_by_codigo.assert_called_once_with("LOTE-ABC", alcance)

    def test_validate_dado_usuario_sin_sede_que_no_ve_todas_cuando_valida_entonces_no_encontrado_sin_consultar(self):
        repo = _make_repo(lote=_make_lote())
        result = LoteValidationService(repo).validate("LOTE-ABC", AlcanceSede(sede_id=None, ve_todas=False))
        assert result.valid is False
        assert "no encontrado" in result.reason.lower()
        repo.get_lote_by_codigo.assert_not_called()
