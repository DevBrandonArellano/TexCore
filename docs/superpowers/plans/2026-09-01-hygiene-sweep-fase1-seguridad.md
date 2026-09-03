# Barrido de Higiene — Fase 1: Seguridad Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado: FASE 1 COMPLETA (2026-09-01).** Las 6 tareas se implementaron y commitearon el 2026-09-01 (commits `2c6c1d5`, `507da99`, `8a62b59`, `7a60db6`, `b0561b3`, `3173ea3`, `e2f1d49`, todos por Brandon). `graphify update .` se corrió al cierre de la Tarea 6 (14:52) pero quedó sin commitear cuando la sesión se quedó sin tokens — pendiente de que Brandon revise y commitee `graphify-out/`. Detalle de verificación final abajo.

**Goal:** Cerrar los 5 hallazgos de seguridad del diagnóstico de higiene del backend (credenciales hardcodeadas, permisos de escritura abiertos, excepción silenciada, falta de locks en transiciones de estado) sin romper ningún flujo existente.

**Architecture:** Cada tarea es un cambio aislado a 1-2 archivos ya existentes, siguiendo patrones que ya usa el propio proyecto (permisos por acción vía `get_permissions()`, generación segura de contraseña como en `seed_production_masters.py`, `select_for_update()` como en `PagoClienteViewSet.perform_create`). No se crean archivos nuevos salvo 2 archivos de test.

**Tech Stack:** Django 5 + DRF, `pytest`/`manage.py test --settings=TexCore.settings_test` (SQL Server real vía `mssql` engine — soporta locking real), `factory_boy` (`gestion/tests/factories.py`).

**Spec:** `docs/superpowers/specs/2026-09-01-backend-hygiene-sweep-design.md` (sección "Fase 1 — Seguridad")

## Global Constraints

- No se edita nada en `migrations/`.
- Este plan corre directamente sobre la rama `feature` (Brandon declinó el worktree aislado — decisión explícita del 2026-09-01). Los commits por tarea que exige `subagent-driven-development` (uno por tarea, para poder generar el diff que revisa cada task-reviewer) se hacen normalmente ahí; no hay `git push`.
- **Sin base de datos disponible en este entorno** (no hay Docker/SQL Server local — `django.db.utils.InterfaceError: Data source name not found`, confirmado 2026-09-01). Ningún paso "Run: python manage.py test ... / Expected: PASS|FAIL" de este plan es ejecutable aquí. Cada implementador debe: escribir el código y el test tal como está especificado, intentar correr el comando igual (para dejar constancia del error de conexión esperado, no un fallo real), y luego verificar manualmente por lectura que el test compila conceptualmente contra el código real (nombres de campos/métodos/URLs existen, la aserción corresponde al comportamiento nuevo) — dejar esto explícito en su reporte. El task-reviewer verifica por lectura del diff, no ejecutando pytest. Brandon corre la suite completa fuera de esta sesión al cerrar la fase.
- Todo fix de comportamiento lleva un test `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]` (ISTQB) que falla antes del fix y pasa después.
- Usar `factory_boy` (`gestion/tests/factories.py`) para datos de prueba, nunca fixtures JSON manuales.
- `graphify explain "<símbolo>"` antes de tocar cualquier permiso/vista para confirmar que no hay otro caller que dependa del comportamiento actual; `graphify update .` al cerrar la fase completa (después de la Tarea 6, no después de cada tarea individual).
- Los scripts de deploy (`scripts/deploy/deploy_prod.sh`/`.ps1`) **no se tocan** en esta fase — la decisión de cuál script usar en producción queda fuera de este plan (ver spec, sección 3).

---

### Task 1: `create_admin.py` — eliminar credenciales hardcodeadas ✅ COMPLETADO (`2c6c1d5`, fixup `507da99`)

**Files:**
- Modify: `gestion/management/commands/create_admin.py`
- Test: `gestion/tests/test_create_admin_command.py` (nuevo)

