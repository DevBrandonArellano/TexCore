"""
Test de humo y coherencia del comando de simulación integral `seed_data`.

Verifica que el seed corre de punta a punta y produce datos coherentes que
reflejan el flujo por rol (producción, trazabilidad, costeo, transferencia,
despacho y cobranza). Corre en SQLite local (settings_test_local, --no-migrations).
"""
from decimal import Decimal

import pytest
from django.core.management import call_command

from gestion.models import (
    Cliente, CostoLoteProduccion, ConsumoMateriaPrima, FormulaColor,
    LoteProduccion, OrdenProduccion, OrdenProduccionSubproceso, PagoCliente,
    PedidoVenta, TransferenciaInterarea,
)
from inventory.models import HistorialDespacho, MovimientoInventario, StockBodega


@pytest.mark.django_db
def test_seed_data_simulacion_integral():
    # El seed debe correr completo sin excepciones.
    call_command('seed_data', '--no-superuser', verbosity=0)

    # --- Producción: lote con trazabilidad, empaque y costeo ---------------
    lote = LoteProduccion.objects.get(codigo_lote='SIM-001-L1')
    assert ConsumoMateriaPrima.objects.filter(lote_produccion=lote).exists(), \
        'El lote debe tener trazabilidad de materia prima'
    assert CostoLoteProduccion.objects.filter(lote_produccion=lote).exists(), \
        'El lote debe tener costeo calculado'
    assert lote.presentacion == 'funda'
    assert lote.peso_bruto == Decimal('98.000') and lote.tara == Decimal('3.000')

    # --- Kardex: existen los tipos de movimiento del flujo completo --------
    tipos = set(MovimientoInventario.objects.values_list('tipo_movimiento', flat=True))
    for esperado in ('COMPRA', 'CONSUMO', 'PRODUCCION', 'TRANSFERENCIA', 'VENTA'):
        assert esperado in tipos, f'Falta movimiento tipo {esperado} en el Kardex'

    # Ningún stock puede quedar negativo (coherencia de inventario)
    assert not StockBodega.objects.filter(cantidad__lt=0).exists()

    # --- Gestión de la orden: jefe crea, operario avanza subprocesos -------
    estados_sub = set(OrdenProduccionSubproceso.objects.values_list('estado', flat=True))
    assert {'completado', 'en_progreso', 'pendiente'} <= estados_sub, \
        f'Subprocesos deben mostrar estados variados, hay: {estados_sub}'
    # El avance quedó atribuido a un responsable
    assert OrdenProduccionSubproceso.objects.filter(
        estado='completado', usuario_responsable__isnull=False).exists()

    # --- OPs en distintos estados ------------------------------------------
    op_estado = dict(OrdenProduccion.objects.values_list('codigo', 'estado'))
    assert op_estado['OP-SIM-001'] == 'finalizada'
    assert op_estado['OP-SIM-002'] == 'finalizada'
    assert op_estado['OP-SIM-003'] == 'en_proceso'
    assert op_estado['OP-SIM-004'] == 'pendiente'

    # --- Transferencia interárea Tintura -> Empaque ------------------------
    assert TransferenciaInterarea.objects.exists()

    # --- Fórmula creada por tintorería y aprobada --------------------------
    formula = FormulaColor.objects.get(codigo='FORM-ROJO-001')
    assert formula.estado == 'aprobada'
    assert formula.fases.count() == 3

    # --- Despacho por escaneo ----------------------------------------------
    assert HistorialDespacho.objects.exists()
    p1 = PedidoVenta.objects.get(guia_remision='GR-SIM-001')
    assert p1.estado == 'despachado'
    assert p1.esta_pagado, 'El pedido 1 debe quedar pagado (pago total)'

    # --- Cartera: vencida y pago parcial -----------------------------------
    cliente2 = Cliente.objects.get(ruc_cedula='RUC-002')
    assert cliente2.cartera_vencida > 0, 'RUC-002 debe tener cartera vencida'

    p4 = PedidoVenta.objects.get(guia_remision='GR-SIM-004')
    assert not p4.esta_pagado and p4.monto_pagado > 0, 'Pedido 4 debe tener pago parcial'


@pytest.mark.django_db
def test_seed_data_cobertura_modelos():
    """La simulación debe poblar TODOS los modelos salvo el opcional.

    Sólo puede quedar vacío ConsumoLoteDetalle (traza de consumo de mezcla, un
    flujo avanzado que no forma parte de la columna vertebral). El MRP corre por
    defecto, así que RequerimientoMaterial y OrdenCompraSugerida sí se pueblan.
    """
    from django.apps import apps

    call_command('seed_data', '--no-superuser', verbosity=0)

    opcionales_vacios = {'ConsumoLoteDetalle'}
    vacios = set()
    for app_label in ('gestion', 'inventory'):
        for model in apps.get_app_config(app_label).get_models():
            if model.objects.count() == 0:
                vacios.add(model.__name__)

    inesperados = vacios - opcionales_vacios
    assert not inesperados, f'Modelos inesperadamente vacíos: {sorted(inesperados)}'


@pytest.mark.django_db
def test_seed_data_es_idempotente():
    """Re-ejecutar el seed no debe duplicar la simulación ni fallar."""
    call_command('seed_data', '--no-superuser', verbosity=0)
    lotes_antes = LoteProduccion.objects.count()
    pedidos_antes = PedidoVenta.objects.count()

    call_command('seed_data', '--no-superuser', verbosity=0)
    assert LoteProduccion.objects.count() == lotes_antes
    assert PedidoVenta.objects.count() == pedidos_antes
