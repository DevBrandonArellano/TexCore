from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from gestion.models import (
    CustomUser, Sede, Area, Bodega, Producto, FormulaColor, FaseReceta, DetalleFormula,
    OrdenProduccion, LoteProduccion, Cliente, PedidoVenta, DetallePedido, PagoCliente,
    Maquina
)
from inventory.models import StockBodega
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seeds the database with initial data for the entire application.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')

        # 1. Create Sedes y Areas
        sede, _ = Sede.objects.get_or_create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
        area_general, _ = Area.objects.get_or_create(nombre='Area General', sede=sede)
        area_tintura, _ = Area.objects.get_or_create(nombre='Tintura', sede=sede)
        area_tejido, _ = Area.objects.get_or_create(nombre='Tejido', sede=sede)
        area_empaque, _ = Area.objects.get_or_create(nombre='Empaque', sede=sede)

        self.stdout.write(self.style.SUCCESS('✓ Sedes y Áreas creadas'))

        # 2. Create Bodegas
        bodega_mp, _ = Bodega.objects.get_or_create(nombre='Bodega de Materia Prima', sede=sede)
        bodega_pt, _ = Bodega.objects.get_or_create(nombre='Bodega de Producto Terminado', sede=sede)
        bodega_insumos, _ = Bodega.objects.get_or_create(nombre='Bodega de Insumos', sede=sede)
        bodega_quimicos, _ = Bodega.objects.get_or_create(nombre='Bodega de Químicos', sede=sede)

        self.stdout.write(self.style.SUCCESS('✓ Bodegas creadas'))

        # 3. Create Productos Terminados (Hilos/Telas)
        hilo_algodon, _ = Producto.objects.get_or_create(
            codigo='HILO-ALG-001',
            defaults={
                'descripcion': 'Hilo de Algodón 100% Natural',
                'tipo': 'hilo',
                'unidad_medida': 'kg',
                'stock_minimo': 100,
                'precio_base': Decimal('8.50')
            }
        )
        hilo_poliester, _ = Producto.objects.get_or_create(
            codigo='HILO-POL-001',
            defaults={
                'descripcion': 'Hilo Poliéster Premium',
                'tipo': 'hilo',
                'unidad_medida': 'kg',
                'stock_minimo': 80,
                'precio_base': Decimal('6.75')
            }
        )
        tela_algodon, _ = Producto.objects.get_or_create(
            codigo='TELA-ALG-001',
            defaults={
                'descripcion': 'Tela de Algodón Teñida',
                'tipo': 'tela',
                'unidad_medida': 'metros',
                'stock_minimo': 500,
                'precio_base': Decimal('12.00')
            }
        )

        # 4. Create Químicos
        quimico_rojo, _ = Producto.objects.get_or_create(
            codigo='QMC-ROJO-001',
            defaults={
                'descripcion': 'Colorante Rojo Reactivo',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 15,
                'precio_base': Decimal('25.00')
            }
        )
        quimico_azul, _ = Producto.objects.get_or_create(
            codigo='QMC-AZUL-001',
            defaults={
                'descripcion': 'Colorante Azul Reactivo',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 15,
                'precio_base': Decimal('25.00')
            }
        )
        quimico_fijador, _ = Producto.objects.get_or_create(
            codigo='QMC-FIJ-001',
            defaults={
                'descripcion': 'Fijador de Color Universal',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 25,
                'precio_base': Decimal('18.00')
            }
        )
        quimico_detergente, _ = Producto.objects.get_or_create(
            codigo='QMC-DET-001',
            defaults={
                'descripcion': 'Detergente Industrial',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 20,
                'precio_base': Decimal('12.00')
            }
        )

        # 5. Create Insumos
        etiqueta_zebra, _ = Producto.objects.get_or_create(
            codigo='INS-ETQ-001',
            defaults={
                'descripcion': 'Etiqueta Zebra 100x50mm',
                'tipo': 'insumo',
                'unidad_medida': 'unidades',
                'stock_minimo': 2000,
                'precio_base': Decimal('0.05')
            }
        )
        funda_plastica, _ = Producto.objects.get_or_create(
            codigo='INS-FUND-001',
            defaults={
                'descripcion': 'Funda Plástica Industrial',
                'tipo': 'insumo',
                'unidad_medida': 'unidades',
                'stock_minimo': 1000,
                'precio_base': Decimal('0.15')
            }
        )
        caja_carton, _ = Producto.objects.get_or_create(
            codigo='INS-CAJA-001',
            defaults={
                'descripcion': 'Caja de Cartón Corrugado',
                'tipo': 'insumo',
                'unidad_medida': 'unidades',
                'stock_minimo': 500,
                'precio_base': Decimal('0.50')
            }
        )

        self.stdout.write(self.style.SUCCESS('✓ Productos y Químicos creados'))

        # 6. Load Initial Stock
        def safe_seed_stock(bodega, producto, cantidad):
            stock, created = StockBodega.objects.get_or_create(bodega=bodega, producto=producto, lote=None)
            stock.cantidad = cantidad
            stock._justificacion_auditoria = 'Carga inicial de datos (Seed)'
            stock.save()

        safe_seed_stock(bodega_mp, hilo_algodon, Decimal('800.00'))
        safe_seed_stock(bodega_mp, hilo_poliester, Decimal('600.00'))
        safe_seed_stock(bodega_quimicos, quimico_rojo, Decimal('100.00'))
        safe_seed_stock(bodega_quimicos, quimico_azul, Decimal('100.00'))
        safe_seed_stock(bodega_quimicos, quimico_fijador, Decimal('150.00'))
        safe_seed_stock(bodega_quimicos, quimico_detergente, Decimal('120.00'))
        safe_seed_stock(bodega_insumos, etiqueta_zebra, Decimal('10000.00'))
        safe_seed_stock(bodega_insumos, funda_plastica, Decimal('5000.00'))
        safe_seed_stock(bodega_insumos, caja_carton, Decimal('3000.00'))
        safe_seed_stock(bodega_pt, tela_algodon, Decimal('2000.00'))

        self.stdout.write(self.style.SUCCESS('✓ Stock inicial cargado'))

        # 7. Create Color Formulas
        formula_rojo, _ = FormulaColor.objects.get_or_create(
            codigo='FORM-ROJO-001',
            defaults={
                'nombre_color': 'Rojo Intenso',
                'tipo_sustrato': 'algodon',
                'version': 1,
                'estado': 'aprobada'
            }
        )

        fase_pretratamiento, _ = FaseReceta.objects.get_or_create(
            formula=formula_rojo,
            nombre='pre_tratamiento',
            defaults={'orden': 1, 'temperatura': 60, 'tiempo': 30}
        )
        fase_tintura_rojo, _ = FaseReceta.objects.get_or_create(
            formula=formula_rojo,
            nombre='tintura',
            defaults={'orden': 2, 'temperatura': 90, 'tiempo': 90}
        )
        fase_lavado, _ = FaseReceta.objects.get_or_create(
            formula=formula_rojo,
            nombre='lavado',
            defaults={'orden': 3, 'temperatura': 70, 'tiempo': 45}
        )

        DetalleFormula.objects.get_or_create(
            fase=fase_pretratamiento,
            producto=quimico_detergente,
            defaults={'gramos_por_kilo': Decimal('5.0'), 'tipo_calculo': 'gr_l', 'orden_adicion': 1}
        )
        DetalleFormula.objects.get_or_create(
            fase=fase_tintura_rojo,
            producto=quimico_rojo,
            defaults={'gramos_por_kilo': Decimal('40.0'), 'tipo_calculo': 'gr_l', 'orden_adicion': 1}
        )
        DetalleFormula.objects.get_or_create(
            fase=fase_tintura_rojo,
            producto=quimico_fijador,
            defaults={'gramos_por_kilo': Decimal('15.0'), 'tipo_calculo': 'gr_l', 'orden_adicion': 2}
        )
        DetalleFormula.objects.get_or_create(
            fase=fase_lavado,
            producto=quimico_detergente,
            defaults={'gramos_por_kilo': Decimal('3.0'), 'tipo_calculo': 'gr_l', 'orden_adicion': 1}
        )

        formula_azul, _ = FormulaColor.objects.get_or_create(
            codigo='FORM-AZUL-001',
            defaults={
                'nombre_color': 'Azul Cielo',
                'tipo_sustrato': 'poliester',
                'version': 1,
                'estado': 'aprobada'
            }
        )

        fase_tintura_azul, _ = FaseReceta.objects.get_or_create(
            formula=formula_azul,
            nombre='tintura',
            defaults={'orden': 1, 'temperatura': 95, 'tiempo': 120}
        )

        DetalleFormula.objects.get_or_create(
            fase=fase_tintura_azul,
            producto=quimico_azul,
            defaults={'gramos_por_kilo': Decimal('45.0'), 'tipo_calculo': 'gr_l', 'orden_adicion': 1}
        )

        self.stdout.write(self.style.SUCCESS('✓ Fórmulas de color creadas'))

        # 8. Create Máquinas
        maquina1, _ = Maquina.objects.get_or_create(
            nombre='Máquina Tintura #1',
            defaults={
                'capacidad_maxima': Decimal('500.00'),
                'eficiencia_ideal': Decimal('0.85'),
                'estado': 'operativa',
                'area': area_tintura
            }
        )
        maquina2, _ = Maquina.objects.get_or_create(
            nombre='Máquina Tintura #2',
            defaults={
                'capacidad_maxima': Decimal('500.00'),
                'eficiencia_ideal': Decimal('0.85'),
                'estado': 'operativa',
                'area': area_tintura
            }
        )
        maquina_tejido, _ = Maquina.objects.get_or_create(
            nombre='Telar Automático',
            defaults={
                'capacidad_maxima': Decimal('1000.00'),
                'eficiencia_ideal': Decimal('0.90'),
                'estado': 'operativa',
                'area': area_tejido
            }
        )

        self.stdout.write(self.style.SUCCESS('✓ Máquinas creadas'))

        # 9. Create Production Orders
        for i in range(1, 4):
            OrdenProduccion.objects.get_or_create(
                codigo=f'OP-2025-{str(i).zfill(3)}',
                defaults={
                    'producto': hilo_algodon if i % 2 == 0 else hilo_poliester,
                    'formula_color': formula_rojo if i % 2 == 0 else formula_azul,
                    'bodega_quimicos': bodega_quimicos,
                    'peso_neto_requerido': Decimal('200.00') + (i * Decimal('50.00')),
                    'estado': ['pendiente', 'en_proceso', 'finalizada'][i-1],
                    'sede': sede,
                    'area': area_tintura,
                    'maquina_asignada': maquina1 if i <= 2 else maquina2,
                    'observaciones': f'Orden de prueba #{i}'
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Órdenes de producción creadas'))

        # 10. Create Customers
        clientes_data = [
            ('RUC-001', 'Textiles Andinos S.A.', 'Quito, Pichincha', 'mayorista', Decimal('5000.00')),
            ('RUC-002', 'Tejidos del Sur', 'Cuenca, Azuay', 'mayorista', Decimal('3000.00')),
            ('RUC-003', 'Moda Express', 'Guayaquil, Guayas', 'normal', Decimal('1500.00')),
            ('RUC-004', 'Tienda de Telas Premium', 'Quito, Pichincha', 'normal', Decimal('2000.00')),
        ]

        clientes = []
        for ruc, nombre, direccion, nivel, limite_credito in clientes_data:
            cliente, _ = Cliente.objects.get_or_create(
                ruc_cedula=ruc,
                defaults={
                    'nombre_razon_social': nombre,
                    'direccion_envio': direccion,
                    'nivel_precio': nivel,
                    'limite_credito': limite_credito,
                    'plazo_credito_dias': 30,
                    'is_active': True
                }
            )
            clientes.append(cliente)

        self.stdout.write(self.style.SUCCESS('✓ Clientes creados'))

        # 11. Create Sales Orders
        for idx, cliente in enumerate(clientes):
            pedido, _ = PedidoVenta.objects.get_or_create(
                guia_remision=f'GR-2025-{str(idx+1).zfill(3)}',
                defaults={
                    'cliente': cliente,
                    'fecha_pedido': timezone.now(),
                    'estado': ['pendiente', 'despachado', 'facturado', 'pendiente'][idx % 4],
                    'esta_pagado': idx % 3 == 0,
                    'sede': sede,
                    'valor_retencion': Decimal('0.00')
                }
            )

            producto = [hilo_algodon, hilo_poliester, tela_algodon, hilo_algodon][idx % 4]
            DetallePedido.objects.get_or_create(
                pedido_venta=pedido,
                producto=producto,
                defaults={
                    'cantidad': 100 + (idx * 50),
                    'piezas': 10 + idx,
                    'peso': Decimal('150.00') + (idx * Decimal('25.00')),
                    'precio_unitario': Decimal('10.00')
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Pedidos de venta creados'))

        # 12. Create Test Users
        password = 'password123'
        group_names = [
            'operario', 'bodeguero', 'vendedor', 'jefe_area',
            'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas',
            'empaquetado', 'despacho', 'tintorero'
        ]

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        for group_name in group_names:
            Group.objects.get_or_create(name=group_name)

        for group_name in group_names:
            username = f'user_{group_name}'
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'password': password,
                    'email': f'{username}@example.com',
                    'first_name': group_name.replace('_', ' ').title(),
                    'last_name': 'Test'
                }
            )

            if created:
                user.set_password(password)

            if group_name != 'admin_sistemas':
                user.sede = sede

                if group_name == 'empaquetado':
                    user.area = area_empaque
                elif group_name in ['tintorero', 'operario']:
                    user.area = area_tintura
                elif group_name == 'jefe_area':
                    user.area = area_general
                else:
                    user.area = area_general

                user.bodegas_asignadas.set([bodega_mp, bodega_pt, bodega_insumos, bodega_quimicos])

            user.groups.set([Group.objects.get(name=group_name)])
            user.save()

        self.stdout.write(self.style.SUCCESS('✓ Usuarios de prueba creados'))

        self.stdout.write(self.style.SUCCESS(self.style.SUCCESS('=' * 50)))
        self.stdout.write(self.style.SUCCESS('✓ Base de datos cargada completamente!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'\nCredenciales de prueba (todas con contraseña: {password}):')
        for group_name in group_names:
            self.stdout.write(f'  • user_{group_name}')