**Interfaces:** Ninguna — cambio aislado, no lo consume ni lo produce ninguna otra tarea de este plan.

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/test_create_admin_command.py`:

```python
"""
Pruebas de gestion/management/commands/create_admin.py — Fase 1.1 del
barrido de higiene (2026-09-01): el comando ya no puede generar una
contraseña estática/predecible.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con DJANGO_SUPERUSER_PASSWORD / sin ella,
  superuser ya existente / no existente.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class CreateAdminCommandTestCase(TestCase):
    def test_create_admin_dado_sin_env_vars_cuando_ejecuta_entonces_password_no_es_estatica(self):
        call_command('create_admin')
        User = get_user_model()
        user = User.objects.get(username='sistemas')
        self.assertFalse(user.check_password('Sistemas2026*'))

    def test_create_admin_dado_password_env_var_cuando_ejecuta_entonces_usa_esa_password(self):
        os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'ClaveDePruebaSegura123!'
        try:
            call_command('create_admin')
            User = get_user_model()
            user = User.objects.get(username='sistemas')
            self.assertTrue(user.check_password('ClaveDePruebaSegura123!'))
        finally:
            del os.environ['DJANGO_SUPERUSER_PASSWORD']

    def test_create_admin_dado_superuser_ya_existe_cuando_ejecuta_entonces_no_duplica(self):
        call_command('create_admin')
        User = get_user_model()
        self.assertEqual(User.objects.filter(username='sistemas').count(), 1)
        call_command('create_admin')
        self.assertEqual(User.objects.filter(username='sistemas').count(), 1)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test gestion.tests.test_create_admin_command --settings=TexCore.settings_test -v 2`
Expected: FAIL en `test_..._password_no_es_estatica` (el comando actual SÍ crea la contraseña estática `Sistemas2026*`, así que `assertFalse` falla) y en `test_..._password_env_var...` (el comando actual ignora `DJANGO_SUPERUSER_PASSWORD`).

- [ ] **Step 3: Implementar el fix**

Editar `gestion/management/commands/create_admin.py` — reemplazar el `handle()` completo (líneas 15-24) y agregar imports:

```python
import os
import secrets

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist, or verifies audit with --verificar'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verificar',
            action='store_true',
            help='Verifica la auditoría en lugar de crear superuser',
        )

    def handle(self, *args, **options):
        if options.get('verificar'):
            self._verificar_auditoria()
            return

        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'sistemas')
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists.'))
            return

        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'sistemas@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        password_generada = password is None
        if password_generada:
            password = secrets.token_urlsafe(18)

        User.objects.create_superuser(username, email, password)
        self.stdout.write(self.style.SUCCESS(f'Successfully created new superuser "{username}"'))
        if password_generada:
            self.stdout.write(self.style.WARNING(
                f'No se definió DJANGO_SUPERUSER_PASSWORD — se generó una contraseña aleatoria. '
                f'Anótala ahora, no se volverá a mostrar: {password}'
            ))
```

(El método `_verificar_auditoria` al final del archivo no cambia — se deja tal cual.)

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python manage.py test gestion.tests.test_create_admin_command --settings=TexCore.settings_test -v 2`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add gestion/management/commands/create_admin.py gestion/tests/test_create_admin_command.py
git commit -m "fix(security): create_admin ya no genera contraseña hardcodeada"
```

---

### Task 2: `sales_views.py` — cerrar permisos de escritura abiertos ✅ COMPLETADO (`8a62b59`)

**Files:**
- Modify: `gestion/views/sales_views.py:30-37` (`ClienteViewSet`), `:285-287` (`PedidoVentaViewSet`), `:636-643` (`DetallePedidoViewSet`)
- Test: `gestion/tests/test_sales_views_extra.py` (agregar 3 clases nuevas al final)

**Interfaces:** Ninguna — cambio aislado a este archivo. `IsVendedorOrEjecutivoOrAdmin` e `IsAdminSistemasOrSede` ya están importados en el archivo (línea 9-11), no hace falta agregar imports.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `gestion/tests/test_sales_views_extra.py` — el archivo ya importa todo lo necesario (`ClienteFactory, CustomUserFactory, ProductoFactory, SedeFactory` de `gestion.tests.factories`, y `Cliente, DetallePedido, PagoCliente, PedidoVenta` de `gestion.models`, más `TestCase`, `reverse`, `APIClient`, `status`), no hace falta agregar ningún import:

```python
class ClienteViewSetPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()

    def test_create_dado_operario_cuando_post_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.post(reverse('cliente-list'), {
            'nombre_razon_social': 'Cliente No Autorizado', 'ruc_cedula': '1701111111',
            'direccion_envio': 'Calle QA', 'limite_credito': '500.00', 'nivel_precio': 'normal',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_dado_operario_cuando_delete_entonces_403(self):
        cliente = ClienteFactory(sede=self.sede)
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.delete(reverse('cliente-detail', args=[cliente.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_dado_operario_cuando_get_entonces_200(self):
        ClienteFactory(sede=self.sede)
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('cliente-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class PedidoVentaViewSetPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)

    def test_create_dado_operario_cuando_post_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.post(reverse('pedidoventa-list'), {
            'cliente': self.cliente.id, 'sede': self.sede.id, 'guia_remision': 'GUIA-QA-001',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_dado_operario_cuando_delete_entonces_403(self):
        pedido = PedidoVenta.objects.create(cliente=self.cliente, sede=self.sede, guia_remision='GUIA-QA-002')
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.delete(reverse('pedidoventa-detail', args=[pedido.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_dado_operario_cuando_get_entonces_200(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('pedidoventa-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class DetallePedidoViewSetPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.pedido = PedidoVenta.objects.create(cliente=self.cliente, sede=self.sede, guia_remision='GUIA-QA-003')

    def _payload(self):
        return {
            'pedido_venta': self.pedido.id, 'producto': self.producto.id,
            'cantidad': 1, 'piezas': 1, 'peso': '1.000', 'precio_unitario': '10.000',
        }

    def test_create_dado_operario_cuando_post_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.post(reverse('detallepedido-list'), self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_vendedor_cuando_post_entonces_201(self):
        vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        self.client.force_authenticate(user=vendedor)
        resp = self.client.post(reverse('detallepedido-list'), self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python manage.py test gestion.tests.test_sales_views_extra --settings=TexCore.settings_test -v 2`
Expected: FAIL en `test_create_dado_operario_cuando_post_entonces_403` y `test_destroy_dado_operario_cuando_delete_entonces_403` de `ClienteViewSetPermissionsTestCase` y `PedidoVentaViewSetPermissionsTestCase` (hoy responden 201/204, no 403). El resto ya pasa (comportamiento actual).

- [ ] **Step 3: Implementar el fix**

En `gestion/views/sales_views.py`, reemplazar la línea 32 (`ClienteViewSet`):

```python
class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsVendedorOrEjecutivoOrAdmin()]
```

Reemplazar la línea 287 (`PedidoVentaViewSet`):

```python
class PedidoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVentaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsVendedorOrEjecutivoOrAdmin()]
        return [IsAuthenticated()]
```

Reemplazar el `get_permissions()` de `DetallePedidoViewSet` (líneas 640-643):

```python
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated(), IsVendedorOrEjecutivoOrAdmin()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python manage.py test gestion.tests.test_sales_views_extra --settings=TexCore.settings_test -v 2`
Expected: PASS (todos)

Correr también la suite completa de `sales_views` para confirmar que no se rompió nada existente (`anular`/`modificar` tienen su propio chequeo de rol interno, no deben verse afectados):

Run: `python manage.py test gestion.tests --settings=TexCore.settings_test -v 2 -k sales`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add gestion/views/sales_views.py gestion/tests/test_sales_views_extra.py
git commit -m "fix(security): restringe create/update/destroy de Cliente, PedidoVenta y DetallePedido a roles comerciales"
```

---

### Task 3: `kardex_views.py` — scoping por bodega/sede ✅ COMPLETADO (`7a60db6`)

**Files:**
- Modify: `inventory/views/kardex_views.py:129-177` (`RetroKardexAPIView`), `:180-213` (`MovimientosPorLoteAPIView`)
- Test: `inventory/tests/test_views_endpoints.py` (agregar 2 clases nuevas al final)

**Interfaces:** Ninguna. `IsInventoryStaffOrAdmin` ya está importado en `kardex_views.py` (línea 12).

- [ ] **Step 1: Escribir los tests que fallan**

El archivo `inventory/tests/test_views_endpoints.py` hoy solo importa `Decimal`, `TestCase`, `APIClient`, `status`, y de `gestion.tests.factories`: `SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory, StockBodegaFactory`. Agregar al inicio del archivo:

```python
from django.urls import reverse
from inventory.models import MovimientoInventario
from gestion.tests.factories import AreaFactory, OrdenProduccionFactory, LoteProduccionFactory
```

Y agregar al final del archivo:

```python
class RetroKardexAPIViewScopingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.producto = ProductoFactory(sede=self.sede)
        self.bodega_a = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede)
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto,
            bodega_destino=self.bodega_a, cantidad=Decimal('10.000'),
        )
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto,
            bodega_destino=self.bodega_b, cantidad=Decimal('20.000'),
        )

    def test_retro_kardex_dado_bodeguero_sin_bodega_b_asignada_cuando_get_entonces_no_ve_bodega_b(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        bodegas_vistas = {r['bodega'] for r in resp.data}
        self.assertIn(self.bodega_a.nombre, bodegas_vistas)
        self.assertNotIn(self.bodega_b.nombre, bodegas_vistas)

    def test_retro_kardex_dado_admin_cuando_get_entonces_ve_todas_las_bodegas(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        bodegas_vistas = {r['bodega'] for r in resp.data}
        self.assertIn(self.bodega_a.nombre, bodegas_vistas)
        self.assertIn(self.bodega_b.nombre, bodegas_vistas)

    def test_retro_kardex_dado_operario_raso_cuando_get_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MovimientosPorLoteAPIViewScopingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.bodega_a = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede)
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.lote = LoteProduccionFactory(orden_produccion=self.op)
        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION', producto=self.op.producto_salida,
            bodega_destino=self.bodega_a, cantidad=Decimal('5.000'), lote=self.lote,
        )

    def test_movimientos_por_lote_dado_bodeguero_sin_bodega_a_asignada_cuando_get_entonces_historial_vacio(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_b)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('movimientos-lote', args=[self.lote.codigo_lote]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['historial'], [])

    def test_movimientos_por_lote_dado_bodeguero_con_bodega_a_asignada_cuando_get_entonces_ve_movimiento(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('movimientos-lote', args=[self.lote.codigo_lote]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['historial']), 1)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python manage.py test inventory.tests.test_views_endpoints --settings=TexCore.settings_test -v 2`
Expected: FAIL en `test_retro_kardex_dado_bodeguero_sin_bodega_b_asignada...` (hoy ve ambas bodegas), `test_retro_kardex_dado_operario_raso...` (hoy responde 200, no 403), y `test_movimientos_por_lote_dado_bodeguero_sin_bodega_a_asignada...` (hoy ve el movimiento igual).

- [ ] **Step 3: Implementar el fix**

En `inventory/views/kardex_views.py`, cambiar `permission_classes` en ambas clases (líneas 133 y 184) de `[permissions.IsAuthenticated]` a `[IsInventoryStaffOrAdmin]`.

Reemplazar el método `get` de `RetroKardexAPIView` completo (líneas 135-177):

```python
    def get(self, request, *args, **kwargs):
        producto_id = request.query_params.get('producto_id')
        fecha_corte = request.query_params.get('fecha_corte')
        bodega_id = request.query_params.get('bodega_id')
        sede_id = request.query_params.get('sede_id')

        if not producto_id or not fecha_corte:
            return Response(
                {"error": "Los parámetros 'producto_id' y 'fecha_corte' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        get_object_or_404(Producto, pk=producto_id)

        query_filter = models.Q(producto_id=producto_id, fecha__lte=fecha_corte)
        if bodega_id:
            query_filter &= (models.Q(bodega_origen_id=bodega_id) | models.Q(bodega_destino_id=bodega_id))
        if sede_id:
            query_filter &= (models.Q(bodega_origen__sede_id=sede_id) | models.Q(bodega_destino__sede_id=sede_id))

        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()):
            bodegas_asignadas = list(user.bodegas_asignadas.values_list('id', flat=True))
            query_filter &= (
                models.Q(bodega_origen_id__in=bodegas_asignadas) | models.Q(bodega_destino_id__in=bodegas_asignadas)
            )

        movs = MovimientoInventario.objects.select_related('bodega_origen', 'bodega_destino').filter(query_filter)

        stock_por_bodega = {}
        for m in movs:
            if m.bodega_destino_id:
                if bodega_id and str(m.bodega_destino_id) != str(bodega_id):
                    pass
                else:
                    stock_por_bodega[m.bodega_destino.nombre] = stock_por_bodega.get(
                        m.bodega_destino.nombre, Decimal('0.00')) + m.cantidad
            if m.bodega_origen_id:
                if bodega_id and str(m.bodega_origen_id) != str(bodega_id):
                    pass
                else:
                    stock_por_bodega[m.bodega_origen.nombre] = stock_por_bodega.get(
                        m.bodega_origen.nombre, Decimal('0.00')) - m.cantidad

        resultados = [
            {"bodega": bodega, "stock_calculado": cantidad}
            for bodega, cantidad in stock_por_bodega.items() if cantidad != 0
        ]

        return Response(resultados, status=status.HTTP_200_OK)
```

Reemplazar el método `get` de `MovimientosPorLoteAPIView` completo (líneas 186-212):

```python
    def get(self, request, lote_codigo, *args, **kwargs):
        lote = get_object_or_404(LoteProduccion, codigo_lote=lote_codigo)

        movimientos = MovimientoInventario.objects.select_related(
            'bodega_origen', 'bodega_destino', 'producto', 'usuario'
        ).filter(lote=lote)

        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()):
            bodegas_asignadas = user.bodegas_asignadas.values_list('id', flat=True)
            movimientos = movimientos.filter(
                models.Q(bodega_origen_id__in=bodegas_asignadas) | models.Q(bodega_destino_id__in=bodegas_asignadas)
            )

        movimientos = movimientos.order_by('fecha')

        data = []
        producto_desc = "N/A"
        for m in movimientos:
            producto_desc = m.producto.descripcion
            data.append({
                "id": m.id,
                "fecha": m.fecha,
                "tipo_movimiento": m.get_tipo_movimiento_display(),
                "bodega_origen": m.bodega_origen.nombre if m.bodega_origen else "-",
                "bodega_destino": m.bodega_destino.nombre if m.bodega_destino else "-",
                "cantidad": m.cantidad,
                "documento_ref": m.documento_ref,
                "usuario": m.usuario.get_full_name() or m.usuario.username if m.usuario else "Sistema"
            })

        return Response({
            "lote_codigo": lote.codigo_lote,
            "producto": producto_desc,
            "historial": data
        }, status=status.HTTP_200_OK)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python manage.py test inventory.tests.test_views_endpoints --settings=TexCore.settings_test -v 2`
Expected: PASS (todos)

Correr también `KardexBodegaAPIView` (no tocada) para confirmar que no se rompió nada:

Run: `python manage.py test inventory.tests --settings=TexCore.settings_test -v 2 -k kardex`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add inventory/views/kardex_views.py inventory/tests/test_views_endpoints.py
git commit -m "fix(security): RetroKardexAPIView y MovimientosPorLoteAPIView ahora acotan por bodega/sede"
```

---

### Task 4: `transferencia_views.py` — dejar de silenciar la excepción ✅ COMPLETADO (`b0561b3`)

**Files:**
- Modify: `inventory/views/transferencia_views.py:85-90`
- Test: `inventory/tests/test_views_endpoints.py` (agregar 1 test a `TransferenciaStockAPIViewTestCase`)

**Interfaces:** Ninguna. `logger` ya está definido en el archivo (línea 14: `logger = logging.getLogger('inventory.views')`).

- [ ] **Step 1: Escribir el test que falla**

El archivo no importa `unittest.mock.patch` todavía — agregar `from unittest.mock import patch` a sus imports (junto a `from decimal import Decimal`). Luego, agregar dentro de la clase existente `TransferenciaStockAPIViewTestCase` (ya autentica un admin en `setUp()` y define `self.origen`, `self.destino`, `self.producto`, `self.url`, y el helper `self._stock_origen(cantidad)`):

```python
    def test_transferencia_dado_error_inesperado_cuando_post_entonces_queda_logueado(self):
        self._stock_origen('100.00')
        with patch('inventory.views.transferencia_views.logger') as mock_logger:
            with patch(
                'inventory.views.transferencia_views.safe_get_or_create_stock',
                side_effect=RuntimeError('fallo simulado'),
            ):
                resp = self.client.post(self.url, {
                    'producto_id': self.producto.id, 'cantidad': '10.00',
                    'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
                }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        mock_logger.error.assert_called_once()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test inventory.tests.test_views_endpoints --settings=TexCore.settings_test -v 2 -k test_transferencia_dado_error_inesperado`
Expected: FAIL — `mock_logger.error.assert_called_once()` falla porque el `except` actual no llama a `logger.error(...)`.

- [ ] **Step 3: Implementar el fix**

En `inventory/views/transferencia_views.py`, reemplazar líneas 85-90:

```python
        except Exception as e:
            logger.error("Error inesperado en transferencia de stock", exc_info=True)
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python manage.py test inventory.tests.test_views_endpoints --settings=TexCore.settings_test -v 2 -k Transferencia`
Expected: PASS (todos, incluido el nuevo)

- [ ] **Step 5: Commit**

```bash
git add inventory/views/transferencia_views.py inventory/tests/test_views_endpoints.py
git commit -m "fix(security): TransferenciaStockAPIView ya no silencia excepciones inesperadas"
```

---

### Task 5: `production_subproceso_views.py` — atomicidad + lock en transiciones de estado ✅ COMPLETADO (`3173ea3`)

**Files:**
- Modify: `gestion/views/production_subproceso_views.py:1-19` (imports), `:66-139` (las 4 acciones)
- Test: `gestion/tests/test_production_views.py` (agregar 4 tests a `SubprocesoStateMachineTestCase`)

**Interfaces:** Ninguna.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar dentro de la clase existente `SubprocesoStateMachineTestCase` en `gestion/tests/test_production_views.py`. El archivo ya importa `from unittest.mock import patch` (línea 16) y `OrdenProduccionSubproceso` (la propia clase ya lo usa en su método `_subproceso()`, línea 788) — no hace falta agregar ningún import:

```python
    def test_iniciar_dado_pendiente_cuando_patch_entonces_bloquea_subproceso_con_select_for_update(self):
        sp = self._subproceso('pendiente')
        with patch.object(
            OrdenProduccionSubproceso.objects, 'select_for_update',
            wraps=OrdenProduccionSubproceso.objects.select_for_update,
        ) as mock_lock:
            resp = self.client.patch(reverse('orden-produccion-subproceso-iniciar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_lock.assert_called_once()

    def test_completar_dado_en_progreso_cuando_patch_entonces_bloquea_subproceso_con_select_for_update(self):
        sp = self._subproceso('en_progreso')
        with patch.object(
            OrdenProduccionSubproceso.objects, 'select_for_update',
            wraps=OrdenProduccionSubproceso.objects.select_for_update,
        ) as mock_lock:
            resp = self.client.patch(reverse('orden-produccion-subproceso-completar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_lock.assert_called_once()

    def test_rechazar_dado_pendiente_cuando_patch_entonces_bloquea_subproceso_con_select_for_update(self):
        sp = self._subproceso('pendiente')
        with patch.object(
            OrdenProduccionSubproceso.objects, 'select_for_update',
            wraps=OrdenProduccionSubproceso.objects.select_for_update,
        ) as mock_lock:
            resp = self.client.patch(
                reverse('orden-produccion-subproceso-rechazar-subproceso', args=[sp.id]),
                {'motivo_rechazo': 'Material no disponible'}, format='json'
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_lock.assert_called_once()

    def test_pausar_dado_en_progreso_cuando_patch_entonces_bloquea_subproceso_con_select_for_update(self):
        sp = self._subproceso('en_progreso')
        with patch.object(
            OrdenProduccionSubproceso.objects, 'select_for_update',
            wraps=OrdenProduccionSubproceso.objects.select_for_update,
        ) as mock_lock:
            resp = self.client.patch(reverse('orden-produccion-subproceso-pausar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_lock.assert_called_once()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python manage.py test gestion.tests.test_production_views.SubprocesoStateMachineTestCase --settings=TexCore.settings_test -v 2`
Expected: FAIL en los 4 tests nuevos (`mock_lock.assert_called_once()` — hoy ninguna acción llama a `select_for_update`).

- [ ] **Step 3: Implementar el fix**

En `gestion/views/production_subproceso_views.py`, agregar el import de `transaction` (línea 3, junto a `from django.utils import timezone`):

```python
from django.db import transaction
from django.utils import timezone
```

Reemplazar las 4 acciones (líneas 66-139) completas:

```python
    @action(detail=True, methods=['patch'])
    def iniciar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        with transaction.atomic():
            subproceso = OrdenProduccionSubproceso.objects.select_for_update().get(pk=subproceso.pk)
            if subproceso.estado != 'pendiente':
                return Response(
                    {'detail': 'Solo se pueden iniciar subprocesos en estado pendiente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subproceso.estado = 'en_progreso'
            subproceso.fecha_inicio_real = timezone.now()
            subproceso.usuario_responsable = request.user
            subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def completar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        with transaction.atomic():
            subproceso = OrdenProduccionSubproceso.objects.select_for_update().get(pk=subproceso.pk)
            if subproceso.estado not in ['en_progreso', 'pausado']:
                return Response(
                    {'detail': 'El subproceso debe estar en progreso o pausado para completarse.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subproceso.estado = 'completado'
            subproceso.fecha_fin_real = timezone.now()
            subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
            subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def rechazar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        with transaction.atomic():
            subproceso = OrdenProduccionSubproceso.objects.select_for_update().get(pk=subproceso.pk)
            if subproceso.estado == 'completado':
                return Response(
                    {'detail': 'No se puede rechazar un subproceso completado.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subproceso.estado = 'rechazado'
            subproceso.motivo_rechazo = request.data.get('motivo_rechazo', '')
            subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
            subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def pausar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        with transaction.atomic():
            subproceso = OrdenProduccionSubproceso.objects.select_for_update().get(pk=subproceso.pk)
            if subproceso.estado != 'en_progreso':
                return Response(
                    {'detail': 'Solo se pueden pausar subprocesos en progreso.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subproceso.estado = 'pausado'
            subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
            subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )
```

Nota: `self.get_object()` se mantiene como primera llamada en cada acción — es lo que aplica el scoping por área (`get_queryset()`) y el chequeo de permisos a nivel de objeto de DRF. El `select_for_update().get(pk=...)` que sigue es un re-fetch deliberado dentro de la transacción para adquirir el lock antes de leer/mutar `estado`.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python manage.py test gestion.tests.test_production_views.SubprocesoStateMachineTestCase --settings=TexCore.settings_test -v 2`
Expected: PASS (todos, incluidos los 4 nuevos)

Correr también `SubprocesoQuerysetScopingTestCase` (no tocada) para confirmar que el scoping por área sigue intacto:

Run: `python manage.py test gestion.tests.test_production_views.SubprocesoQuerysetScopingTestCase --settings=TexCore.settings_test -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add gestion/views/production_subproceso_views.py gestion/tests/test_production_views.py
git commit -m "fix(security): transiciones de estado de subproceso ahora usan select_for_update en transaccion atomica"
```

---

### Task 6: `generate_next_lote_codigo` — lock sobre la orden ✅ COMPLETADO (`e2f1d49`)

**Files:**
- Modify: `gestion/services/registro_lote.py:1-16` (imports), `:29` (inicio de `registrar_lote`)
- Test: `gestion/tests/test_registro_lote_lock.py` (nuevo)

**Interfaces:** Ninguna.

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/test_registro_lote_lock.py`:

```python
"""
Fase 1.5b del barrido de higiene (2026-09-01): generate_next_lote_codigo()
(gestion/models/produccion.py) lee lotes.count() sin lock — dos registros
concurrentes del mismo OP podrían calcular el mismo código de lote
(mitigado solo por unique_together, que falla con IntegrityError en vez de
prevenir la condición de carrera). registrar_lote() ahora adquiere
select_for_update() sobre la orden antes de generar el código.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from gestion.models import OrdenProduccion
from gestion.services.registro_lote import RegistroLoteService
from gestion.tests.factories import CustomUserFactory, OrdenProduccionFactory, StockBodegaFactory


