from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class Produto(Base):
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

class LoteProduccion(Base):
    __tablename__ = "gestion_loteproduccion"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lote = Column(String, unique=True, index=True)
    peso_neto_producido = Column(Float)
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))

    producto = relationship("Produto")

class StockBodega(Base):
    __tablename__ = "inventory_stockbodega"
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Float)
    bodega_id = Column(Integer, ForeignKey("gestion_bodega.id"))
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    lote_id = Column(Integer, ForeignKey("gestion_loteproduccion.id"))

    bodega = relationship("Bodega")
    producto = relationship("Produto")
    lote = relationship("LoteProduccion")
