"""
Seed de SIMULACIÓN INTEGRAL de TexCore.

Puebla la base con un caso coherente end-to-end que recorre el trabajo de CADA
rol, usando la capa de servicios real (para que stock, Kardex y costos cuadren)
e inserción directa donde no hay servicio de creación (despacho, pagos, config).

Orden recomendado de despliegue (este comando ya lo orquesta con flags):
    python manage.py seed_data          # superuser + permisos + datos

Flujo simulado (una sede: "Planta Quito"):
  admin      -> credenciales de servicios internos
  vendedor   -> clientes
  bodeguero  -> recepción de materia prima (COMPRA) + surtido de químicos/insumos
  jefe_planta-> crea las órdenes de producción
  jefe_area  -> asigna máquina + operario y genera los subprocesos
  tintorero  -> crea la fórmula de color y la OP se produce usándola
  operario   -> registra el avance (subprocesos), transformación, lote y costeo
  transferencia Tintura -> Empaque (3 fases a granel + transferencia del lote)
  empaquetado-> empaca el lote final (queda listo para etiqueta ZPL y despacho)
  despacho   -> despacho por escaneo (baja de stock VENTA)
  vendedor   -> pagos (total / parcial / anticipo / reversión) y cartera vencida
  (opcional) MRP -> requerimientos y órdenes de compra sugeridas

Las etiquetas NO son entidades Django: el printing_service genera el ZPL al
vuelo desde el LoteProduccion; por eso el seed deja los lotes con los datos de
empaque completos. Las SQLite de los microservicios (scanning/printing/reporting)
las llenan ellos en runtime.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from gestion import middleware
from gestion.models import (
    Area, AreaProcessStep, Batch, Bodega, Cliente, ComponenteMezclaOP,
    CostoHoraMaquina, CustomUser, DetalleFormula, DetallePedido,
    EtapaProduccion, FaseReceta, FormulaColor, LineaProduccion, LoteProduccion,
    Maquina, OrdenProduccion, OrdenProduccionSubproceso, PagoCliente, PedidoVenta,
    ProcessStep, Producto, Proveedor, Sede, TarifaOperario,
    TransferenciaInterarea,
)
from inventory.models import (
    DetalleHistorialDespacho, DetalleHistorialDespachoPedido,
    HistorialDespacho, MovimientoInventario, StockBodega,
)
from internal_api.models import ServiceCredential

from inventory.utils import safe_get_or_create_stock
from inventory.services.transicion_bodega_service import TransicionBodegaService
from gestion.services.materia_prima_service import MateriaPrimaService
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.transformacion import TransformacionService
from gestion.services.registro_lote import RegistroLoteService
from gestion.services.costeo_service import CostoLoteService
from gestion.services.pago_reversion import PagoReversionService
from gestion.utils import PaymentReconciler

logger = logging.getLogger(__name__)

PASSWORD = 'password123'
GROUP_NAMES = [
    'operario', 'bodeguero', 'vendedor', 'jefe_area', 'jefe_planta',
    'admin_sede', 'ejecutivo', 'admin_sistemas', 'empaquetado', 'despacho',
    'tintorero',
]


class Command(BaseCommand):
    help = 'Simulación integral de datos de TexCore (todos los flujos por rol).'

    def add_arguments(self, parser):
        parser.add_argument('--no-superuser', action='store_true',
                            help='No crear/asegurar el superusuario "sistemas".')
        parser.add_argument('--no-permissions', action='store_true',
                            help='No ejecutar setup_permissions.')
        parser.add_argument('--sin-mrp', action='store_true',
                            help='No ejecutar el motor MRP (por defecto se ejecuta al final).')
        parser.add_argument('--sin-credenciales', action='store_true',
                            help='No crear ServiceCredential de los microservicios.')

    # ------------------------------------------------------------------ utils
    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'✓ {msg}'))

    def _info(self, msg):
        self.stdout.write(self.style.NOTICE(msg))

    def actuar_como(self, user):
        """Simula el usuario autenticado para que el AuditLog atribuya la acción."""
        middleware._local.user = user

    def _limpiar_actor(self):
        middleware._local.__dict__.pop('user', None)

    def _compra_inicial(self, producto, bodega, cantidad, usuario, ref='COMPRA-INICIAL'):
        """Ingreso directo de stock con Kardex (COMPRA) para químicos/insumos."""
        cantidad = Decimal(str(cantidad))
        stock, _ = safe_get_or_create_stock(StockBodega, bodega=bodega, producto=producto, lote=None)
        stock.cantidad += cantidad
        stock._justificacion_auditoria = f'{ref} (seed)'
        stock.save()
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=producto,
            bodega_destino=bodega,
            cantidad=cantidad,
            usuario=usuario,
            documento_ref=ref,
            saldo_resultante=stock.cantidad,
        )
        return stock

    def _crear_subprocesos(self, orden):
        """Un OrdenProduccionSubproceso por cada AreaProcessStep del área (estado pendiente)."""
        creados = []
        for aps in AreaProcessStep.objects.filter(area=orden.area).order_by('orden'):
            sub, _ = OrdenProduccionSubproceso.objects.get_or_create(
                orden_produccion=orden, area_proceso=aps,
                defaults={'estado': 'pendiente'},
            )
            creados.append(sub)
        return creados

    def _avanzar_subproceso(self, sub, estado, operario, obs=''):
        """Replica las transiciones del OrdenProduccionSubprocesoViewSet."""
        ahora = timezone.now()
        if estado == 'en_progreso':
            sub.estado = 'en_progreso'
            sub.fecha_inicio_real = sub.fecha_inicio_real or ahora
            sub.usuario_responsable = operario
        elif estado == 'completado':
            sub.estado = 'completado'
            sub.fecha_inicio_real = sub.fecha_inicio_real or (ahora - timedelta(hours=3))
            sub.fecha_fin_real = ahora
            sub.usuario_responsable = operario
        if obs:
            sub.observaciones = obs
        sub.save()
        return sub

    def _transferir_lote(self, lote, producto, b_origen, b_destino, cantidad, usuario, op_o, op_d):
        """Transfiere un lote terminado entre áreas (con lote) + registra TransferenciaInterarea."""
        cantidad = Decimal(str(cantidad))
        stock_o = StockBodega.objects.get(bodega=b_origen, producto=producto, lote=lote)
        stock_o.cantidad -= cantidad
        stock_o._justificacion_auditoria = f'Transferencia interárea → {b_destino.nombre}'
        stock_o.save()

        stock_d, _ = safe_get_or_create_stock(StockBodega, bodega=b_destino, producto=producto, lote=lote)
        stock_d.cantidad += cantidad
        stock_d._justificacion_auditoria = f'Recepción interárea desde {b_origen.nombre}'
        stock_d.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='TRANSFERENCIA',
            producto=producto,
            lote=lote,
            bodega_origen=b_origen,
            bodega_destino=b_destino,
            cantidad=cantidad,
            usuario=usuario,
            documento_ref=f'TRANSF-{op_o.codigo}->{op_d.codigo}',
            estado_movimiento='completado',
            saldo_resultante=stock_d.cantidad,
        )
        TransferenciaInterarea.objects.create(
            orden_area_origen=op_o,
            orden_area_destino=op_d,
            bodega_origen=b_origen,
            bodega_destino=b_destino,
            cantidad_transferida=cantidad,
            usuario_responsable=usuario,
            observaciones='Transferencia Tintura → Empaque (seed)',
        )

    def _registrar_despacho(self, pedido, lote_items, usuario, bodega):
        """Crea el despacho (HistorialDespacho + detalles + MovimientoInventario VENTA)."""
        total_peso = sum((Decimal(str(p)) for _, _, p in lote_items), Decimal('0'))
        historial = HistorialDespacho.objects.create(
            usuario=usuario,
            total_bultos=len(lote_items),
            total_peso=total_peso,
            observaciones=f'Despacho por escaneo de {pedido.guia_remision} (seed)',
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=historial, pedido=pedido, cantidad_despachada=total_peso,
        )
        for lote, producto, peso in lote_items:
            peso = Decimal(str(peso))
            stock = StockBodega.objects.get(bodega=bodega, producto=producto, lote=lote)
            stock.cantidad -= peso
            stock._justificacion_auditoria = f'Despacho {pedido.guia_remision}'
            stock.save()
            mov = MovimientoInventario.objects.create(
                tipo_movimiento='VENTA',
                producto=producto,
                lote=lote,
                bodega_origen=bodega,
                cantidad=peso,
                usuario=usuario,
                documento_ref=f'DESP-{pedido.guia_remision}',
                saldo_resultante=stock.cantidad,
            )
            DetalleHistorialDespacho.objects.create(
                historial=historial, lote=lote, producto=producto,
                peso=peso, movimiento_venta=mov,
            )
        pedido.estado = 'despachado'
        pedido.fecha_despacho = timezone.now().date()
        pedido._justificacion_auditoria = 'Despacho de pedido (seed)'
        pedido.save()
        return historial

    # ------------------------------------------------------------------ main
    @transaction.atomic
    def handle(self, *args, **options):
        self._info('== Simulación integral TexCore ==')

        if not options['no_superuser']:
            self._asegurar_superuser()
        self._crear_grupos()
        if not options['no_permissions']:
            self._info('Ejecutando setup_permissions...')
            call_command('setup_permissions')

        self._crear_maestros()
        self._crear_usuarios()
        if not options['sin_credenciales']:
            self._crear_credenciales()

        # A partir de aquí, la parte transaccional. Guarda de idempotencia:
        if LoteProduccion.objects.filter(codigo_lote__startswith='SIM-').exists():
            self._info('La simulación transaccional ya fue sembrada. '
                       'Usa "python manage.py flush_test_data" para reiniciar.')
            self._limpiar_actor()
            self._resumen_cobertura()
            return

        self._crear_clientes()
        self._recepcion_materia_prima()
        self._surtir_quimicos_insumos()
        self._tintorero_crea_formula()
        self._crear_ordenes_produccion()
        self._ejecutar_op_tintura()
        self._transferencia_a_empaque()
        self._empaque_producto_final()
        self._op_en_proceso_y_pendiente()
        self._ventas_despacho_cobranza()
        self._bodeguero_edita_movimiento()

        if not options['sin_mrp']:
            self._ejecutar_mrp()

        self._limpiar_actor()
        self._ok('Base de datos cargada con la simulación integral.')
        self._resumen_cobertura()
        self.stdout.write(f'\nCredenciales de prueba (contraseña: {PASSWORD}):')
        for g in GROUP_NAMES:
            self.stdout.write(f'  • user_{g}')
        self.stdout.write('  • sistemas (superusuario)')

    # -------------------------------------------------------------- setup
    def _asegurar_superuser(self):
        if not CustomUser.objects.filter(username='sistemas').exists():
            CustomUser.objects.create_superuser('sistemas', 'sistemas@example.com', 'Sistemas2026*')
            self._ok('Superusuario "sistemas" creado')
        else:
            self._ok('Superusuario "sistemas" ya existe')

    def _crear_grupos(self):
        for name in GROUP_NAMES:
            Group.objects.get_or_create(name=name)
        self._ok('Grupos de roles asegurados')

    # -------------------------------------------------------------- maestros
    def _crear_maestros(self):
        sede, _ = Sede.objects.get_or_create(
            nombre='Planta Quito', defaults={'location': 'Quito, Ecuador'})
        self.sede = sede

        # Áreas
        self.areas = {}
        for nombre in ['General', 'Tintura', 'Tejido', 'Empaque']:
            self.areas[nombre], _ = Area.objects.get_or_create(nombre=nombre, sede=sede)

        # Bodegas
        self.bodegas = {}
        for nombre in ['Bodega Materia Prima', 'Bodega Línea Tintura', 'Bodega Salida Tintura',
                       'Bodega Tránsito', 'Bodega Químicos', 'Bodega Insumos',
                       'Bodega Producto Terminado']:
            self.bodegas[nombre], _ = Bodega.objects.get_or_create(nombre=nombre, sede=sede)

        # Proveedor
        self.proveedor, _ = Proveedor.objects.get_or_create(
            nombre='Hilanderías del Ecuador S.A.', sede=sede)

        # Productos
        self.productos = {}
        prod_defs = [
            ('HILO-ALG-CRUDO', 'Hilo de Algodón Crudo', 'materia_prima', 'kg', 150, '7.50'),
            ('HILO-ALG-ROJO', 'Hilo de Algodón Teñido Rojo', 'hilo', 'kg', 80, '12.00'),
            ('TELA-ALG-001', 'Tela de Algodón', 'tela', 'metros', 500, '15.00'),
            ('MERMA-HILO-001', 'Retazo/Merma de Hilo (2da)', 'subproducto', 'kg', 0, '3.00'),
            ('QMC-ROJO-001', 'Colorante Rojo Reactivo', 'quimico', 'kg', 15, '25.00'),
            ('QMC-AZUL-001', 'Colorante Azul Reactivo', 'quimico', 'kg', 15, '25.00'),
            ('QMC-FIJ-001', 'Fijador de Color Universal', 'quimico', 'kg', 25, '18.00'),
            ('QMC-DET-001', 'Detergente Industrial', 'quimico', 'kg', 20, '12.00'),
            ('INS-ETQ-001', 'Etiqueta Zebra 100x50mm', 'insumo', 'unidades', 2000, '0.05'),
            ('INS-FUND-001', 'Funda Plástica Industrial', 'insumo', 'unidades', 1000, '0.15'),
            ('INS-CAJA-001', 'Caja de Cartón Corrugado', 'insumo', 'unidades', 500, '0.50'),
        ]
        for codigo, desc, tipo, um, minimo, precio in prod_defs:
            self.productos[codigo], _ = Producto.objects.get_or_create(
                codigo=codigo, sede=sede,
                defaults={
                    'descripcion': desc, 'tipo': tipo, 'unidad_medida': um,
                    'stock_minimo': Decimal(str(minimo)), 'precio_base': Decimal(precio),
                },
            )

        # Batch (lote de compra legacy) para el hilo crudo
        Batch.objects.get_or_create(
            code='BATCH-HILO-2026-001',
            defaults={
                'producto': self.productos['HILO-ALG-CRUDO'],
                'initial_quantity': Decimal('500.000'),
                'current_quantity': Decimal('500.000'),
                'unit_of_measure': 'kg',
            },
        )

        # Máquinas (con bodegas de entrada/salida/merma coherentes)
        self.maquinas = {}
        tintura1, _ = Maquina.objects.get_or_create(
            nombre='Máquina Tintura #1', area=self.areas['Tintura'],
            defaults={
                'capacidad_maxima': Decimal('500.00'), 'eficiencia_ideal': Decimal('0.85'),
                'estado': 'operativa',
                'bodega_entrada': self.bodegas['Bodega Línea Tintura'],
                'bodega_salida': self.bodegas['Bodega Salida Tintura'],
                'producto_merma': self.productos['MERMA-HILO-001'],
                'bodega_merma': self.bodegas['Bodega Salida Tintura'],
            },
        )
        # Asegurar bodegas/merma aunque la máquina ya existiera
        tintura1.bodega_entrada = self.bodegas['Bodega Línea Tintura']
        tintura1.bodega_salida = self.bodegas['Bodega Salida Tintura']
        tintura1.producto_merma = self.productos['MERMA-HILO-001']
        tintura1.bodega_merma = self.bodegas['Bodega Salida Tintura']
        tintura1.save()
        self.maquinas['Tintura #1'] = tintura1

        self.maquinas['Tintura #2'], _ = Maquina.objects.get_or_create(
            nombre='Máquina Tintura #2', area=self.areas['Tintura'],
            defaults={
                'capacidad_maxima': Decimal('500.00'), 'eficiencia_ideal': Decimal('0.85'),
                'estado': 'operativa',
                'bodega_entrada': self.bodegas['Bodega Línea Tintura'],
                'bodega_salida': self.bodegas['Bodega Salida Tintura'],
            },
        )
        self.maquinas['Telar'], _ = Maquina.objects.get_or_create(
            nombre='Telar Automático', area=self.areas['Tejido'],
            defaults={
                'capacidad_maxima': Decimal('1000.00'), 'eficiencia_ideal': Decimal('0.90'),
                'estado': 'operativa',
            },
        )

        # Líneas de Producción (Células de Manufactura Flexibles)
        # 2 activas compartiendo Tintura #1, 1 inactiva, Telar queda sin línea.
        linea_tintura_a, _ = LineaProduccion.objects.get_or_create(
            nombre='Línea Tintura A', area=self.areas['Tintura'],
            defaults={'estado': 'activa', 'descripcion': 'Procesos de tintura reactiva principales'}
        )
        linea_tintura_a.maquinas.add(self.maquinas['Tintura #1'])

        linea_tintura_b, _ = LineaProduccion.objects.get_or_create(
            nombre='Línea Tintura B (Especiales)', area=self.areas['Tintura'],
            defaults={'estado': 'activa', 'descripcion': 'Procesos de tintura colores intensos'}
        )
        linea_tintura_b.maquinas.add(self.maquinas['Tintura #1'], self.maquinas['Tintura #2'])

        linea_inactiva, _ = LineaProduccion.objects.get_or_create(
            nombre='Línea Antigua', area=self.areas['Tintura'],
            defaults={'estado': 'inactiva', 'descripcion': 'Fuera de servicio'}
        )
        linea_inactiva.maquinas.add(self.maquinas['Tintura #2'])

        # ProcessStep + AreaProcessStep + EtapaProduccion
        self.process_steps = {}
        for name in ['Pre-tratamiento', 'Teñido', 'Secado', 'Empaque', 'Control de Calidad']:
            self.process_steps[name], _ = ProcessStep.objects.get_or_create(name=name)

        cfg_area = {
            'Tintura': ['Pre-tratamiento', 'Teñido', 'Secado'],
            'Empaque': ['Empaque', 'Control de Calidad'],
        }
        for area_nombre, pasos in cfg_area.items():
            for i, paso in enumerate(pasos, start=1):
                AreaProcessStep.objects.get_or_create(
                    area=self.areas[area_nombre], proceso=self.process_steps[paso],
                    defaults={'orden': i, 'tipo_flujo': 'secuencial', 'es_bloqueante': True},
                )

        EtapaProduccion.objects.get_or_create(
            area=self.areas['Tintura'], orden=1,
            defaults={
                'nombre': 'Teñido en máquina', 'maquina': tintura1,
                'bodega_entrada': self.bodegas['Bodega Línea Tintura'],
                'bodega_salida': self.bodegas['Bodega Salida Tintura'],
                'tiempo_procesamiento_minutos': 240,
            },
        )
        self._ok('Maestros (áreas, bodegas, productos, máquinas, líneas, procesos) creados')

    def _crear_usuarios(self):
        self.users = {}
        for group_name in GROUP_NAMES:
            username = f'user_{group_name}'
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': group_name.replace('_', ' ').title(),
                    'last_name': 'Demo',
                },
            )
            if created:
                user.set_password(PASSWORD)
            if group_name != 'admin_sistemas':
                user.sede = self.sede
                if group_name in ('tintorero', 'operario'):
                    user.area = self.areas['Tintura']
                elif group_name == 'empaquetado':
                    user.area = self.areas['Empaque']
                elif group_name == 'jefe_area':
                    # El jefe_area gestiona las máquinas de un área real; "General"
                    # no tiene máquinas y dejaría su panel en blanco.
                    user.area = self.areas['Tintura']
                else:
                    user.area = self.areas['General']
                user.save()
                user.bodegas_asignadas.set(list(self.bodegas.values()))
            user.groups.set([Group.objects.get(name=group_name)])
            user.save()
            self.users[group_name] = user

        # Operarios de la máquina de tintura
        self.maquinas['Tintura #1'].operarios.set([self.users['tintorero'], self.users['operario']])

        # Tarifas y costos vigentes (para el costeo)
        hace_60 = (timezone.now() - timedelta(days=60)).date()
        for rol in ('tintorero', 'operario', 'empaquetado'):
            TarifaOperario.objects.get_or_create(
                operario=self.users[rol], vigente_desde=hace_60, sede=self.sede,
                defaults={'tipo_contrato': 'tiempo', 'tarifa_hora': Decimal('4.50')},
            )
        for maq in (self.maquinas['Tintura #1'], self.maquinas['Tintura #2']):
            CostoHoraMaquina.objects.get_or_create(
                maquina=maq, vigente_desde=hace_60,
                defaults={'costo_hora': Decimal('6.00')},
            )
        self._ok('Usuarios por rol, superusuario, tarifas y costos-máquina creados')

    def _crear_credenciales(self):
        self.actuar_como(self.users['admin_sistemas'])
        for name, scopes in [('scanning_service', ['lotes:read']),
                             ('reporting_excel', ['reports:read'])]:
            ServiceCredential.objects.get_or_create(
                name=name,
                defaults={
                    'secret_hash': ServiceCredential.hash_secret('seed-dev-secret'),
                    'allowed_scopes': scopes, 'is_active': True,
                },
            )
        self._ok('Credenciales de microservicios (dev) creadas')

    # -------------------------------------------------------------- negocio
    def _crear_clientes(self):
        self.actuar_como(self.users['vendedor'])
        self.clientes = {}
        defs = [
            ('RUC-001', 'Textiles Andinos S.A.', 'Quito, Pichincha', 'mayorista', '5000.00'),
            ('RUC-002', 'Tejidos del Sur', 'Cuenca, Azuay', 'mayorista', '3000.00'),
            ('RUC-003', 'Moda Express', 'Guayaquil, Guayas', 'normal', '1500.00'),
            ('RUC-004', 'Confecciones Premium', 'Quito, Pichincha', 'normal', '2000.00'),
        ]
        for ruc, nombre, direccion, nivel, limite in defs:
            cliente, _ = Cliente.objects.get_or_create(
                ruc_cedula=ruc, sede=self.sede,
                defaults={
                    'nombre_razon_social': nombre, 'direccion_envio': direccion,
                    'nivel_precio': nivel, 'limite_credito': Decimal(limite),
                    'plazo_credito_dias': 30, 'is_active': True,
                    'vendedor_asignado': self.users['vendedor'],
                },
            )
            self.clientes[ruc] = cliente
        self._ok('Clientes creados (vendedor)')

    def _recepcion_materia_prima(self):
        self.actuar_como(self.users['bodeguero'])
        hoy = timezone.now().date()
        bodega_mp = self.bodegas['Bodega Materia Prima']
        hilo = self.productos['HILO-ALG-CRUDO']
        self.mp_lotes = []
        for i, (cant, dias) in enumerate([(500, 20), (300, 8)], start=1):
            mp = MateriaPrimaService.registrar_entrada(
                proveedor=self.proveedor, producto=hilo,
                lote_proveedor=f'LP-2026-{i:03d}', cantidad_kg=Decimal(str(cant)),
                costo_unitario=Decimal('7.50'), bodega_recepcion=bodega_mp,
                fecha_recepcion=hoy - timedelta(days=dias), usuario=self.users['bodeguero'],
                numero_documento=f'FACT-PROV-{i:03d}',
            )
            self.mp_lotes.append(mp)
        self._ok('Recepción de materia prima (2 lotes, COMPRA en Kardex)')

    def _surtir_quimicos_insumos(self):
        self.actuar_como(self.users['bodeguero'])
        quim = self.bodegas['Bodega Químicos']
        insu = self.bodegas['Bodega Insumos']
        for codigo, cant in [('QMC-ROJO-001', 200), ('QMC-AZUL-001', 200),
                             ('QMC-FIJ-001', 200), ('QMC-DET-001', 200)]:
            self._compra_inicial(self.productos[codigo], quim, cant, self.users['bodeguero'],
                                ref='COMPRA-QUIMICOS')
        for codigo, cant in [('INS-ETQ-001', 10000), ('INS-FUND-001', 5000), ('INS-CAJA-001', 3000)]:
            self._compra_inicial(self.productos[codigo], insu, cant, self.users['bodeguero'],
                                ref='COMPRA-INSUMOS')
        self._ok('Químicos e insumos surtidos (COMPRA en Kardex)')

    def _tintorero_crea_formula(self):
        """El tintorero crea la FormulaColor (en_pruebas -> aprobada) que usará la OP."""
        self.actuar_como(self.users['tintorero'])
        formula, _ = FormulaColor.objects.get_or_create(
            codigo='FORM-ROJO-001', sede=self.sede,
            defaults={
                'nombre_color': 'Rojo Intenso', 'tipo_sustrato': 'algodon',
                'version': 1, 'estado': 'en_pruebas',
                'creado_por': self.users['tintorero'],
                'observaciones': 'Fórmula creada por Tintorería para OP de tintura.',
            },
        )
        fases_cfg = [
            ('pre_tratamiento', 1, 60, 30, [('QMC-DET-001', '3.0', 1)]),
            ('tintura', 2, 90, 90, [('QMC-ROJO-001', '30.0', 1), ('QMC-FIJ-001', '10.0', 2)]),
            ('lavado', 3, 70, 45, [('QMC-DET-001', '2.0', 1)]),
        ]
        for nombre, orden, temp, tiempo, insumos in fases_cfg:
            fase, _ = FaseReceta.objects.get_or_create(
                formula=formula, orden=orden,
                defaults={'nombre': nombre, 'temperatura': temp, 'tiempo': tiempo},
            )
            for codigo, conc, orden_ad in insumos:
                DetalleFormula.objects.get_or_create(
                    fase=fase, producto=self.productos[codigo],
                    defaults={
                        'tipo_calculo': 'gr_l',
                        'concentracion_gr_l': Decimal(conc),
                        'orden_adicion': orden_ad,
                    },
                )
        # Aprobación de la fórmula (UPDATE auditable: requiere justificación)
        if formula.estado != 'aprobada':
            formula.estado = 'aprobada'
            formula._justificacion_auditoria = 'Aprobación de fórmula tras pruebas de laboratorio.'
            formula.save()
        self.formula_rojo = formula
        self._ok('Tintorero creó y aprobó la fórmula "Rojo Intenso"')

    def _crear_ordenes_produccion(self):
        """jefe_planta crea las OPs; jefe_area asigna máquina + operario y genera subprocesos."""
        ahora = timezone.now()
        self.ordenes = {}

        # jefe_planta crea las 4 órdenes (auditadas a su nombre)
        self.actuar_como(self.users['jefe_planta'])
        plan = [
            ('OP-SIM-001', 'Tintura', '100.00', 'alta'),
            ('OP-SIM-002', 'Empaque', '95.00', 'normal'),
            ('OP-SIM-003', 'Tintura', '120.00', 'normal'),
            ('OP-SIM-004', 'Tintura', '80.00', 'baja'),
        ]
        for codigo, area, peso, prioridad in plan:
            orden, _ = OrdenProduccion.objects.get_or_create(
                codigo=codigo, sede=self.sede,
                defaults={
                    'area': self.areas[area],
                    'peso_neto_requerido': Decimal(peso),
                    'prioridad': prioridad,
                    'observaciones': f'Orden creada por Jefe de Planta ({area}).',
                },
            )
            self.ordenes[codigo] = orden

        # jefe_area asigna detalles (máquina, operario, bodegas, fórmula) — UPDATE auditable
        self.actuar_como(self.users['jefe_area'])
        hilo_crudo = self.productos['HILO-ALG-CRUDO']
        hilo_rojo = self.productos['HILO-ALG-ROJO']

        def asignar_tintura(orden, maquina, operario):
            orden.producto_entrada = hilo_crudo
            orden.producto_salida = hilo_rojo
            orden.formula_color = self.formula_rojo
            orden.bodega_quimicos = self.bodegas['Bodega Químicos']
            orden.bodega_entrada = self.bodegas['Bodega Línea Tintura']
            orden.bodega_salida = self.bodegas['Bodega Salida Tintura']
            orden.maquina_asignada = maquina
            orden.operario_asignado = operario
            orden.fecha_inicio_planificada = ahora.date()
            orden.fecha_fin_planificada = (ahora + timedelta(days=2)).date()
            orden._justificacion_auditoria = 'Asignación de máquina y operario (Jefe de Área).'
            orden.save()
            self._crear_subprocesos(orden)

        asignar_tintura(self.ordenes['OP-SIM-001'], self.maquinas['Tintura #1'], self.users['tintorero'])
        asignar_tintura(self.ordenes['OP-SIM-003'], self.maquinas['Tintura #2'], self.users['operario'])
        asignar_tintura(self.ordenes['OP-SIM-004'], self.maquinas['Tintura #1'], self.users['operario'])

        # OP de empaque: entrada = producto teñido, salida = producto teñido (empacado)
        op2 = self.ordenes['OP-SIM-002']
        op2.producto_entrada = hilo_rojo
        op2.producto_salida = hilo_rojo
        op2.bodega_entrada = self.bodegas['Bodega Producto Terminado']
        op2.bodega_salida = self.bodegas['Bodega Producto Terminado']
        op2.operario_asignado = self.users['empaquetado']
        op2._justificacion_auditoria = 'Asignación de operario de empaque (Jefe de Área).'
        op2.save()
        self._crear_subprocesos(op2)

        # Jefe de área define una receta de mezcla para OP-SIM-004 (componentes %)
        op4 = self.ordenes['OP-SIM-004']
        mezcla = [
            (hilo_crudo, self.bodegas['Bodega Línea Tintura'], Decimal('70.00'), Decimal('56.000')),
            (hilo_rojo, self.bodegas['Bodega Producto Terminado'], Decimal('30.00'), Decimal('24.000')),
        ]
        for producto, bodega, pct, kg in mezcla:
            ComponenteMezclaOP.objects.get_or_create(
                orden=op4, producto=producto,
                defaults={'bodega': bodega, 'porcentaje': pct, 'cantidad_kg': kg},
            )
        self._ok('4 OPs creadas (Jefe de Planta), asignadas con subprocesos y receta de mezcla (Jefe de Área)')

    def _ejecutar_op_tintura(self):
        """OP-SIM-001 finalizada: abastecimiento, descarga química, avance, transformación,
        lote, trazabilidad y costeo."""
        op = self.ordenes['OP-SIM-001']
        ahora = timezone.now()
        hilo_crudo = self.productos['HILO-ALG-CRUDO']

        # Abastecimiento a línea de tintura vía protocolo 3-fase (stock a granel, sin lote)
        self.actuar_como(self.users['bodeguero'])
        mov = TransicionBodegaService.iniciar_transicion(
            producto=hilo_crudo,
            bodega_origen=self.bodegas['Bodega Materia Prima'],
            bodega_destino=self.bodegas['Bodega Línea Tintura'],
            bodega_transicion=self.bodegas['Bodega Tránsito'],
            cantidad=Decimal('300'), usuario=self.users['bodeguero'],
            documento_ref='ABAST-LINEA-TINTURA',
        )
        TransicionBodegaService.completar_transicion(mov, self.users['bodeguero'])

        # Descarga automática de químicos según la fórmula (tintorero)
        self.actuar_como(self.users['tintorero'])
        DescargaQuimicosService.descargar_para_op(op, self.users['tintorero'])

        # El operario registra el avance de los subprocesos
        self.actuar_como(self.users['tintorero'])
        for sub in OrdenProduccionSubproceso.objects.filter(orden_produccion=op).order_by('area_proceso__orden'):
            self._avanzar_subproceso(sub, 'en_progreso', self.users['tintorero'])
            self._avanzar_subproceso(sub, 'completado', self.users['tintorero'],
                                     obs='Subproceso completado en tintura.')

        # Transformación hilo crudo -> hilo teñido (con merma)
        TransformacionService.registrar(op, {
            'maquina': self.maquinas['Tintura #1'],
            'producto_salida': self.productos['HILO-ALG-ROJO'],
            'peso_entrada': Decimal('100'), 'peso_salida': Decimal('95'),
            'fecha_inicio': ahora - timedelta(hours=5), 'fecha_fin': ahora - timedelta(hours=1),
            'operario': self.users['tintorero'],
            'observaciones': 'Teñido rojo intenso.',
        }, self.users['tintorero'])

        # Registro del lote de producción (consume MP, produce PT, merma vendible)
        lote = RegistroLoteService.registrar_lote(op, {
            'codigo_lote': 'SIM-001-L1',
            'peso_neto_producido': Decimal('95'), 'peso_merma': Decimal('5'),
            'tipo_merma': 'setup', 'clasificacion_calidad': 'primera',
            'maquina': self.maquinas['Tintura #1'], 'operario': self.users['tintorero'].id,
            'turno': 'Matutino',
            'hora_inicio': ahora - timedelta(hours=5), 'hora_final': ahora - timedelta(hours=1),
            'presentacion': 'cono',
        }, self.users['tintorero'], completar_orden=True)
        self.lote_op1 = lote

        # Trazabilidad: vincular el lote con el lote de MP del proveedor
        MateriaPrimaService.consumir_materia_prima(
            lote, [{'materia_prima_lote_id': self.mp_lotes[0].id, 'cantidad_kg': Decimal('100')}],
            self.users['tintorero'],
        )

        # Costeo del lote (MP + químicos + operario + máquina) -> margen
        CostoLoteService.calcular_costo(lote, self.users['jefe_area'])
        self._ok('OP-SIM-001 producida: descarga química, avance, transformación, lote, trazabilidad y costeo')

    def _transferencia_a_empaque(self):
        """Transfiere el lote terminado de Salida Tintura a Producto Terminado (Empaque)."""
        self.actuar_como(self.users['bodeguero'])
        self._transferir_lote(
            lote=self.lote_op1, producto=self.productos['HILO-ALG-ROJO'],
            b_origen=self.bodegas['Bodega Salida Tintura'],
            b_destino=self.bodegas['Bodega Producto Terminado'],
            cantidad=Decimal('95'), usuario=self.users['bodeguero'],
            op_o=self.ordenes['OP-SIM-001'], op_d=self.ordenes['OP-SIM-002'],
        )
        self._ok('Transferencia interárea Tintura → Empaque (lote movido a PT)')

    def _empaque_producto_final(self):
        """El empaquetado completa los subprocesos y empaca el lote (etiqueta lista)."""
        op2 = self.ordenes['OP-SIM-002']
        self.actuar_como(self.users['empaquetado'])
        for sub in OrdenProduccionSubproceso.objects.filter(orden_produccion=op2).order_by('area_proceso__orden'):
            self._avanzar_subproceso(sub, 'completado', self.users['empaquetado'],
                                     obs='Empaque y control de calidad OK.')
        # Empaque del lote: datos completos para la etiqueta ZPL
        lote = self.lote_op1
        lote.presentacion = 'funda'           # clean() ajusta unidades_empaque=15
        lote.tara = Decimal('3.000')
        lote.peso_bruto = Decimal('98.000')   # neto 95 + tara 3
        lote.save()
        op2.estado = 'finalizada'
        op2._justificacion_auditoria = 'Empaque finalizado (seed).'
        op2.save()
        self._ok('OP-SIM-002: lote empacado (etiqueta ZPL lista) en Producto Terminado')

    def _op_en_proceso_y_pendiente(self):
        """OP-SIM-003 en proceso (avance en vivo) y OP-SIM-004 pendiente."""
        op3 = self.ordenes['OP-SIM-003']
        # Abastecer un poco de MP a la línea para que la descarga tenga contexto
        self.actuar_como(self.users['tintorero'])
        DescargaQuimicosService.descargar_para_op(op3, self.users['tintorero'])
        subs = list(OrdenProduccionSubproceso.objects.filter(orden_produccion=op3).order_by('area_proceso__orden'))
        if subs:
            self._avanzar_subproceso(subs[0], 'completado', self.users['operario'],
                                     obs='Pre-tratamiento listo.')
        if len(subs) > 1:
            self._avanzar_subproceso(subs[1], 'en_progreso', self.users['operario'],
                                     obs='Teñido en curso.')
        op3.estado = 'en_proceso'
        op3._justificacion_auditoria = 'OP en proceso (seed).'
        op3.save()
        # OP-SIM-004 queda pendiente con subprocesos pendientes (ya creados)
        self._ok('OP-SIM-003 en proceso (avance en vivo) y OP-SIM-004 pendiente')

    def _ventas_despacho_cobranza(self):
        self.actuar_como(self.users['vendedor'])
        hoy = timezone.now().date()
        hilo_rojo = self.productos['HILO-ALG-ROJO']
        bodega_pt = self.bodegas['Bodega Producto Terminado']

        def crear_pedido(guia, cliente, estado, dias_venc, producto, peso, precio, lote=None):
            pedido, _ = PedidoVenta.objects.get_or_create(
                guia_remision=guia,
                defaults={
                    'cliente': cliente, 'estado': estado, 'sede': self.sede,
                    'vendedor_asignado': self.users['vendedor'],
                    'fecha_vencimiento': hoy + timedelta(days=dias_venc),
                    'valor_retencion': Decimal('0.00'),
                },
            )
            DetallePedido.objects.get_or_create(
                pedido_venta=pedido, producto=producto,
                defaults={
                    'lote': lote, 'cantidad': int(peso), 'piezas': 10,
                    'peso': Decimal(str(peso)), 'precio_unitario': Decimal(str(precio)),
                    'incluye_iva': True,
                },
            )
            return pedido

        # Pedido 1: se despacha (parcial, deja stock escaneable) y se paga completo
        p1 = crear_pedido('GR-SIM-001', self.clientes['RUC-001'], 'pendiente', 30,
                          hilo_rojo, 50, '14.00', lote=self.lote_op1)
        self.actuar_como(self.users['despacho'])
        self._registrar_despacho(p1, [(self.lote_op1, hilo_rojo, Decimal('50'))],
                                 self.users['despacho'], bodega_pt)

        # Pedido 2: facturado, vencido, sin pagar -> cartera vencida
        self.actuar_como(self.users['vendedor'])
        crear_pedido('GR-SIM-002', self.clientes['RUC-002'], 'facturado', -5,
                     hilo_rojo, 30, '14.00')
        # Pedido 3: pendiente
        crear_pedido('GR-SIM-003', self.clientes['RUC-003'], 'pendiente', 20,
                     hilo_rojo, 20, '15.00')
        # Pedido 4: pago parcial
        p4 = crear_pedido('GR-SIM-004', self.clientes['RUC-004'], 'pendiente', 15,
                          hilo_rojo, 40, '15.00')

        # Pagos (vendedor) + reconciliación FIFO
        valor_p1 = sum(d.total_con_iva for d in p1.detalles.all())
        PagoCliente.objects.create(cliente=self.clientes['RUC-001'], monto=valor_p1,
                                   metodo_pago='transferencia', comprobante='TRF-001')
        PaymentReconciler.reconcile_client_orders(self.clientes['RUC-001'])

        valor_p4 = sum(d.total_con_iva for d in p4.detalles.all())
        PagoCliente.objects.create(cliente=self.clientes['RUC-004'],
                                   monto=(valor_p4 * Decimal('0.4')).quantize(Decimal('0.001')),
                                   metodo_pago='efectivo', comprobante='EF-004')
        PaymentReconciler.reconcile_client_orders(self.clientes['RUC-004'])

        # Reversión de un pago (demostración del servicio): pago erróneo -> revertido
        pago_err = PagoCliente.objects.create(cliente=self.clientes['RUC-003'],
                                              monto=Decimal('100.00'), metodo_pago='efectivo',
                                              comprobante='EF-ERR', notas='Pago erróneo (demo)')
        PagoReversionService.revertir_pago(pago_err, self.users['vendedor'],
                                           'Reversión: pago registrado por error (seed).')
        PaymentReconciler.reconcile_client_orders(self.clientes['RUC-003'])
        self._ok('Ventas, despacho por escaneo y cobranza (pago total, parcial, cartera vencida, reversión)')

    def _bodeguero_edita_movimiento(self):
        """El bodeguero corrige un movimiento -> genera AuditoriaMovimiento."""
        from inventory.models import AuditoriaMovimiento
        self.actuar_como(self.users['bodeguero'])
        mov = MovimientoInventario.objects.filter(
            tipo_movimiento='COMPRA', documento_ref='COMPRA-QUIMICOS').first()
        if mov:
            anterior = mov.observaciones or ''
            mov.observaciones = 'Corrección: factura de proveedor verificada.'
            mov.editado = True
            mov.fecha_ultima_edicion = timezone.now()
            mov._justificacion_auditoria = 'Corrección de datos de compra (seed).'
            mov.save()
            AuditoriaMovimiento.objects.create(
                movimiento=mov, usuario_modificador=self.users['bodeguero'],
                campo_modificado='observaciones', valor_anterior=anterior,
                valor_nuevo=mov.observaciones, razon_cambio='Verificación de factura.',
            )
            self._ok('Bodeguero editó un movimiento (AuditoriaMovimiento generada)')

    def _ejecutar_mrp(self):
        """Ejecuta el motor MRP -> RequerimientoMaterial + OrdenCompraSugerida."""
        from inventory.services.mrp_engine import MRPEngine
        engine = MRPEngine()
        engine.ejecutar_mrp()
        self._ok(f'MRP ejecutado ({engine.requerimientos_generados} requerimientos, '
                 f'{engine.ocs_generadas} órdenes de compra sugeridas)')

    # -------------------------------------------------------------- resumen
    def _resumen_cobertura(self):
        from django.apps import apps
        self.stdout.write('\nCobertura de modelos (registros por modelo):')
        vacios = []
        for model in apps.get_app_config('gestion').get_models():
            n = model.objects.count()
            if n == 0:
                vacios.append(model.__name__)
        for model in apps.get_app_config('inventory').get_models():
            n = model.objects.count()
            if n == 0:
                vacios.append(model.__name__)
        if vacios:
            self.stdout.write(self.style.WARNING(
                '  Modelos sin registros: ' + ', '.join(sorted(vacios))))
        else:
            self._ok('Todos los modelos de gestion/inventory tienen registros')
