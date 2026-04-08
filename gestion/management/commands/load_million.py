"""
Carga ~1,000,000 registros para estresar el aplicativo TexCore.

Usa bulk_create() para bypasear AuditableModelMixin.save() y ser rápido.
Distribuye fechas aleatoriamente sobre los últimos 12 meses via SQL crudo al final.

Distribución objetivo:
  Fase 1 - Master data        :      ~150 registros
  Fase 2 - Productos           :    1 000 registros
  Fase 3 - Fórmulas            :    1 000 registros (250 formulas + 750 detalles)
  Fase 4 - Clientes            :   10 000 registros
  Fase 5 - Órdenes producción  :   20 000 registros
  Fase 6 - Lotes producción    :   80 000 registros
  Fase 7 - Pedidos + Detalles  :  150 000 registros (30K pedidos + 120K detalles)
  Fase 8 - Stock               :   20 000 registros
  Fase 9 - Movimientos inv.    :  750 000 registros  ← volumen principal
  ──────────────────────────────────────────────────
  TOTAL                        : ~1 032 150 registros

Uso:
  python manage.py load_million
  python manage.py load_million --fase 9          # solo movimientos
  python manage.py load_million --batch 5000       # tamaño de lote
  python manage.py load_million --movimientos 500000
"""

import random
import time
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from gestion.models import (
    Area, Bodega, Cliente, CustomUser, DetalleFormula, DetallePedido,
    FaseReceta, FormulaColor, LoteProduccion, Maquina, OrdenProduccion,
    PedidoVenta, Producto, Proveedor, Sede,
)
from inventory.models import MovimientoInventario, StockBodega

# ─── Constantes ────────────────────────────────────────────────────────────────

TIPOS_MOV = ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'AJUSTE', 'VENTA', 'CONSUMO', 'DEVOLUCION']
TIPOS_PROD = ['hilo', 'tela', 'quimico', 'insumo', 'subproducto']
UNIDADES = ['kg', 'metros', 'unidades', 'litros']
ESTADOS_OP = ['pendiente', 'en_proceso', 'finalizada']
ESTADOS_PED = ['pendiente', 'despachado', 'facturado']
TURNOS = ['Matutino', 'Vespertino', 'Nocturno']
PAISES = ['Ecuador', 'Colombia', 'Peru', 'Brasil', 'China', 'India', 'Italia']
PRESENTACIONES = ['cono', 'funda', 'caja', 'rollo', 'saco']
METODOS_PAGO = ['transferencia', 'efectivo', 'cheque', 'tarjeta']

NOMBRES_CLIENTES = [
    'Textiles del Sur', 'Hilandería Andina', 'Confecciones Express', 'Almacén La Esquina',
    'Distribuidora Norte', 'Mayorista Textil', 'Boutique Moda', 'Industrias Creativas',
    'Comercial El Ahorro', 'Importadora Quito', 'Exportadora Ecuador', 'Fábrica Moderna',
    'Corporación Textil', 'Grupo Industrial', 'Cadena de Tiendas', 'Cooperativa Artesanal',
    'Tejidos Nacionales', 'Moda Urbana', 'Confecciones del Valle', 'Artesanías del Norte',
    'Fábrica San Miguel', 'Textil Pichincha', 'Hilados del Pacífico', 'Industria Textil SA',
]


def _rnd_decimal(lo: float, hi: float, decimals: int = 2) -> Decimal:
    val = random.uniform(lo, hi)
    quantize_str = '0.' + '0' * decimals
    return Decimal(val).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def _progress(stdout, label: str, done: int, total: int, start: float):
    pct = done / total * 100
    elapsed = time.time() - start
    rate = done / elapsed if elapsed > 0 else 0
    remaining = (total - done) / rate if rate > 0 else 0
    stdout.write(
        f'  {label}: {done:>8,}/{total:,} ({pct:5.1f}%) '
        f'| {rate:,.0f} reg/s | ETA {remaining:,.0f}s   ',
        ending='\r'
    )
    stdout.flush()


