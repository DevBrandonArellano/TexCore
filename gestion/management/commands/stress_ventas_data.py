"""
Pobla clientes, pedidos de venta y pagos para probar el dashboard de Ventas (ejecutivo).
Ejecutar después de stress_test_data para tener productos y vendedores.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from gestion.models import (
    CustomUser,
    Sede,
    Cliente,
    PedidoVenta,
    DetallePedido,
    PagoCliente,
    Producto,
)


class Command(BaseCommand):
    help = 'Pobla clientes, pedidos y pagos para probar el dashboard de Ventas en ejecutivo.'

    def add_arguments(self, parser):
        parser.add_argument('--clientes', type=int, default=40, help='Número de clientes (default: 40)')
        parser.add_argument('--pedidos', type=int, default=120, help='Número de pedidos (default: 120)')

    @transaction.atomic
    def handle(self, *args, **options):
        num_clientes = options['clientes']
        num_pedidos = options['pedidos']

        self.stdout.write(f'Poblando datos de ventas: {num_clientes} clientes, {num_pedidos} pedidos...')

        # 1. Sede y vendedores
        sede = Sede.objects.first()
        if not sede:
            sede = Sede.objects.create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
            self.stdout.write('  Creada Sede Principal')

        group_vendedor, _ = Group.objects.get_or_create(name='vendedor')
        vendedores = list(CustomUser.objects.filter(groups__name='vendedor'))
        if not vendedores:
            v = CustomUser.objects.create_user(
                username='user_vendedor',
                password='password123',
                email='vendedor@example.com',
                first_name='Vendedor',
                last_name='Test',
                sede=sede,
            )
            v.groups.add(group_vendedor)
            v.save()
            vendedores = [v]
            self.stdout.write('  Creado user_vendedor')
        # Añadir 2 vendedores extra para gráfico "Ventas por Vendedor"
        for i in range(1, 3):
            uname = f'stress_vendedor_{i}'
            if not CustomUser.objects.filter(username=uname).exists():
                v = CustomUser.objects.create_user(
                    username=uname,
                    password='password123',
                    email=f'{uname}@example.com',
                    first_name=f'Vendedor {i}',
                    last_name='Stress',
                    sede=sede,
                )
                v.groups.add(group_vendedor)
                v.save()
                vendedores.append(v)
        self.stdout.write(f'  {len(vendedores)} vendedores disponibles')

        # 2. Productos para vender (preferir hilo, tela, subproducto; si no hay, usar cualquiera)
        productos = list(
            Producto.objects.filter(tipo__in=['hilo', 'tela', 'subproducto']).exclude(precio_base=0)
        )
        if not productos:
            productos = list(Producto.objects.filter(precio_base__gt=0)[:30])
        if not productos:
            # Crear productos básicos si la BD está vacía
            self.stdout.write('  Creando productos básicos para ventas...')
            for i in range(15):
                Producto.objects.get_or_create(
                    codigo=f'VENT-STR-{i:03d}',
                    defaults={
                        'descripcion': f'Producto venta prueba {i}',
                        'tipo': 'hilo',
                        'unidad_medida': 'kg',
                        'stock_minimo': 10,
                        'precio_base': Decimal(random.uniform(2, 25)).quantize(Decimal('0.01')),
                    }
                )
            productos = list(Producto.objects.filter(codigo__startswith='VENT-STR-'))
        if not productos:
            self.stdout.write(self.style.ERROR('No se pudieron obtener o crear productos.'))
            return

        self.stdout.write(f'  Usando {len(productos)} productos')

        # 3. Crear clientes
        nombres = [
            'Textiles del Sur', 'Hilandería Andina', 'Confecciones Express', 'Almacén La Esquina',
            'Distribuidora Norte', 'Mayorista Textil', 'Boutique Moda', 'Industrias Creativas',
            'Comercial El Ahorro', 'Importadora Quito', 'Exportadora Ecuador', 'Fábrica Moderna',
            'Corporación Textil', 'Grupo Industrial', 'Cadena de Tiendas', 'Cooperativa Artesanal',
        ]
        for i in range(num_clientes):
            idx = i % len(nombres)
            suf = f' {i // len(nombres) + 1}' if i >= len(nombres) else ''
            ruc = f'179{i:08d}001'  # Único por cliente
            Cliente.objects.get_or_create(
                ruc_cedula=ruc,
                defaults={
                    'nombre_razon_social': f'{nombres[idx]}{suf} S.A.',
                    'direccion_envio': f'Calle {i + 1}, Av. Principal',
                    'nivel_precio': random.choice(['mayorista', 'normal']),
                    'tiene_beneficio': random.random() < 0.25,
                    'limite_credito': Decimal(random.randint(2000, 30000)),
                    'plazo_credito_dias': random.choice([0, 8, 15, 30, 45, 60]),
                    'vendedor_asignado': random.choice(vendedores),
                }
            )

        clientes = list(Cliente.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  {len(clientes)} clientes listos'))

        # 4. Crear pedidos (últimos 60 días)
        hoy = timezone.now()
        pedidos_creados = 0
        for i in range(num_pedidos):
            cliente = random.choice(clientes)
            vendedor = cliente.vendedor_asignado or random.choice(vendedores)
            dias_atras = random.randint(0, 60)
            fecha_ped = hoy - timedelta(days=dias_atras)
            esta_pagado = random.random() < 0.55

            pedido = PedidoVenta.objects.create(
                cliente=cliente,
                guia_remision=f'GR-{hoy.year}-{10000 + i}',
                estado=random.choice(['pendiente', 'despachado', 'facturado']),
                esta_pagado=esta_pagado,
                sede=sede,
                vendedor_asignado=vendedor,
            )
            PedidoVenta.objects.filter(pk=pedido.pk).update(fecha_pedido=fecha_ped)

            # 1-4 ítems por pedido
            num_items = random.randint(1, 4)
            prods = random.sample(productos, min(num_items, len(productos)))
            for p in prods:
                peso = Decimal(random.uniform(5, 150)).quantize(Decimal('0.001'))
                precio = p.precio_base * Decimal(random.uniform(1.0, 1.4))
                DetallePedido.objects.create(
                    pedido_venta=pedido,
                    producto=p,
                    cantidad=random.randint(1, 10),
                    piezas=random.randint(1, 5),
                    peso=peso,
                    precio_unitario=precio,
                    incluye_iva=True,
                )
            pedidos_creados += 1

        self.stdout.write(self.style.SUCCESS(f'  {pedidos_creados} pedidos creados'))

        # 5. Crear algunos pagos (para que saldo_pendiente y cartera_vencida se calculen)
        from gestion.utils import PaymentReconciler
        for cliente in random.sample(clientes, min(15, len(clientes))):
            total_cliente = sum(
                d.peso * d.precio_unitario * Decimal('1.15')
                for p in PedidoVenta.objects.filter(cliente=cliente)
                for d in p.detalles.all()
            )
            if total_cliente > 0:
                monto_pago = total_cliente * Decimal(random.uniform(0.2, 0.8))
                PagoCliente.objects.create(
                    cliente=cliente,
                    monto=monto_pago.quantize(Decimal('0.001')),
                    metodo_pago=random.choice(['transferencia', 'efectivo', 'cheque']),
                    comprobante=f'COMP-{random.randint(1000, 9999)}',
                    sede=sede,
                )
                PaymentReconciler.reconcile_client_orders(cliente)

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Datos de ventas creados. Prueba el dashboard Ventas en ejecutivo.'
        ))
