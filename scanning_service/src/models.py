"""
Modelos SQLAlchemy que mapean las tablas de SQL Server compartidas con el backend Django.

NOTA DE NORMALIZACIÓN:
  - StockBodega.producto_id es transitivamente dependiente de lote_id:
      lote_id → orden_produccion_id → producto_id  (3FN violada en el esquema físico)
    Se conserva porque el esquema de SQL Server lo incluye (generado por Django migrations).
    La lógica de negocio DEBE obtener el producto via lote.orden_produccion.producto.
    La relación ORM hacia Producto desde StockBodega se omite para evitar uso accidental.
  - Bodega.sede_id referencia gestion_sede. Se declara con ForeignKey para que
    SQLAlchemy valide la integridad. La tabla no se crea desde este servicio.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .database import Base


class Sede(Base):
    __tablename__ = "gestion_sede"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)


class Producto(Base):
    __tablename__ = "gestion_producto"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String)
    descripcion = Column(String)
    stock_minimo = Column(Float)
    precio_base = Column(Float)


class Bodega(Base):
    __tablename__ = "gestion_bodega"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    sede_id = Column(Integer, ForeignKey("gestion_sede.id"), nullable=True)

    sede = relationship("Sede")


class OrdenProduccion(Base):
    __tablename__ = "gestion_ordenproduccion"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String)
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    peso_neto_requerido = Column(Numeric(10, 2))
    estado = Column(String)

    producto = relationship("Producto")


class LoteProduccion(Base):
    __tablename__ = "gestion_loteproduccion"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lote = Column(String, unique=True, index=True)
    peso_neto_producido = Column(Numeric(10, 2))
    orden_produccion_id = Column(Integer, ForeignKey("gestion_ordenproduccion.id"))

    orden_produccion = relationship("OrdenProduccion")


class StockBodega(Base):
    __tablename__ = "inventory_stockbodega"
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Numeric(12, 2))
    bodega_id = Column(Integer, ForeignKey("gestion_bodega.id"))
    # producto_id: dependencia transitiva (lote → orden → producto).
    # Se conserva por compatibilidad con el esquema físico. No usar en lógica de negocio.
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    lote_id = Column(Integer, ForeignKey("gestion_loteproduccion.id"))

    bodega = relationship("Bodega")
    lote = relationship("LoteProduccion")
    # Relación hacia Producto omitida intencionalmente: usar lote.orden_produccion.producto.
