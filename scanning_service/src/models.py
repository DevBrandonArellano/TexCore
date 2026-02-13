from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from .database import Base

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
    sede_id = Column(Integer)

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
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    lote_id = Column(Integer, ForeignKey("gestion_loteproduccion.id"))

    bodega = relationship("Bodega")
    producto = relationship("Producto")
    lote = relationship("LoteProduccion")

