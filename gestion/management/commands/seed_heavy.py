from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from gestion.models import (
    CustomUser, Sede, Area, Bodega, Producto, FormulaColor, FaseReceta, DetalleFormula,
    OrdenProduccion, Cliente, Maquina, LoteProduccion, PedidoVenta, DetallePedido
)
from inventory.models import StockBodega
from decimal import Decimal
import random
import string
from datetime import timedelta


class Command(BaseCommand):
    help = 'Seeds the database with THOUSANDS of records for stress testing.'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=100)
        parser.add_argument('--customers', type=int, default=50)
        parser.add_argument('--orders', type=int, default=200)

    def random_string(self, length=10):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @transaction.atomic
    def handle(self, *args, **options):
        num_products = options['products']
        num_customers = options['customers']
        num_orders = options['orders']

        self.stdout.write(
            f'Starting ADAPTED HEAVY database seeding: {num_products} products, '
            f'{num_customers} customers, {num_orders} orders...'
        )

        # 1. Basics
        sede, _ = Sede.objects.get_or_create(
            nombre='Planta Industrial Norte', defaults={
                'location': 'Sector Industrial'})
        area_prod, _ = Area.objects.get_or_create(nombre='Producción Textil', sede=sede)
        bodega_mp, _ = Bodega.objects.get_or_create(nombre='Bodega Central MP', sede=sede)
        bodega_pt, _ = Bodega.objects.get_or_create(nombre='Bodega Despacho PT', sede=sede)

        # Machines
        machines = []
        for i in range(1, 11):
            m, _ = Maquina.objects.get_or_create(
                nombre=f'Circular Machine {i:02d}',
                defaults={
                    'capacidad_maxima': Decimal('500.00'),
                    'eficiencia_ideal': Decimal('0.95'),
                    'estado': 'operativa',
                    'area': area_prod
                }
            )
            machines.append(m)

        # Users
        admin_user = CustomUser.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = CustomUser.objects.create_superuser('admin', 'admin@example.com', 'admin123')

        operario, _ = CustomUser.objects.get_or_create(
            username='operario_heavy',
            defaults={'first_name': 'Operario', 'last_name': 'Heavy', 'sede': sede, 'area': area_prod}
        )
        if operario.password == '':
            operario.set_password('password123')
            operario.save()

        # 2. Products
        self.stdout.write('Generating products...')
        products = []
        types = ['hilo', 'tela', 'quimico', 'insumo']
        for i in range(num_products):
            p = Producto.objects.create(
                codigo=f'PROD-{self.random_string(6)}-{i}',
                descripcion=f'Producto de Prueba Intensiva {i}',
                tipo=random.choice(types),
                unidad_medida=random.choice(['kg', 'metros', 'unidades']),
                stock_minimo=Decimal(random.randint(10, 100)),
                precio_base=Decimal(random.uniform(1.0, 50.0)).quantize(Decimal('0.01'))
            )
            products.append(p)

            # Initial stock for some products
            if random.random() > 0.3:
                stock = StockBodega.objects.create(
                    bodega=bodega_mp,
                    producto=p,
                    cantidad=Decimal(random.randint(100, 5000))
                )
                stock._justificacion_auditoria = 'Carga pesada inicial'
                stock.save()

        # 3. Formulas
        self.stdout.write('Generating formulas and phases...')
        formulas = []
        quimicos = [p for p in products if p.tipo == 'quimico']
        if not quimicos:
            # Ensure at least one chemical
            q = Producto.objects.create(
                codigo='QMC-BASE-H',
                descripcion='Quimico Base Heavy',
                tipo='quimico',
                unidad_medida='kg')
            quimicos.append(q)

        for i in range(20):
            f = FormulaColor.objects.create(
                codigo=f'FORM-H-{i:03d}',
                nombre_color=f'Color Experimental {i}',
                estado='aprobada'
            )
            formulas.append(f)

            # Create at least one phase for the formula
            fase = FaseReceta.objects.create(
                formula=f,
                nombre='tintura',
                orden=1,
                temperatura=90,
                tiempo=60
            )

            # Add 1-3 chemicals to the phase
            for q in random.sample(quimicos, k=random.randint(1, min(3, len(quimicos)))):
                DetalleFormula.objects.create(
                    fase=fase,
                    producto=q,
                    gramos_por_kilo=Decimal(random.uniform(5.0, 60.0)).quantize(Decimal('0.1')),
                    tipo_calculo='gr_l',
                    orden_adicion=random.randint(1, 5)
                )

        # 4. Customers
        self.stdout.write('Generating customers...')
        customers = []
        for i in range(num_customers):
            c = Cliente.objects.create(
                ruc_cedula=f'179{random.randint(1000000, 9999999)}001',
                nombre_razon_social=f'Corporacion Textil {self.random_string(5)} S.A.',
                direccion_envio=f'Calle {i}, Av. Industrial',
                nivel_precio=random.choice(['mayorista', 'normal']),
                limite_credito=Decimal(random.randint(5000, 50000)),
                plazo_credito_dias=random.choice([0, 15, 30, 45]),
                is_active=True
            )
            customers.append(c)

        # 5. Orders and Lots
        self.stdout.write('Generating orders and lots...')
        base_date = timezone.now()
        hilos_telas = [p for p in products if p.tipo in ['hilo', 'tela']]
        if not hilos_telas:
            hilos_telas = products[:10]

        for i in range(num_orders):
            op = OrdenProduccion.objects.create(
                codigo=f'OP-HEAVY-{i:05d}',
                producto=random.choice(hilos_telas),
                formula_color=random.choice(formulas),
                bodega=bodega_mp,
                area=area_prod,
                peso_neto_requerido=Decimal(random.randint(50, 1000)),
                estado=random.choice(['pendiente', 'en_proceso', 'finalizada']),
                maquina_asignada=random.choice(machines),
                operario_asignado=operario,
                sede=sede
            )

            # Create lots for finished orders
            if op.estado == 'finalizada':
                num_lots = random.randint(1, 5)
                for lot_idx in range(num_lots):
                    LoteProduccion.objects.create(
                        orden_produccion=op,
                        codigo_lote=f'LOTE-{op.codigo}-{lot_idx}',
                        peso_neto_producido=(op.peso_neto_requerido / num_lots).quantize(Decimal('0.001')),
                        operario=operario,
                        maquina=op.maquina_asignada,
                        turno='Matutino',
                        hora_inicio=base_date - timedelta(days=random.randint(1, 30)),
                        hora_final=base_date - timedelta(days=random.randint(1, 30)) + timedelta(hours=4)
                    )

        # 6. Sales
        self.stdout.write('Generating sales orders...')
        finalized_ops = OrdenProduccion.objects.filter(estado='finalizada').prefetch_related('lotes')
        for i in range(int(num_orders * 0.5)):
            if not finalized_ops:
                break

            cliente = random.choice(customers)
            pedido = PedidoVenta.objects.create(
                cliente=cliente,
                guia_remision=f'GR-{self.random_string(8)}',
                estado=random.choice(['pendiente', 'despachado', 'facturado']),
                sede=sede,
                valor_retencion=Decimal('0.000')  # Added for compatibility
            )

            # Add 1-4 items
            for _ in range(random.randint(1, 4)):
                op_choice = random.choice(finalized_ops)
                lote_choice = random.choice(op_choice.lotes.all()) if op_choice.lotes.exists() else None

                DetallePedido.objects.create(
                    pedido_venta=pedido,
                    producto=op_choice.producto,
                    lote=lote_choice,
                    cantidad=random.randint(1, 10),
                    piezas=random.randint(1, 20),
                    peso=Decimal(random.uniform(10.0, 100.0)).quantize(Decimal('0.01')),
                    precio_unitario=op_choice.producto.precio_base * Decimal('1.2'),
                    incluye_iva=True
                )

        self.stdout.write(self.style.SUCCESS('ADAPTED HEAVY seeding completed successfully!'))
