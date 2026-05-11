"""
Tests unitarios de LoteValidationService.
No requieren BD, HTTP ni FastAPI: solo dependen del Protocol ILoteRepository.
LoteValidationService recibe un mock que implementa ILoteRepository — sin sys.modules hacks.
Convención ISTQB: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
"""
import pytest
from unittest.mock import MagicMock

from src.services.validation_service import LoteValidationService


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
    o.producto = producto or _make_producto()
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
        result = service.validate("LOTE-INEXISTENTE")
        assert result.valid is False
        assert "no encontrado" in result.reason.lower()

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_consulta_repositorio_con_codigo(self):
        repo = _make_repo(lote=None)
        LoteValidationService(repo).validate("LOTE-ABC")
        repo.get_lote_by_codigo.assert_called_once_with("LOTE-ABC")

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_no_consulta_stock(self):
        repo = _make_repo(lote=None)
        LoteValidationService(repo).validate("LOTE-ABC")
        repo.get_stock_activo_por_lote.assert_not_called()


# ---------------------------------------------------------------------------
# EP Clase Inválida: lote sin orden de producción
# ---------------------------------------------------------------------------

class TestLoteValidationService_LoteSinOrden:

    def test_validate_dado_lote_sin_orden_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        lote.orden_produccion = None
        result = LoteValidationService(_make_repo(lote=lote)).validate("LOTE-00001")
        assert result.valid is False
        assert result.reason is not None

    def test_validate_dado_lote_sin_producto_en_orden_cuando_validar_entonces_retorna_invalido(self):
        orden = _make_orden()
        orden.producto = None
        lote = _make_lote(orden=orden)
        result = LoteValidationService(_make_repo(lote=lote)).validate("LOTE-00001")
        assert result.valid is False

    def test_validate_dado_lote_sin_orden_cuando_validar_entonces_no_consulta_stock(self):
        lote = _make_lote()
        lote.orden_produccion = None
        repo = _make_repo(lote=lote)
        LoteValidationService(repo).validate("LOTE-00001")
        repo.get_stock_activo_por_lote.assert_not_called()


# ---------------------------------------------------------------------------
# EP Clase Inválida: lote sin stock
# ---------------------------------------------------------------------------

class TestLoteValidationService_LoteSinStock:

    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        result = LoteValidationService(_make_repo(lote=lote, stock=None)).validate("LOTE-00001")
        assert result.valid is False
        assert "stock" in result.reason.lower()

    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_consulta_stock_del_lote_correcto(self):
        lote = _make_lote()
        lote.id = 42
        repo = _make_repo(lote=lote, stock=None)
        LoteValidationService(repo).validate("LOTE-00001")
        repo.get_stock_activo_por_lote.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# EP Clase Válida: lote con stock disponible
# ---------------------------------------------------------------------------

class TestLoteValidationService_LoteValido:

    def test_validate_dado_lote_con_stock_cuando_validar_entonces_retorna_valido(self):
        lote = _make_lote("LOTE-00001")
        stock = _make_stock(cantidad=25)
        result = LoteValidationService(_make_repo(lote=lote, stock=stock)).validate("LOTE-00001")
        assert result.valid is True
        assert result.lote is not None

    def test_validate_dado_lote_valido_cuando_validar_entonces_codigo_en_respuesta(self):
        lote = _make_lote("LOTE-00001")
        result = LoteValidationService(_make_repo(lote=lote, stock=_make_stock())).validate("LOTE-00001")
        assert result.lote.codigo == "LOTE-00001"

    def test_validate_dado_lote_valido_cuando_validar_entonces_retorna_nombre_bodega_correcto(self):
        bodega = _make_bodega(id=10, nombre="Bodega Sur")
        lote = _make_lote()
        result = LoteValidationService(
            _make_repo(lote=lote, stock=_make_stock(bodega=bodega))
        ).validate("LOTE-00001")
        assert result.lote.bodega_nombre == "Bodega Sur"
        assert result.lote.bodega_id == 10

    def test_validate_dado_lote_valido_cuando_validar_entonces_retorna_datos_producto(self):
        producto = _make_producto(id=5, descripcion="Hilo Texturizado")
        orden = _make_orden(producto=producto)
        lote = _make_lote(orden=orden)
        result = LoteValidationService(
            _make_repo(lote=lote, stock=_make_stock())
        ).validate("LOTE-00001")
        assert result.lote.producto_id == 5
        assert result.lote.producto_nombre == "Hilo Texturizado"

    def test_validate_dado_lote_valido_cuando_validar_entonces_peso_es_string_de_cantidad(self):
        stock = _make_stock(cantidad=37.5)
        lote = _make_lote()
        result = LoteValidationService(
            _make_repo(lote=lote, stock=stock)
        ).validate("LOTE-00001")
        assert result.lote.peso == "37.5"

    def test_validate_dado_lote_valido_cuando_validar_entonces_lote_sin_razon(self):
        lote = _make_lote()
        result = LoteValidationService(
            _make_repo(lote=lote, stock=_make_stock())
        ).validate("LOTE-00001")
        assert result.reason is None