class RegistroLoteLockTestCase(TestCase):
    def setUp(self):
        self.orden = OrdenProduccionFactory()
        self.user = CustomUserFactory(sede=self.orden.sede)
        StockBodegaFactory(
            bodega=self.orden.bodega_entrada, producto=self.orden.producto_entrada,
            cantidad=Decimal('1000.00'), lote=None,
        )

    def test_registrar_lote_dado_orden_cuando_registra_entonces_bloquea_orden_con_select_for_update(self):
        lote_data = {
            'peso_neto_producido': '10.00',
            'peso_merma': '0.00',
            'tipo_merma': 'maquina',
            'turno': 'Dia',
            'hora_inicio': '2026-09-01T08:00:00Z',
            'hora_final': '2026-09-01T10:00:00Z',
        }
        with patch.object(
            OrdenProduccion.objects, 'select_for_update',
            wraps=OrdenProduccion.objects.select_for_update,
        ) as mock_lock:
            RegistroLoteService.registrar_lote(self.orden, lote_data, self.user)

        mock_lock.assert_called_once()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test gestion.tests.test_registro_lote_lock --settings=TexCore.settings_test -v 2`
Expected: FAIL — `mock_lock.assert_called_once()` falla porque `registrar_lote` hoy nunca llama a `select_for_update`.

- [ ] **Step 3: Implementar el fix**

En `gestion/services/registro_lote.py`, agregar `OrdenProduccion` al import existente (línea 8):

```python
from gestion.models import CustomUser, LoteProduccion, Maquina, OrdenProduccion
```

Agregar el lock como primera línea del cuerpo de `registrar_lote` (después de la línea 29, antes de `peso_neto = ...`):

```python
    @staticmethod
    @transaction.atomic
    def registrar_lote(orden, lote_data: dict, user, completar_orden: bool = False):
        # Lock de la orden para serializar registros concurrentes de lotes:
        # generate_next_lote_codigo() (más abajo) lee lotes.count() sin lock;
        # sin esto, dos requests concurrentes podrían calcular el mismo código.
        OrdenProduccion.objects.select_for_update().get(pk=orden.pk)

        peso_neto = Decimal(str(lote_data['peso_neto_producido'])).quantize(Decimal('0.01'))
        ...
