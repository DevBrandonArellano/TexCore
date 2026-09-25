"""
Servicio de calculo de dosificacion para formulas de tintoreria.

Metodos de calculo soportados:
- Concentracion (gr/L): la cantidad del producto se calcula sobre el volumen del bano.
- Agotamiento (%): la cantidad del producto se calcula como porcentaje sobre el peso de la tela.

Terminologia:
- Relacion de bano (ej. 10 para una relacion 1:10): litros de agua por kg de tela.
- Volumen del bano (L) = kg_tela * relacion_bano
- Dosificacion por gr/L: cantidad_gr = volumen_L * concentracion_gr_l
- Dosificacion por %: cantidad_gr = kg_tela * 1000 * (porcentaje / 100)
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoInsumo:
    """Resultado de dosificacion para un insumo especifico."""
    producto_id: int
    producto_descripcion: str
    tipo_calculo: str
    cantidad_kg: Decimal
    cantidad_gr: Decimal
    concentracion_gr_l: Optional[Decimal] = None
    porcentaje: Optional[Decimal] = None
    orden_adicion: int = 1
    notas: str = ''
    stock_minimo: Optional[Decimal] = None


@dataclass
class ResultadoDosificacion:
    """Resultado completo de la calculadora de dosificacion para un bano de tintura."""
    kg_tela: Decimal
    relacion_bano: Decimal
    volumen_bano_litros: Decimal
    insumos: list


def calcular_dosificacion_gr_l(
    concentracion_gr_l: Decimal,
    volumen_bano_litros: Decimal,
) -> Decimal:
    """
    Calcula la cantidad de insumo en kg usando el metodo de Concentracion (gr/L).

    Formula:
        cantidad_gr = volumen_bano_litros * concentracion_gr_l
        cantidad_kg = cantidad_gr / 1000

    Args:
        concentracion_gr_l: Concentracion del insumo en gramos por litro de bano.
        volumen_bano_litros: Volumen total del bano en litros.

    Returns:
        Cantidad del insumo en kilogramos, redondeada a 6 decimales.
    """
    cantidad_gr = volumen_bano_litros * concentracion_gr_l
    return (cantidad_gr / Decimal('1000')).quantize(Decimal('0.000001'))


def calcular_dosificacion_pct(
    porcentaje: Decimal,
    kg_tela: Decimal,
) -> Decimal:
    """
    Calcula la cantidad de insumo en kg usando el metodo de Agotamiento (%).

    Formula:
        cantidad_kg = (kg_tela * porcentaje) / 100

    Args:
        porcentaje: Porcentaje del insumo sobre el peso de la tela.
        kg_tela: Peso de la tela en kilogramos.

    Returns:
        Cantidad del insumo en kilogramos, redondeada a 6 decimales.
    """
    return ((kg_tela * porcentaje) / Decimal('100')).quantize(Decimal('0.000001'))


class DosificacionCalculator:
    """
    Calculadora de dosificacion para un bano de tintoreria completo.

    Recibe una instancia de FormulaColor y los parametros del bano,
    y retorna la cantidad requerida de cada insumo quimico.
    """

    def __init__(self, formula_color):
        """
        Args:
            formula_color: Instancia de gestion.models.FormulaColor.
        """
        self.formula = formula_color

    def calcular(
        self,
        kg_tela: Decimal,
        relacion_bano: Decimal,
    ) -> ResultadoDosificacion:
        """
        Ejecuta el calculo de dosificacion para todos los insumos de la formula.

        Args:
            kg_tela: Peso de la tela en kilogramos.
            relacion_bano: Relacion de bano (litros de agua por kg de tela).
                          Ejemplo: 10 para una relacion 1:10.

        Returns:
            ResultadoDosificacion con el detalle por insumo.
        """
        kg_tela = Decimal(str(kg_tela))
        relacion_bano = Decimal(str(relacion_bano))
        volumen_litros = kg_tela * relacion_bano

        resultados_insumos = []

        # Recorrer todas las fases y sus detalles en orden
        for fase in self.formula.fases.all().order_by('orden'):
            detalles = fase.detalles.select_related('producto').order_by('orden_adicion')
            for detalle in detalles:
                if not detalle.producto:
                    continue

                tipo = detalle.tipo_calculo

                if tipo == 'gr_l':
                    concentracion = detalle.concentracion_gr_l
                    if concentracion is None:
                        # Fallback al campo legacy gramos_por_kilo interpretado como gr/L
                        concentracion = detalle.gramos_por_kilo
                    cantidad_kg = calcular_dosificacion_gr_l(concentracion, volumen_litros)
                elif tipo == 'pct':
                    porcentaje = detalle.porcentaje
                    if porcentaje is None:
                        pct_convertido = (detalle.gramos_por_kilo / Decimal('1000')) * Decimal('100')
                        porcentaje = pct_convertido
                    cantidad_kg = calcular_dosificacion_pct(porcentaje, kg_tela)
                else:
                    cantidad_kg = Decimal('0')

                resultados_insumos.append(
                    ResultadoInsumo(
                        producto_id=detalle.producto.id,
                        producto_descripcion=detalle.producto.descripcion,
                        tipo_calculo=tipo,
                        cantidad_kg=cantidad_kg,
                        cantidad_gr=(cantidad_kg * Decimal('1000')).quantize(Decimal('0.001')),
                        concentracion_gr_l=detalle.concentracion_gr_l if tipo == 'gr_l' else None,
                        porcentaje=detalle.porcentaje if tipo == 'pct' else None,
                        orden_adicion=detalle.orden_adicion,
                        notas=detalle.notas or '',
                        stock_minimo=detalle.producto.stock_minimo,
                    )
                )

        return ResultadoDosificacion(
            kg_tela=kg_tela,
            relacion_bano=relacion_bano,
            volumen_bano_litros=volumen_litros,
            insumos=resultados_insumos,
        )

    def calcular_desde_litros(self, peso: Decimal, litros: Decimal) -> ResultadoDosificacion:
        """Fase 3 del spec 2026-09-24 (D3): los litros son el dato canónico que fija el
        ingeniero tintorero; la relación de baño se deriva (litros / peso), no se pide.
        Mismas fórmulas de dosificación que `calcular` (gr/L sobre litros, % sobre peso):
        se implementa como una conversión de unidades hacia `calcular`."""
        peso = Decimal(str(peso))
        litros = Decimal(str(litros))
        if peso <= 0:
            raise ValueError('El peso debe ser mayor a cero.')
        relacion_bano = (litros / peso).quantize(Decimal('0.0001'))
        return self.calcular(kg_tela=peso, relacion_bano=relacion_bano)


def calcular_dosificacion_desde_snapshot(snapshot: dict, peso: Decimal, litros: Decimal) -> ResultadoDosificacion:
    """Regla 6 del spec 2026-09-24: la descarga de químicos de una orden lanzada se
    calcula desde `version_formula.snapshot` (receta congelada), no desde la receta viva.
    Recorre el JSON del snapshot en vez de las relaciones ORM de FormulaColor."""
    from gestion.models import Producto

    peso = Decimal(str(peso))
    litros = Decimal(str(litros))
    if peso <= 0:
        raise ValueError('El peso debe ser mayor a cero.')
    relacion_bano = (litros / peso).quantize(Decimal('0.0001'))

    detalles_planos = [
        detalle
        for fase in snapshot.get('fases', [])
        for detalle in fase.get('detalles', [])
    ]
    producto_ids = {d['producto_id'] for d in detalles_planos if d.get('producto_id')}
    productos = Producto.objects.in_bulk(producto_ids)

    resultados_insumos = []
    for detalle in detalles_planos:
        producto = productos.get(detalle.get('producto_id'))
        tipo = detalle.get('tipo_calculo')

        if tipo == 'gr_l':
            concentracion = Decimal(detalle['concentracion_gr_l']) if detalle.get('concentracion_gr_l') is not None else Decimal('0')
            cantidad_kg = calcular_dosificacion_gr_l(concentracion, litros)
        elif tipo == 'pct':
            porcentaje = Decimal(detalle['porcentaje']) if detalle.get('porcentaje') is not None else Decimal('0')
            cantidad_kg = calcular_dosificacion_pct(porcentaje, peso)
        else:
            cantidad_kg = Decimal('0')

        resultados_insumos.append(
            ResultadoInsumo(
                producto_id=detalle.get('producto_id'),
                producto_descripcion=detalle.get('producto_descripcion') or (producto.descripcion if producto else ''),
                tipo_calculo=tipo,
                cantidad_kg=cantidad_kg,
                cantidad_gr=(cantidad_kg * Decimal('1000')).quantize(Decimal('0.001')),
                concentracion_gr_l=Decimal(detalle['concentracion_gr_l']) if tipo == 'gr_l' and detalle.get('concentracion_gr_l') is not None else None,
                porcentaje=Decimal(detalle['porcentaje']) if tipo == 'pct' and detalle.get('porcentaje') is not None else None,
                orden_adicion=detalle.get('orden_adicion', 1),
                notas='',
                stock_minimo=producto.stock_minimo if producto else None,
            )
        )

    return ResultadoDosificacion(
        kg_tela=peso,
        relacion_bano=relacion_bano,
        volumen_bano_litros=litros,
        insumos=resultados_insumos,
    )