# ─── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Carga ~1 000 000 de registros para estresar el aplicativo TexCore.'

    def add_arguments(self, parser):
        parser.add_argument('--fase', type=int, default=0,
                            help='Ejecutar solo una fase (1-9). 0 = todas.')
        parser.add_argument('--batch', type=int, default=5000,
                            help='Tamaño de lote para bulk_create (default: 5 000).')
        parser.add_argument('--movimientos', type=int, default=750_000,
                            help='Número de movimientos a generar (default: 750 000).')
        parser.add_argument('--pedidos', type=int, default=30_000,
                            help='Número de pedidos de venta (default: 30 000).')
        parser.add_argument('--ordenes', type=int, default=20_000,
                            help='Número de órdenes de producción (default: 20 000).')

    def handle(self, *args, **options):
        fase = options['fase']
        batch_size = options['batch']
        num_movimientos = options['movimientos']
        num_pedidos = options['pedidos']
        num_ordenes = options['ordenes']

        self.stdout.write(self.style.SUCCESS(
            f'\n{"═" * 60}\n'
            f'  load_million — TexCore Stress Data Loader\n'
            f'  Target: ~{num_movimientos + num_pedidos * 5 + num_ordenes * 5:,} registros\n'
            f'  Batch size: {batch_size:,}\n'
            f'{"═" * 60}\n'
        ))

        fases = {
            1: ('Master data (sedes, bodegas, máquinas, proveedores)', self._fase1_master),
            2: ('Productos (1 000)', self._fase2_productos),
            3: ('Fórmulas color (250 + 750 detalles)', self._fase3_formulas),
            4: ('Clientes (10 000)', self._fase4_clientes),
            5: (f'Órdenes de producción ({num_ordenes:,})', self._fase5_ordenes),
            6: ('Lotes de producción (~4× órdenes)', self._fase6_lotes),
            7: (f'Pedidos de venta ({num_pedidos:,} + detalles)', self._fase7_pedidos),
            8: ('Stock bodega (productos × bodegas)', self._fase8_stock),
            9: (f'Movimientos inventario ({num_movimientos:,})', self._fase9_movimientos),
        }

        total_start = time.time()
        ctx = {}  # shared context between phases

        for num, (desc, fn) in fases.items():
            if fase != 0 and fase != num:
                continue
            self.stdout.write(f'\n{"─" * 60}')
            self.stdout.write(self.style.HTTP_INFO(f'  FASE {num}: {desc}'))
            self.stdout.write(f'{"─" * 60}')
            t0 = time.time()
            fn(ctx, batch_size, num_movimientos=num_movimientos,
               num_pedidos=num_pedidos, num_ordenes=num_ordenes)
            elapsed = time.time() - t0
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Fase {num} completada en {elapsed:.1f}s'))

        if fase == 0 or fase == 9:
            self.stdout.write(f'\n{"─" * 60}')
            self.stdout.write(self.style.HTTP_INFO('  POST-PROCESO: Distribuyendo fechas en los últimos 12 meses...'))
            self._randomize_dates()
            self.stdout.write(self.style.SUCCESS('  ✓ Fechas distribuidas'))

        total_elapsed = time.time() - total_start
        self._print_summary(total_elapsed)

    # ─── FASE 1: Master data ──────────────────────────────────────────────────

    def _fase1_master(self, ctx, batch_size, **kw):
        # Sedes
        sedes = []
        for nombre, loc in [
            ('Sede Principal', 'Quito Centro, Ecuador'),
            ('Sede Norte', 'Quito Norte, Ecuador'),
            ('Sede Calderón', 'Calderón, Ecuador'),
            ('Sede Cumbayá', 'Cumbayá, Ecuador'),
        ]:
            s, _ = Sede.objects.get_or_create(nombre=nombre, defaults={'location': loc})
            sedes.append(s)
        ctx['sedes'] = sedes

        # Áreas (3 por sede)
        areas = []
        area_nombres = ['Producción', 'Tintorería', 'Empaque']
        for sede in sedes:
            for an in area_nombres:
                a, _ = Area.objects.get_or_create(nombre=f'{an} {sede.nombre}', defaults={'sede': sede})
                areas.append(a)
        ctx['areas'] = areas

        # Bodegas (3 por sede: MP, PT, Insumos)
        bodegas = []
        for sede in sedes:
            for sufijo in ['Materia Prima', 'Producto Terminado', 'Insumos']:
                b, _ = Bodega.objects.get_or_create(nombre=f'Bodega {sufijo} {sede.nombre}', defaults={'sede': sede})
                bodegas.append(b)
        ctx['bodegas'] = bodegas
        ctx['bodegas_mp'] = [b for i, b in enumerate(bodegas) if i % 3 == 0]
        ctx['bodegas_pt'] = [b for i, b in enumerate(bodegas) if i % 3 == 1]

        # Máquinas (5 por sede = 20 total)
        maquinas = []
        for sede_idx, sede in enumerate(sedes):
            area_prod = next((a for a in areas if 'Producción' in a.nombre and sede.nombre in a.nombre), areas[0])
            for i in range(5):
                m, _ = Maquina.objects.get_or_create(
                    nombre=f'Maquina-S{sede_idx+1}-{i+1:02d}',
                    defaults={
                        'capacidad_maxima': Decimal('600.00'),
                        'eficiencia_ideal': Decimal('0.92'),
                        'estado': 'operativa',
                        'area': area_prod,
                    }
                )
                maquinas.append(m)
        ctx['maquinas'] = maquinas

        # Proveedores (25 por sede = 100 total)
        proveedores = []
        for sede in sedes:
            for i in range(25):
                p, _ = Proveedor.objects.get_or_create(
                    nombre=f'Proveedor {sede.nombre[:5]} {i+1:03d} S.A.',
                    defaults={'sede': sede}
                )
                proveedores.append(p)
        ctx['proveedores'] = proveedores

        # Usuario operario para asignar
        grupos = {}
        for gname in ['operario', 'bodeguero', 'vendedor', 'ejecutivo', 'admin_sistemas']:
            g, _ = Group.objects.get_or_create(name=gname)
            grupos[gname] = g

        operario, created = CustomUser.objects.get_or_create(
            username='operario_stress',
            defaults={'email': 'operario_stress@test.com', 'sede': sedes[0]}
        )
        if created:
            operario.set_password('password123')
            operario.groups.add(grupos['operario'])
            operario.save()
        ctx['operario'] = operario

        vendedor, created = CustomUser.objects.get_or_create(
            username='vendedor_stress',
            defaults={'email': 'vendedor_stress@test.com', 'sede': sedes[0]}
        )
        if created:
            vendedor.set_password('password123')
            vendedor.groups.add(grupos['vendedor'])
            vendedor.save()
        ctx['vendedor'] = vendedor

        self.stdout.write(
            f'  Sedes: {len(sedes)} | Bodegas: {len(bodegas)} | '
            f'Máquinas: {len(maquinas)} | Proveedores: {len(proveedores)}'
        )

    # ─── FASE 2: Productos ────────────────────────────────────────────────────

    def _fase2_productos(self, ctx, batch_size, **kw):
        TARGET = 1_000
        existing = Producto.objects.filter(codigo__startswith='STR-PROD-').count()
        to_create = max(0, TARGET - existing)

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing:,} productos STR-PROD-*. Omitiendo.')
        else:
            self.stdout.write(f'  Creando {to_create:,} productos con bulk_create...')
            t0 = time.time()
            objs = [
                Producto(
                    codigo=f'STR-PROD-{existing + i + 1:06d}',
                    descripcion=f'Producto Stress {existing + i + 1} - {random.choice(TIPOS_PROD).title()}',
                    tipo=random.choice(TIPOS_PROD),
                    unidad_medida=random.choice(UNIDADES),
                    stock_minimo=_rnd_decimal(5, 200),
                    precio_base=_rnd_decimal(1.5, 120.0),
                )
                for i in range(to_create)
            ]
            for i in range(0, len(objs), batch_size):
                batch = objs[i:i + batch_size]
                Producto.objects.bulk_create(batch, batch_size=batch_size, )
                _progress(self.stdout, 'Productos', min(i + batch_size, to_create), to_create, t0)

        ctx['productos'] = list(Producto.objects.filter(precio_base__gt=0).values_list('id', 'tipo', 'precio_base'))
        ctx['hilos_telas_ids'] = [p[0] for p in ctx['productos'] if p[1] in ('hilo', 'tela', 'subproducto')]
        if not ctx['hilos_telas_ids']:
            ctx['hilos_telas_ids'] = [p[0] for p in ctx['productos'][:100]]
        self.stdout.write(f'\n  Total productos disponibles: {len(ctx["productos"]):,}')

    # ─── FASE 3: Fórmulas ─────────────────────────────────────────────────────

    def _fase3_formulas(self, ctx, batch_size, **kw):
        TARGET = 250
        existing = FormulaColor.objects.filter(codigo__startswith='STR-FORM-').count()
        to_create = max(0, TARGET - existing)

        colores = [
            'Negro Intenso', 'Blanco Óptico', 'Rojo Carmesí', 'Azul Marino',
            'Verde Esmeralda', 'Amarillo Oro', 'Naranja Flúor', 'Gris Perla',
            'Café Chocolate', 'Lila Pastel', 'Rosa Fucsia', 'Beige Natural',
            'Turquesa Mar', 'Borgoña Oscuro', 'Lima Vibrante', 'Coral Suave',
        ]

        if to_create > 0:
            formulas_nuevas = []
            for i in range(to_create):
                color_base = random.choice(colores)
                formulas_nuevas.append(FormulaColor(
                    codigo=f'STR-FORM-{existing + i + 1:04d}',
                    nombre_color=f'{color_base} Stress {existing + i + 1}',
                ))
            FormulaColor.objects.bulk_create(formulas_nuevas, batch_size=batch_size, )
            self.stdout.write(f'  {to_create} fórmulas creadas')

        formulas = list(FormulaColor.objects.values_list('id', flat=True))
        ctx['formulas'] = formulas

        # FaseReceta: 1 fase 'tintura' por formula STR-FORM (requerida por DetalleFormula)
        quimicos = list(Producto.objects.filter(tipo='quimico').values_list('id', flat=True)[:100])
        if not quimicos:
            quimicos = list(Producto.objects.values_list('id', flat=True)[:20])

        formulas_str = list(FormulaColor.objects.filter(codigo__startswith='STR-FORM-'))
        fases_existentes = set(
            FaseReceta.objects.filter(formula__in=formulas_str).values_list('formula_id', flat=True)
        )

        fases_nuevas = []
        for f in formulas_str:
            if f.id not in fases_existentes:
                fases_nuevas.append(FaseReceta(
                    formula=f,
                    nombre='tintura',
                    orden=1,
                    temperatura=90,
                    tiempo=60,
                ))
        if fases_nuevas:
            FaseReceta.objects.bulk_create(fases_nuevas, batch_size=batch_size, )
            self.stdout.write(f'  {len(fases_nuevas)} fases de receta creadas')

        # DetalleFormula: hasta 3 químicos por fase
        fases = list(FaseReceta.objects.filter(formula__in=formulas_str).values_list('id', flat=True))
        existing_det = DetalleFormula.objects.filter(fase_id__in=fases).count()

        if existing_det < len(fases) * 2 and quimicos and fases:
            detalles = []
            for fase_id in fases:
                for q_id in random.sample(quimicos, k=min(3, len(quimicos))):
                    detalles.append(DetalleFormula(
                        fase_id=fase_id,
                        producto_id=q_id,
                        gramos_por_kilo=_rnd_decimal(5, 80),
                        tipo_calculo=random.choice(['gr_l', 'pct']),
                        orden_adicion=random.randint(1, 5),
                    ))
            DetalleFormula.objects.bulk_create(detalles, batch_size=batch_size, )
            self.stdout.write(f'  {len(detalles)} detalles de fórmula creados')

        self.stdout.write(f'  Total fórmulas disponibles: {len(formulas):,}')

    # ─── FASE 4: Clientes ─────────────────────────────────────────────────────

    def _fase4_clientes(self, ctx, batch_size, **kw):
        TARGET = 10_000
        existing = Cliente.objects.filter(ruc_cedula__startswith='STR').count()
        to_create = max(0, TARGET - existing)

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing:,} clientes STR*. Omitiendo.')
        else:
            self.stdout.write(f'  Creando {to_create:,} clientes...')
            t0 = time.time()
            sedes = ctx.get('sedes') or list(Sede.objects.all())
            vendedor = ctx.get('vendedor')

            objs = []
            for i in range(to_create):
                nombre_base = random.choice(NOMBRES_CLIENTES)
                sufijo = existing + i + 1
                objs.append(Cliente(
                    ruc_cedula=f'STR{sufijo:010d}',
                    nombre_razon_social=f'{nombre_base} #{sufijo} S.A.',
                    direccion_envio=f'Calle {random.randint(1, 999)} y Av. {random.randint(1, 50)}',
                    nivel_precio=random.choice(['mayorista', 'normal']),
                    tiene_beneficio=random.random() < 0.20,
                    limite_credito=Decimal(random.randint(1_000, 100_000)),
                    plazo_credito_dias=random.choice([0, 8, 15, 30, 45, 60, 90]),
                    vendedor_asignado=vendedor,
                ))
                if len(objs) >= batch_size:
                    Cliente.objects.bulk_create(objs, batch_size=batch_size, )
                    _progress(self.stdout, 'Clientes', min(i + 1, to_create), to_create, t0)
                    objs = []
            if objs:
                Cliente.objects.bulk_create(objs, batch_size=batch_size, )

        ctx['clientes_ids'] = list(Cliente.objects.values_list('id', flat=True))
        self.stdout.write(f'\n  Total clientes: {len(ctx["clientes_ids"]):,}')

    # ─── FASE 5: Órdenes de producción ────────────────────────────────────────

    def _fase5_ordenes(self, ctx, batch_size, num_ordenes=20_000, **kw):
        existing = OrdenProduccion.objects.filter(codigo__startswith='STR-OP-').count()
        to_create = max(0, num_ordenes - existing)

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing:,} órdenes STR-OP-*. Omitiendo.')
        else:
            self.stdout.write(f'  Creando {to_create:,} órdenes de producción...')
            t0 = time.time()
            productos_ids = ctx.get('hilos_telas_ids') or list(Producto.objects.values_list('id', flat=True)[:200])
            formulas = ctx.get('formulas') or list(FormulaColor.objects.values_list('id', flat=True))
            bodegas_mp = ctx.get('bodegas_mp') or list(Bodega.objects.all()[:4])
            maquinas = ctx.get('maquinas') or list(Maquina.objects.all())
            operario = ctx.get('operario') or CustomUser.objects.filter(is_superuser=False).first()
            sedes = ctx.get('sedes') or list(Sede.objects.all())
            areas = ctx.get('areas') or list(Area.objects.all())

            objs = []
            now = timezone.now()
            for i in range(to_create):
                n = existing + i + 1
                estado = random.choices(ESTADOS_OP, weights=[20, 30, 50])[0]
                objs.append(OrdenProduccion(
                    codigo=f'STR-OP-{n:07d}',
                    producto_id=random.choice(productos_ids),
                    formula_color_id=random.choice(formulas) if formulas else None,
                    bodega=random.choice(bodegas_mp),
                    area=random.choice(areas) if areas else None,
                    peso_neto_requerido=_rnd_decimal(50, 2000),
                    estado=estado,
                    maquina_asignada=random.choice(maquinas) if maquinas else None,
                    operario_asignado=operario,
                    sede=random.choice(sedes),
                ))
                if len(objs) >= batch_size:
                    OrdenProduccion.objects.bulk_create(objs, batch_size=batch_size, )
                    _progress(self.stdout, 'Órdenes', min(i + 1, to_create), to_create, t0)
                    objs = []
            if objs:
                OrdenProduccion.objects.bulk_create(objs, batch_size=batch_size, )

        ctx['ordenes_ids'] = list(
            OrdenProduccion.objects.filter(estado='finalizada').values_list('id', flat=True)
        )
        self.stdout.write(f'\n  Total órdenes: {OrdenProduccion.objects.filter(codigo__startswith="STR-OP-").count():,}')

    # ─── FASE 6: Lotes de producción ──────────────────────────────────────────

    def _fase6_lotes(self, ctx, batch_size, **kw):
        ordenes_ids = ctx.get('ordenes_ids') or list(
            OrdenProduccion.objects.filter(estado='finalizada').values_list('id', flat=True)
        )
        if not ordenes_ids:
            self.stdout.write('  No hay órdenes finalizadas. Omitiendo lotes.')
            ctx['lotes_ids'] = []
            return

        # Cuántos lotes hay que crear: ~4 por orden, máximo 80K
        existing_lotes = LoteProduccion.objects.filter(codigo_lote__startswith='STR-LOTE-').count()
        TARGET_LOTES = min(len(ordenes_ids) * 4, 80_000)
        to_create = max(0, TARGET_LOTES - existing_lotes)

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing_lotes:,} lotes STR-LOTE-*. Omitiendo.')
        else:
            self.stdout.write(f'  Creando {to_create:,} lotes de producción...')
            t0 = time.time()
            maquinas = ctx.get('maquinas') or list(Maquina.objects.all())
            operario = ctx.get('operario') or CustomUser.objects.filter(is_superuser=False).first()
            now = timezone.now()

            objs = []
            n = existing_lotes
            ordenes_sample = ordenes_ids * (to_create // max(len(ordenes_ids), 1) + 1)
            random.shuffle(ordenes_sample)

            for i, op_id in enumerate(ordenes_sample[:to_create]):
                n += 1
                hora_inicio = now - timedelta(days=random.randint(1, 365), hours=random.randint(0, 20))
                objs.append(LoteProduccion(
                    orden_produccion_id=op_id,
                    codigo_lote=f'STR-LOTE-{n:08d}',
                    peso_neto_producido=_rnd_decimal(10, 500, decimals=3),
                    peso_bruto=_rnd_decimal(11, 510, decimals=3),
                    tara=_rnd_decimal(0.5, 5, decimals=3),
                    operario=operario,
                    maquina=random.choice(maquinas) if maquinas else None,
                    turno=random.choice(TURNOS),
                    hora_inicio=hora_inicio,
                    hora_final=hora_inicio + timedelta(hours=random.randint(2, 10)),
                    unidades_empaque=random.choice([1, 15, 225]),
                    presentacion=random.choice(PRESENTACIONES),
                ))
                if len(objs) >= batch_size:
                    LoteProduccion.objects.bulk_create(objs, batch_size=batch_size, )
                    _progress(self.stdout, 'Lotes', min(i + 1, to_create), to_create, t0)
                    objs = []
            if objs:
                LoteProduccion.objects.bulk_create(objs, batch_size=batch_size, )

        ctx['lotes_ids'] = list(
            LoteProduccion.objects.filter(codigo_lote__startswith='STR-LOTE-').values_list('id', flat=True)
        )
        self.stdout.write(f'\n  Total lotes: {len(ctx["lotes_ids"]):,}')

    # ─── FASE 7: Pedidos de venta + detalles ─────────────────────────────────

    def _fase7_pedidos(self, ctx, batch_size, num_pedidos=30_000, **kw):
        existing = PedidoVenta.objects.filter(guia_remision__startswith='STR-GR-').count()
        to_create = max(0, num_pedidos - existing)

        clientes_ids = ctx.get('clientes_ids') or list(Cliente.objects.values_list('id', flat=True))
        productos_ids = [p[0] for p in (ctx.get('productos') or [])]
        if not productos_ids:
            productos_ids = list(Producto.objects.values_list('id', flat=True))
        productos_precio = {p[0]: p[2] for p in (ctx.get('productos') or [])}
        if not productos_precio:
            productos_precio = dict(Producto.objects.values_list('id', 'precio_base'))

        sedes = ctx.get('sedes') or list(Sede.objects.all())
        vendedor = ctx.get('vendedor')

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing:,} pedidos STR-GR-*. Omitiendo creación de pedidos.')
        else:
            self.stdout.write(f'  Creando {to_create:,} pedidos de venta...')
            t0 = time.time()
            pedido_objs = []
            for i in range(to_create):
                n = existing + i + 1
                pedido_objs.append(PedidoVenta(
                    cliente_id=random.choice(clientes_ids) if clientes_ids else None,
                    guia_remision=f'STR-GR-{n:08d}',
                    estado=random.choices(ESTADOS_PED, weights=[30, 40, 30])[0],
                    esta_pagado=random.random() < 0.55,
                    sede=random.choice(sedes),
                    vendedor_asignado=vendedor,
                    valor_retencion=_rnd_decimal(0, 50, 3) if random.random() < 0.15 else Decimal('0.000'),
                ))
                if len(pedido_objs) >= batch_size:
                    PedidoVenta.objects.bulk_create(pedido_objs, batch_size=batch_size)
                    _progress(self.stdout, 'Pedidos', min(i + 1, to_create), to_create, t0)
                    pedido_objs = []
            if pedido_objs:
                PedidoVenta.objects.bulk_create(pedido_objs, batch_size=batch_size)

        # Detalles de pedido: ~4 por pedido
        target_detalles = num_pedidos * 4
        existing_det = DetallePedido.objects.filter(pedido_venta__guia_remision__startswith='STR-GR-').count()
        to_create_det = max(0, target_detalles - existing_det)

        if to_create_det == 0:
            self.stdout.write(f'\n  Ya existen {existing_det:,} detalles. Omitiendo.')
        else:
            self.stdout.write(f'\n  Creando {to_create_det:,} detalles de pedido...')
            t0 = time.time()
            pedidos_ids = list(
                PedidoVenta.objects.filter(guia_remision__startswith='STR-GR-').values_list('id', flat=True)
            )
            lotes_ids = ctx.get('lotes_ids') or []

            det_objs = []
            for i in range(to_create_det):
                prod_id = random.choice(productos_ids) if productos_ids else None
                precio_base = productos_precio.get(prod_id, Decimal('10.00'))
                peso = _rnd_decimal(0.5, 500, 3)
                precio = Decimal(float(precio_base) * random.uniform(0.9, 1.5)).quantize(Decimal('0.001'))
                iva = random.random() < 0.80
                subtotal = (peso * precio).quantize(Decimal('0.001'))
                total_con_iva = (subtotal * Decimal('1.15') if iva else subtotal).quantize(Decimal('0.001'))
                det_objs.append(DetallePedido(
                    pedido_venta_id=random.choice(pedidos_ids),
                    producto_id=prod_id,
                    lote_id=random.choice(lotes_ids) if lotes_ids and random.random() < 0.6 else None,
                    cantidad=random.randint(1, 50),
                    piezas=random.randint(1, 20),
                    peso=peso,
                    precio_unitario=precio,
                    incluye_iva=iva,
                    subtotal=subtotal,
                    total_con_iva=total_con_iva,
                ))
                if len(det_objs) >= batch_size:
                    DetallePedido.objects.bulk_create(det_objs, batch_size=batch_size)
                    _progress(self.stdout, 'Detalles', min(i + 1, to_create_det), to_create_det, t0)
                    det_objs = []
            if det_objs:
                DetallePedido.objects.bulk_create(det_objs, batch_size=batch_size)

        self.stdout.write(f'\n  PedidoVenta: {PedidoVenta.objects.filter(guia_remision__startswith="STR-GR-").count():,}')
        self.stdout.write(f'  DetallePedido: {DetallePedido.objects.filter(pedido_venta__guia_remision__startswith="STR-GR-").count():,}')

    # ─── FASE 8: Stock bodega ─────────────────────────────────────────────────

    def _fase8_stock(self, ctx, batch_size, **kw):
        productos_ids = [p[0] for p in (ctx.get('productos') or [])]
        if not productos_ids:
            productos_ids = list(Producto.objects.values_list('id', flat=True))
        bodegas_all = ctx.get('bodegas') or list(Bodega.objects.all())

        # Cargar pares (bodega_id, producto_id) ya existentes sin lote para evitar UniqueConstraint
        existing_pairs = set(
            StockBodega.objects.filter(lote__isnull=True).values_list('bodega_id', 'producto_id')
        )

        prods_sample = random.sample(productos_ids, min(500, len(productos_ids)))
        TARGET = len(prods_sample) * len(bodegas_all)
        self.stdout.write(f'  Target stock: {TARGET:,} | Existentes: {len(existing_pairs):,}')

        objs = []
        created = 0
        t0 = time.time()
        for bodega in bodegas_all:
            for prod_id in prods_sample:
                if (bodega.id, prod_id) in existing_pairs:
                    continue
                objs.append(StockBodega(
                    bodega=bodega,
                    producto_id=prod_id,
                    lote=None,
                    cantidad=_rnd_decimal(0, 5000),
                ))
                created += 1
                if len(objs) >= batch_size:
                    StockBodega.objects.bulk_create(objs, batch_size=batch_size)
                    _progress(self.stdout, 'Stock', created, TARGET - len(existing_pairs), t0)
                    objs = []
        if objs:
            StockBodega.objects.bulk_create(objs, batch_size=batch_size)

        self.stdout.write(f'\n  Total StockBodega: {StockBodega.objects.count():,}')

    # ─── FASE 9: Movimientos de inventario (el volumen principal) ─────────────

    def _fase9_movimientos(self, ctx, batch_size, num_movimientos=750_000, **kw):
        existing = MovimientoInventario.objects.count()
        to_create = max(0, num_movimientos - existing)

        if to_create == 0:
            self.stdout.write(f'  Ya existen {existing:,} movimientos. Omitiendo.')
            return

        self.stdout.write(f'  Creando {to_create:,} movimientos (bulk_create, batch={batch_size:,})...')
        self.stdout.write('  ⚠ Nota: bulk_create bypasea AuditableModelMixin.save() intencionalmente.')

        productos_ids = [p[0] for p in (ctx.get('productos') or [])]
        if not productos_ids:
            productos_ids = list(Producto.objects.values_list('id', flat=True))
        bodegas_mp = ctx.get('bodegas_mp') or list(Bodega.objects.all()[:4])
        bodegas_pt = ctx.get('bodegas_pt') or list(Bodega.objects.all()[4:8]) or bodegas_mp
        lotes_ids = ctx.get('lotes_ids') or [None]
        proveedores_ids = [p.id for p in (ctx.get('proveedores') or [])] or [None]
        operario = ctx.get('operario')
        operario_id = operario.id if operario else None

        tipos_weights = [25, 20, 15, 10, 20, 8, 2]  # COMPRA, PROD, TRANSF, AJUSTE, VENTA, CONSUMO, DEV

        t0 = time.time()
        objs = []
        total_done = 0

        for i in range(to_create):
            tipo = random.choices(TIPOS_MOV, weights=tipos_weights)[0]
            prod_id = random.choice(productos_ids)
            cantidad = _rnd_decimal(0.1, 1000)
            saldo = _rnd_decimal(0, 10000)

            if tipo == 'COMPRA':
                b_origen, b_destino = None, random.choice(bodegas_mp).id
            elif tipo == 'VENTA':
                b_origen, b_destino = random.choice(bodegas_pt).id, None
            elif tipo == 'PRODUCCION':
                b_origen, b_destino = None, random.choice(bodegas_pt).id
            elif tipo == 'TRANSFERENCIA':
                b_origen = random.choice(bodegas_mp).id
                b_destino = random.choice(bodegas_pt).id
            elif tipo == 'CONSUMO':
                b_origen, b_destino = random.choice(bodegas_mp).id, None
            else:  # AJUSTE, DEVOLUCION
                b_origen = random.choice(bodegas_mp).id if random.random() < 0.5 else None
                b_destino = random.choice(bodegas_pt).id if b_origen is None else None

            objs.append(MovimientoInventario(
                tipo_movimiento=tipo,
                producto_id=prod_id,
                lote_id=random.choice(lotes_ids) if lotes_ids and random.random() < 0.4 else None,
                bodega_origen_id=b_origen,
                bodega_destino_id=b_destino,
                cantidad=cantidad,
                saldo_resultante=saldo,
                documento_ref=f'STR-{tipo[:3]}-{total_done + i + 1:09d}',
                usuario_id=operario_id,
                proveedor_id=random.choice(proveedores_ids) if tipo == 'COMPRA' and proveedores_ids[0] else None,
                pais=random.choice(PAISES) if tipo == 'COMPRA' else None,
                calidad=random.choice(['A', 'B', 'C']) if tipo == 'COMPRA' else None,
                observaciones=None,
                editado=False,
            ))

            if len(objs) >= batch_size:
                with transaction.atomic():
                    MovimientoInventario.objects.bulk_create(objs, batch_size=batch_size)
                total_done += len(objs)
                _progress(self.stdout, 'Movimientos', total_done, to_create, t0)
                objs = []

        if objs:
            with transaction.atomic():
                MovimientoInventario.objects.bulk_create(objs, batch_size=batch_size)
            total_done += len(objs)

        self.stdout.write(f'\n  Total movimientos: {MovimientoInventario.objects.count():,}')

    # ─── POST-PROCESO: Distribuir fechas en 12 meses ─────────────────────────

    def _randomize_dates(self):
        """
        Distribuye las fechas de MovimientoInventario y PedidoVenta aleatoriamente
        sobre los últimos 12 meses usando SQL nativo (una sola sentencia, muy rápido).
        """
        with connection.cursor() as cursor:
            # MovimientoInventario.fecha (auto_now_add → todos cayeron en el mismo momento)
            self.stdout.write('  Randomizando fecha en MovimientoInventario...')
            cursor.execute("""
                UPDATE inventory_movimientoinventario
                SET fecha = DATEADD(
                    second,
                    -(CAST(ABS(CHECKSUM(NEWID())) AS BIGINT) % 31536000),
                    GETUTCDATE()
                )
                WHERE documento_ref LIKE 'STR-%'
            """)
            self.stdout.write(f'    → {cursor.rowcount:,} filas actualizadas')

            # PedidoVenta.fecha_pedido
            self.stdout.write('  Randomizando fecha_pedido en PedidoVenta...')
            cursor.execute("""
                UPDATE gestion_pedidoventa
                SET fecha_pedido = DATEADD(
                    second,
                    -(CAST(ABS(CHECKSUM(NEWID())) AS BIGINT) % 15552000),
                    GETUTCDATE()
                )
                WHERE guia_remision LIKE 'STR-GR-%'
            """)
            self.stdout.write(f'    → {cursor.rowcount:,} filas actualizadas')

    # ─── Resumen final ────────────────────────────────────────────────────────

    def _print_summary(self, elapsed: float):
        from django.apps import apps

        conteos = {
            'Sede': Sede.objects.count(),
            'Bodega': Bodega.objects.count(),
            'Producto': Producto.objects.count(),
            'FormulaColor': FormulaColor.objects.count(),
            'Cliente': Cliente.objects.count(),
            'OrdenProduccion': OrdenProduccion.objects.count(),
            'LoteProduccion': LoteProduccion.objects.count(),
            'PedidoVenta': PedidoVenta.objects.count(),
            'DetallePedido': DetallePedido.objects.count(),
            'StockBodega': StockBodega.objects.count(),
            'MovimientoInventario': MovimientoInventario.objects.count(),
        }
        total = sum(conteos.values())

        self.stdout.write(self.style.SUCCESS(f'\n{"═" * 60}'))
        self.stdout.write(self.style.SUCCESS('  RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS(f'{"═" * 60}'))
        for model, count in conteos.items():
            bar = '█' * min(30, int(count / max(total, 1) * 300))
            self.stdout.write(f'  {model:<25} {count:>10,}  {bar}')
        self.stdout.write(f'{"─" * 60}')
        self.stdout.write(self.style.SUCCESS(f'  TOTAL                    {total:>10,}'))
        self.stdout.write(f'  Tiempo total: {elapsed:.1f}s ({elapsed/60:.1f} min)')
        self.stdout.write(self.style.SUCCESS(f'{"═" * 60}\n'))

        self.stdout.write(self.style.WARNING(
            '  ⚡ ÁREAS A OBSERVAR DURANTE LAS PRUEBAS:\n'
            '  1. /api/movimientos/?producto=X  → Kardex sin filtro = tabla scan 750K\n'
            '  2. /api/audit-log/               → Sin paginación = timeout potencial\n'
            '  3. Dashboard ejecutivo → N+1 en clientes con 10K registros\n'
            '  4. Reporte Excel con >10K filas   → OOM en reporting_excel\n'
            '  5. /api/pedidos/?expand=detalles  → prefetch_related crítico\n'
            '  6. Admin Django → AuditLog sin filtro de fecha\n'
        ))