```

(El resto del método, desde `peso_neto = ...` en adelante, no cambia — se deja tal cual está hoy.)

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python manage.py test gestion.tests.test_registro_lote_lock --settings=TexCore.settings_test -v 2`
Expected: PASS

Correr también la suite completa de `registro_lote` para confirmar que no se rompió nada (el lock es un `get()` adicional, no cambia el resto del flujo):

Run: `python manage.py test gestion.tests.test_registro_lote_merma gestion.tests.test_registro_lote_transformacion --settings=TexCore.settings_test -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add gestion/services/registro_lote.py gestion/tests/test_registro_lote_lock.py
git commit -m "fix(security): registrar_lote bloquea la orden antes de generar el codigo de lote"
```

---

## Verificación final de la fase

- [ ] Correr la suite completa afectada: `python manage.py test gestion.tests inventory.tests --settings=TexCore.settings_test -v 2` — 0 fallos. **Pendiente**: no ejecutable en esta máquina (sin Docker/SQL Server local, restricción ya conocida — ver Global Constraints). Brandon debe correrla fuera de esta sesión.
- [x] `cd frontend && npx tsc --noEmit` — confirmar que el frontend no dependía de que `ClienteViewSet`/`PedidoVentaViewSet`/`DetallePedidoViewSet` estuvieran abiertos a cualquier autenticado. Verificado por lectura (2026-09-02): los únicos consumidores de escritura de `cliente`/`pedido-venta`/`detalle-pedido` en `frontend/src` están en `vendedor/`, `ejecutivos/` y `admin-sistemas/ManageClientes.tsx` — todos roles ya cubiertos por `IsVendedorOrEjecutivoOrAdmin`. `despacho/` solo lee pedidos, no escribe. Sin conflicto. (No se corrió `tsc --noEmit` en sí — pendiente que Brandon lo confirme junto con la suite de tests.)
- [x] `graphify update .` para refrescar el grafo con estos 6 cambios. Ejecutado 2026-09-01 14:52 al cerrar la Tarea 6 (`graphify-out/graph.json`, `manifest.json`, `GRAPH_REPORT.md` actualizados) — **quedó sin commitear** cuando la sesión se quedó sin tokens. Sigue sin commitear al 2026-09-02; Brandon debe revisar y commitear `graphify-out/` junto con esta actualización de documentación.
- [ ] Brandon revisa los 6 commits y decide si los aplasta en uno solo o los deja separados antes de mergear. **Pendiente** — commits ya en `feature`, no mergeados/aplastados.
