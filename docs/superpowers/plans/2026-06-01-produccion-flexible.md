# Producción Flexible — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender el modelo de producción para soportar transformación producto_entrada→producto_salida, mezcla de lotes, y merma como producto vendible, con CRUD en dashboards, auditoría completa (ISO 27001 A.12.4), controles COBIT DSS06 y TDD.

**Architecture:** Opción A — cambio quirúrgico sobre modelos existentes. Nuevos modelos `ComponenteMezclaOP` y `ConsumoLoteDetalle` se agregan sin romper datos existentes. Nuevos services `ConsumoMezclaService` y `MermaStockService` siguen SRP. Frontend actualiza dashboards por rol con patrón DataTable+Dialog+TanStack Query existente.

**Tech Stack:** Django 5.x + DRF, React 18 + TypeScript, factory_boy, pytest-django, Zod, TanStack Query, Shadcn/UI, SQL Server 2022.

---

## File Map

### Backend — nuevos/modificados
```
gestion/models.py                              MODIFY — OrdenProduccion, Maquina
gestion/migrations/0060_rename_producto_entrada.py   CREATE
gestion/migrations/0061_rename_bodega_entrada.py     CREATE
gestion/migrations/0062_add_producto_salida.py       CREATE
gestion/migrations/0063_componente_mezcla_op.py      CREATE
gestion/migrations/0064_consumo_lote_detalle.py      CREATE
gestion/migrations/0065_maquina_merma_fields.py      CREATE
gestion/migrations/0066_backfill_producto_salida.py  CREATE
gestion/migrations/0067_make_producto_salida_required.py CREATE
gestion/services/consumo_mezcla.py             CREATE — ConsumoMezclaService (SRP)
gestion/services/merma_stock.py                CREATE — MermaStockService (SRP)
gestion/services/registro_lote.py              MODIFY — usar producto_entrada/salida, delegar a nuevos services
gestion/serializers.py                         MODIFY — OrdenProduccionSerializer + nuevos
gestion/views/production_views.py              MODIFY — OrdenProduccionViewSet, LoteProduccionViewSet
gestion/tests/factories.py                     MODIFY — nuevas factories
gestion/tests/test_consumo_mezcla_service.py   CREATE
gestion/tests/test_merma_stock_service.py      CREATE
gestion/tests/test_registro_lote_transformacion.py  MODIFY
```

### Frontend — nuevos/modificados
```
frontend/src/components/jefe-planta/JefePlantaDashboard.tsx          MODIFY
frontend/src/components/jefe-area/JefeAreaDashboard.tsx              MODIFY
frontend/src/components/jefe-area/ManageMaquinas.tsx                 CREATE
frontend/src/components/jefe-area/ComponenteMezclaPanel.tsx          CREATE
frontend/src/components/operario/OperarioDashboard.tsx               MODIFY
frontend/src/components/admin-sistemas/ManageProductos.tsx           MODIFY
frontend/src/components/admin-sistemas/ManageBodegas.tsx             MODIFY
frontend/src/types/produccion.ts                                     CREATE
```

---

## SP-1: Modelos y Migraciones

### Task 1: Factories nuevas (antes que cualquier test)

**Files:**
- Modify: `gestion/tests/factories.py`

- [ ] **1.1 Agregar MaquinaConMermaFactory, ComponenteMezclaOPFactory, ConsumoLoteDetalleFactory**

Abrir `gestion/tests/factories.py` y agregar al final (después de las factories existentes):

```python
class MaquinaFactory(DjangoModelFactory):
    class Meta:
        model = Maquina

    nombre = factory.Sequence(lambda n: f'Maquina-{n}')
    capacidad_maxima = Decimal('500.00')
    eficiencia_ideal = Decimal('0.85')
    estado = 'operativa'
    area = factory.SubFactory(AreaFactory)


class MaquinaConMermaFactory(MaquinaFactory):
    producto_merma = factory.SubFactory(ProductoFactory,
                                        tipo='merma',
                                        codigo=factory.Sequence(lambda n: f'MERMA-{n:04d}'))
    bodega_merma = factory.SubFactory(BodegaFactory)


class OrdenProduccionFactory(DjangoModelFactory):
    class Meta:
        model = OrdenProduccion

    codigo = factory.Sequence(lambda n: f'OP-{n:04d}')
    producto_entrada = factory.SubFactory(ProductoFactory)
    producto_salida = factory.SubFactory(ProductoFactory,
                                         codigo=factory.Sequence(lambda n: f'OUT-{n:04d}'))
    bodega_entrada = factory.SubFactory(BodegaFactory)
    bodega_salida = factory.SubFactory(BodegaFactory)
    peso_neto_requerido = Decimal('100.00')
    estado = 'pendiente'
    prioridad = 'normal'
    sede = factory.SubFactory(SedeFactory)
    area = factory.SubFactory(AreaFactory)


class ComponenteMezclaOPFactory(DjangoModelFactory):
    class Meta:
        model = ComponenteMezclaOP

    orden = factory.SubFactory(OrdenProduccionFactory)
    producto = factory.SubFactory(ProductoFactory)
    bodega = factory.SubFactory(BodegaFactory)
    porcentaje = Decimal('50.00')
    cantidad_kg = Decimal('50.000')


class LoteProduccionFactory(DjangoModelFactory):
    class Meta:
        model = LoteProduccion

    orden_produccion = factory.SubFactory(OrdenProduccionFactory)
    codigo_lote = factory.Sequence(lambda n: f'OP-TEST-L{n}')
    peso_neto_producido = Decimal('95.000')
    peso_merma = Decimal('5.000')
    tipo_merma = 'maquina'
    maquina = factory.SubFactory(MaquinaFactory)
    turno = 'Dia'
    hora_inicio = factory.LazyFunction(lambda: datetime(2026, 1, 1, 8, 0))
    hora_final = factory.LazyFunction(lambda: datetime(2026, 1, 1, 16, 0))
    unidades_empaque = 1
    presentacion = 'cono'


class ConsumoLoteDetalleFactory(DjangoModelFactory):
    class Meta:
        model = ConsumoLoteDetalle

    lote_produccion = factory.SubFactory(LoteProduccionFactory)
    lote_origen = factory.SubFactory(LoteProduccionFactory)
    cantidad_consumida = Decimal('50.000')
    genera_nuevo_lote = True
```

Agregar el import `from datetime import datetime` al inicio si no existe, y `from decimal import Decimal`.

- [ ] **1.2 Commit factories**
```bash
git add gestion/tests/factories.py
git commit -m "test: agregar factories para mezcla, merma y transformacion"
```

---

### Task 2: Modificar modelos — OrdenProduccion y Maquina

**Files:**
- Modify: `gestion/models.py`

- [ ] **2.1 Escribir test de modelo que verifica campos nuevos**

Crear `gestion/tests/test_modelos_transformacion.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from gestion.tests.factories import (
    OrdenProduccionFactory, ComponenteMezclaOPFactory,
    MaquinaConMermaFactory, BodegaFactory, ProductoFactory
)


class OrdenProduccionTransformacionTest(TestCase):
    """EP: OrdenProduccion con producto_entrada y producto_salida distintos."""

    def test_op_tiene_producto_entrada_y_salida_distintos(self):
        op = OrdenProduccionFactory()
        self.assertIsNotNone(op.producto_entrada)
        self.assertIsNotNone(op.producto_salida)
        self.assertNotEqual(op.producto_entrada, op.producto_salida)

    def test_op_tiene_bodega_entrada_y_salida(self):
        op = OrdenProduccionFactory()
        self.assertIsNotNone(op.bodega_entrada)
        self.assertIsNotNone(op.bodega_salida)


class ComponenteMezclaOPTest(TestCase):
    """COBIT DSS06: sum(porcentaje) == 100 validado en modelo."""

    def test_componentes_mezcla_vinculados_a_op(self):
        op = OrdenProduccionFactory()
        c1 = ComponenteMezclaOPFactory(orden=op, porcentaje=Decimal('50.00'))
        c2 = ComponenteMezclaOPFactory(orden=op, porcentaje=Decimal('50.00'))
        self.assertEqual(op.componentes_mezcla.count(), 2)

    def test_cantidad_kg_calculada_correctamente(self):
        """BVA: cantidad_kg = (porcentaje / 100) * peso_neto_requerido."""
        op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        comp = ComponenteMezclaOPFactory(orden=op, porcentaje=Decimal('50.00'),
                                          cantidad_kg=Decimal('50.000'))
        self.assertEqual(comp.cantidad_kg, Decimal('50.000'))


class MaquinaConMermaTest(TestCase):
    """EP: Maquina con producto_merma y bodega_merma configurados."""

    def test_maquina_tiene_producto_merma(self):
        maquina = MaquinaConMermaFactory()
        self.assertIsNotNone(maquina.producto_merma)
        self.assertIsNotNone(maquina.bodega_merma)

    def test_maquina_sin_merma_es_valida(self):
        from gestion.tests.factories import MaquinaFactory
        maquina = MaquinaFactory()
        self.assertIsNone(maquina.producto_merma)
        self.assertIsNone(maquina.bodega_merma)
```

- [ ] **2.2 Ejecutar tests — deben fallar (RED)**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_modelos_transformacion -v 2
```
Esperado: `ImportError` o `AttributeError` — los campos no existen aún.

- [ ] **2.3 Modificar `gestion/models.py` — OrdenProduccion**

Localizar la clase `OrdenProduccion` (línea ~594). Cambiar:
```python
# ANTES:
producto = models.ForeignKey(
    'Producto', on_delete=models.PROTECT, db_index=True,
    verbose_name='Producto'
)
bodega = models.ForeignKey(
    'Bodega', on_delete=models.PROTECT,
    verbose_name='Bodega de Materia Prima'
)

# DESPUÉS:
producto_entrada = models.ForeignKey(
    'Producto', on_delete=models.PROTECT, db_index=True,
    related_name='ordenes_como_entrada',
    verbose_name='Producto de Entrada'
)
producto_salida = models.ForeignKey(
    'Producto', on_delete=models.PROTECT, db_index=True,
    related_name='ordenes_como_salida',
    null=True, blank=True,  # nullable durante migración, se hace required en 0067
    verbose_name='Producto de Salida'
)
bodega_entrada = models.ForeignKey(
    'Bodega', on_delete=models.PROTECT,
    related_name='ordenes_entrada',
    verbose_name='Bodega de Entrada (MP)'
)
bodega_salida = models.ForeignKey(
    'Bodega', on_delete=models.PROTECT,
    related_name='ordenes_salida',
    null=True, blank=True,  # nullable durante migración
    verbose_name='Bodega de Salida (PT)'
)
```

También actualizar `campos_auditables` en `OrdenProduccion`:
```python
campos_auditables = [
    'codigo', 'producto_entrada', 'producto_salida',
    'peso_neto_requerido', 'estado', 'maquina_asignada',
    'operario_asignado', 'prioridad', 'bodega_entrada', 'bodega_salida'
]
```

- [ ] **2.4 Agregar campos merma a `Maquina` en `gestion/models.py`**

Localizar clase `Maquina` (línea ~335). Agregar después del campo `operarios`:
```python
producto_merma = models.ForeignKey(
    'Producto', on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='maquinas_generadoras',
    verbose_name='Producto de Merma'
)
bodega_merma = models.ForeignKey(
    'Bodega', on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='maquinas_merma',
    verbose_name='Bodega de Merma'
)
```

- [ ] **2.5 Agregar modelos `ComponenteMezclaOP` y `ConsumoLoteDetalle` en `gestion/models.py`**

Agregar después de la clase `LoteProduccion`:

```python
class ComponenteMezclaOP(AuditableModelMixin, models.Model):
    """
    Receta de mezcla definida por Jefe de Área para una OP.
    COBIT DSS06: sum(porcentaje) == 100 validado en serializer y service.
    ISO 27001 A.12.4: auditoría automática vía AuditableModelMixin.
    """
    campos_auditables = ['porcentaje', 'cantidad_kg', 'producto', 'bodega']

    orden = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='componentes_mezcla',
        verbose_name='Orden de Producción'
    )
    producto = models.ForeignKey(
        'Producto', on_delete=models.PROTECT,
        verbose_name='Producto Componente'
    )
    bodega = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        verbose_name='Bodega Origen del Componente'
    )
    porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Porcentaje (%)'
    )
    cantidad_kg = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad calculada (kg)'
    )

    class Meta:
        verbose_name = 'Componente de Mezcla'
        unique_together = [('orden', 'producto')]
        constraints = [
            models.CheckConstraint(
                check=models.Q(porcentaje__gt=0) & models.Q(porcentaje__lte=100),
                name='componente_porcentaje_rango'
            )
        ]

    def __str__(self):
        return f'{self.orden.codigo} — {self.producto.codigo} ({self.porcentaje}%)'


class ConsumoLoteDetalle(AuditableModelMixin, models.Model):
    """
    Registro inmutable del consumo real de lotes de entrada al producir un lote.
    ISO 27001 A.12.4: NO permite UPDATE. Solo DELETE vía endpoint rechazar/ con justificación.
    """
    campos_auditables = ['cantidad_consumida']

    lote_produccion = models.ForeignKey(
        LoteProduccion, on_delete=models.CASCADE,
        related_name='consumos_detalle',
        verbose_name='Lote Producido (output)'
    )
    lote_origen = models.ForeignKey(
        LoteProduccion, on_delete=models.PROTECT,
        related_name='usos_como_input',
        verbose_name='Lote de Origen (input)'
    )
    cantidad_consumida = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad Consumida (kg)'
    )
    genera_nuevo_lote = models.BooleanField(
        default=True,
        verbose_name='¿Genera nuevo código de lote?'
    )

    class Meta:
        verbose_name = 'Detalle de Consumo de Lote'
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_consumida__gt=0),
                name='consumo_cantidad_positiva'
            )
        ]

    def __str__(self):
        return f'{self.lote_produccion.codigo_lote} ← {self.lote_origen.codigo_lote} ({self.cantidad_consumida} kg)'
```

- [ ] **2.6 Ejecutar tests — deben pasar (GREEN)**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_modelos_transformacion -v 2
```
Esperado: `OK` — pero primero hay que crear las migraciones (Task 3).

---

### Task 3: Migraciones

**Files:**
- Create: `gestion/migrations/0060_rename_producto_to_producto_entrada.py`
- Create: `gestion/migrations/0061_rename_bodega_to_bodega_entrada.py`
- Create: `gestion/migrations/0062_add_producto_salida_bodega_salida.py`
- Create: `gestion/migrations/0063_componente_mezcla_op.py`
- Create: `gestion/migrations/0064_consumo_lote_detalle.py`
- Create: `gestion/migrations/0065_maquina_merma_fields.py`
- Create: `gestion/migrations/0066_backfill_producto_salida.py`
- Create: `gestion/migrations/0067_make_producto_salida_required.py`

- [ ] **3.1 Generar migraciones de renombrado**
```bash
docker exec texcore-backend-1 python manage.py makemigrations gestion --name rename_producto_bodega_to_entrada
```
Django detectará RenameField automáticamente. Verificar que el archivo generado contenga `RenameField` (no DeleteField+AddField).

- [ ] **3.2 Generar migraciones de campos nuevos y modelos**
```bash
docker exec texcore-backend-1 python manage.py makemigrations gestion --name add_transformacion_models
```

- [ ] **3.3 Crear migración de backfill manualmente**

Crear `gestion/migrations/0066_backfill_producto_salida.py`:
```python
from django.db import migrations


def backfill_producto_salida(apps, schema_editor):
    """Copia producto_entrada → producto_salida para registros existentes."""
    OrdenProduccion = apps.get_model('gestion', 'OrdenProduccion')
    updated = OrdenProduccion.objects.filter(
        producto_salida__isnull=True
    ).update(
        producto_salida=models.F('producto_entrada'),
        bodega_salida=models.F('bodega_entrada')
    )
    print(f'Backfill: {updated} OPs actualizadas.')


class Migration(migrations.Migration):
    dependencies = [
        ('gestion', '0065_maquina_merma_fields'),  # ajustar número real generado
    ]

    operations = [
        migrations.RunPython(backfill_producto_salida, migrations.RunPython.noop),
    ]
```

- [ ] **3.4 Generar migración final que hace required los campos**
```bash
docker exec texcore-backend-1 python manage.py makemigrations gestion --name make_producto_salida_required
```
Editar el archivo generado para asegurar que depende de `0066_backfill`.

- [ ] **3.5 Aplicar todas las migraciones**
```bash
docker exec texcore-backend-1 python manage.py migrate gestion
```
Esperado: todas las migraciones aplicadas sin error.

- [ ] **3.6 Verificar en shell que los campos existen**
```bash
docker exec texcore-backend-1 python manage.py shell -c "
from gestion.models import OrdenProduccion, ComponenteMezclaOP, ConsumoLoteDetalle, Maquina
print('producto_entrada:', OrdenProduccion._meta.get_field('producto_entrada'))
print('producto_salida:', OrdenProduccion._meta.get_field('producto_salida'))
print('bodega_salida:', OrdenProduccion._meta.get_field('bodega_salida'))
print('ComponenteMezclaOP:', ComponenteMezclaOP._meta.db_table)
print('ConsumoLoteDetalle:', ConsumoLoteDetalle._meta.db_table)
print('producto_merma en Maquina:', Maquina._meta.get_field('producto_merma'))
"
```

- [ ] **3.7 Ejecutar tests de modelo y confirmar GREEN**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_modelos_transformacion -v 2
```
Esperado: `Ran 5 tests in X.XXXs — OK`

- [ ] **3.8 Commit**
```bash
git add gestion/models.py gestion/migrations/
git commit -m "feat: agregar producto_entrada/salida, ComponenteMezclaOP, ConsumoLoteDetalle, merma en Maquina"
```

---

## SP-2: Service Layer

### Task 4: MermaStockService (TDD)

**Files:**
- Create: `gestion/services/merma_stock.py`
- Create: `gestion/tests/test_merma_stock_service.py`

- [ ] **4.1 Escribir tests (RED)**

Crear `gestion/tests/test_merma_stock_service.py`:

```python
from decimal import Decimal
from django.test import TestCase
from inventory.models import StockBodega, MovimientoInventario
from gestion.tests.factories import (
    MaquinaConMermaFactory, MaquinaFactory,
    LoteProduccionFactory, CustomUserFactory
)


class MermaStockServiceTest(TestCase):
    """TDD — MermaStockService. ISO 27001 A.12.4 + COBIT MEA01."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.maquina = MaquinaConMermaFactory()
        self.lote = LoteProduccionFactory(
            maquina=self.maquina,
            peso_merma=Decimal('5.000'),
            tipo_merma='maquina'
        )

    # EP: máquina con merma configurada y peso_merma > 0
    def test_dado_maquina_con_merma_cuando_registrar_entonces_crea_stock_merma(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)

        stock = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma,
            lote=self.lote
        )
        self.assertEqual(stock.cantidad, Decimal('5.00'))

    # EP: máquina sin merma configurada — no crea nada
    def test_dado_maquina_sin_merma_cuando_registrar_entonces_no_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        maquina_simple = MaquinaFactory()
        lote = LoteProduccionFactory(maquina=maquina_simple, peso_merma=Decimal('3.000'))
        MermaStockService.registrar(lote, self.user)

        self.assertFalse(
            StockBodega.objects.filter(producto=None).exists()
        )
        # No se creó ningún movimiento de merma vendible
        self.assertEqual(
            MovimientoInventario.objects.filter(documento_ref__startswith='MERMA-').count(), 0
        )

    # BVA: peso_merma = 0 — no crea stock
    def test_dado_peso_merma_cero_cuando_registrar_entonces_no_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        lote = LoteProduccionFactory(maquina=self.maquina, peso_merma=Decimal('0.000'))
        MermaStockService.registrar(lote, self.user)
        self.assertFalse(
            StockBodega.objects.filter(bodega=self.maquina.bodega_merma).exists()
        )

    # BVA: peso_merma = 0.01 — crea stock
    def test_dado_peso_merma_minimo_cuando_registrar_entonces_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        lote = LoteProduccionFactory(maquina=self.maquina, peso_merma=Decimal('0.010'))
        MermaStockService.registrar(lote, self.user)
        self.assertTrue(
            StockBodega.objects.filter(bodega=self.maquina.bodega_merma).exists()
        )

    # ISO 27001 A.12.4: crea MovimientoInventario con documento_ref MERMA-
    def test_cuando_registrar_merma_entonces_crea_movimiento_con_ref_merma(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)
        mov = MovimientoInventario.objects.get(
            documento_ref=f'MERMA-{self.lote.codigo_lote}'
        )
        self.assertEqual(mov.tipo_movimiento, 'PRODUCCION')
        self.assertEqual(mov.cantidad, Decimal('5.00'))
        self.assertEqual(mov.usuario, self.user)

    # STT: merma registrada → lote rechazado → stock revertido
    def test_dado_merma_registrada_cuando_revertir_entonces_stock_decrece(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)
        stock_antes = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma
        ).cantidad

        MermaStockService.revertir(self.lote, self.user, 'Test reversión')

        stock_despues = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma
        ).cantidad
        self.assertEqual(stock_despues, stock_antes - Decimal('5.00'))
```

- [ ] **4.2 Ejecutar tests — RED**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_merma_stock_service -v 2
```
Esperado: `ImportError: cannot import name 'MermaStockService'`

- [ ] **4.3 Implementar `gestion/services/merma_stock.py`**

```python
import logging
from decimal import Decimal
from django.db import transaction
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


class MermaStockService:
    """
    SRP: gestiona el stock de merma vendible por máquina.
    ISO 27001 A.12.4: cada operación crea MovimientoInventario trazable.
    COBIT MEA01: documento_ref 'MERMA-{codigo}' para KPIs de eficiencia.
    """

    @staticmethod
    @transaction.atomic
    def registrar(lote, user) -> None:
        """
        Si la máquina del lote tiene producto_merma configurado y
        peso_merma > 0, crea stock vendible en bodega_merma.
        """
        maquina = lote.maquina
        if not maquina or not maquina.producto_merma or not maquina.bodega_merma:
            return

        peso_merma = lote.peso_merma.quantize(Decimal('0.01'))
        if peso_merma <= 0:
            return

        stock, _ = safe_get_or_create_stock(
            maquina.bodega_merma, maquina.producto_merma, lote=lote
        )
        stock.cantidad += peso_merma
        stock._justificacion_auditoria = f'Merma vendible de lote {lote.codigo_lote}'
        stock.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=maquina.producto_merma,
            lote=lote,
            bodega_destino=maquina.bodega_merma,
            cantidad=peso_merma,
            documento_ref=f'MERMA-{lote.codigo_lote}',
            usuario=user,
            saldo_resultante=stock.cantidad,
        )

        logger.info(
            'Merma vendible registrada',
            extra={'sd': {
                'lote': lote.codigo_lote,
                'producto_merma': maquina.producto_merma.codigo,
                'cantidad_kg': str(peso_merma),
                'bodega': maquina.bodega_merma.nombre,
            }}
        )

    @staticmethod
    @transaction.atomic
    def revertir(lote, user, justificacion: str) -> None:
        """Revierte el stock de merma creado por este lote."""
        maquina = lote.maquina
        if not maquina or not maquina.producto_merma:
            return

        peso_merma = lote.peso_merma.quantize(Decimal('0.01'))
        if peso_merma <= 0:
            return

        try:
            stock = StockBodega.objects.select_for_update().get(
                bodega=maquina.bodega_merma,
                producto=maquina.producto_merma,
                lote=lote
            )
        except StockBodega.DoesNotExist:
            return

        stock.cantidad -= peso_merma
        stock._justificacion_auditoria = justificacion
        stock.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION',
            producto=maquina.producto_merma,
            lote=lote,
            bodega_origen=maquina.bodega_merma,
            cantidad=peso_merma,
            documento_ref=f'REV-MERMA-{lote.codigo_lote}',
            usuario=user,
            saldo_resultante=stock.cantidad,
            observaciones=justificacion,
        )
```

- [ ] **4.4 Ejecutar tests — GREEN**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_merma_stock_service -v 2
```
Esperado: `Ran 6 tests in X.XXXs — OK`

- [ ] **4.5 Commit**
```bash
git add gestion/services/merma_stock.py gestion/tests/test_merma_stock_service.py
git commit -m "feat: MermaStockService — merma vendible por maquina con trazabilidad"
```

---

### Task 5: ConsumoMezclaService (TDD)

**Files:**
- Create: `gestion/services/consumo_mezcla.py`
- Create: `gestion/tests/test_consumo_mezcla_service.py`

- [ ] **5.1 Escribir tests (RED)**

Crear `gestion/tests/test_consumo_mezcla_service.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from inventory.models import StockBodega, MovimientoInventario
from gestion.models import ConsumoLoteDetalle
from gestion.tests.factories import (
    OrdenProduccionFactory, ComponenteMezclaOPFactory,
    LoteProduccionFactory, CustomUserFactory, StockBodegaFactory
)


class ConsumoMezclaServiceTest(TestCase):
    """TDD — ConsumoMezclaService. COBIT DSS06 + ISO 27001 A.12.4."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        self.comp1 = ComponenteMezclaOPFactory(
            orden=self.op, porcentaje=Decimal('50.00'), cantidad_kg=Decimal('50.000')
        )
        self.comp2 = ComponenteMezclaOPFactory(
            orden=self.op, porcentaje=Decimal('50.00'), cantidad_kg=Decimal('50.000')
        )
        # Lotes de origen con stock disponible
        self.lote_origen1 = LoteProduccionFactory(
            peso_neto_producido=Decimal('100.000')
        )
        self.lote_origen2 = LoteProduccionFactory(
            peso_neto_producido=Decimal('100.000')
        )
        # Stock para cada lote origen
        StockBodegaFactory(
            bodega=self.comp1.bodega,
            producto=self.comp1.producto,
            lote=self.lote_origen1,
            cantidad=Decimal('100.00')
        )
        StockBodegaFactory(
            bodega=self.comp2.bodega,
            producto=self.comp2.producto,
            lote=self.lote_origen2,
            cantidad=Decimal('100.00')
        )
        self.lote_output = LoteProduccionFactory(orden_produccion=self.op)

    # EP: mezcla válida 2 componentes
    def test_dado_mezcla_valida_cuando_consumir_entonces_descuenta_ambos_stocks(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {'lote_origen_id': self.lote_origen1.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
            {'lote_origen_id': self.lote_origen2.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
        ]
        ConsumoMezclaService.consumir(self.op, self.lote_output, consumos, self.user)

        stock1 = StockBodega.objects.get(bodega=self.comp1.bodega, producto=self.comp1.producto, lote=self.lote_origen1)
        stock2 = StockBodega.objects.get(bodega=self.comp2.bodega, producto=self.comp2.producto, lote=self.lote_origen2)
        self.assertEqual(stock1.cantidad, Decimal('50.00'))
        self.assertEqual(stock2.cantidad, Decimal('50.00'))

    # EP: genera ConsumoLoteDetalle por cada componente
    def test_cuando_consumir_mezcla_entonces_crea_consumo_lote_detalle(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {'lote_origen_id': self.lote_origen1.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
            {'lote_origen_id': self.lote_origen2.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
        ]
        ConsumoMezclaService.consumir(self.op, self.lote_output, consumos, self.user)
        self.assertEqual(ConsumoLoteDetalle.objects.filter(lote_produccion=self.lote_output).count(), 2)

    # BVA: suma cantidades != consumo_total → ValidationError (COBIT DSS06)
    def test_dado_suma_incorrecta_cuando_consumir_entonces_lanza_error(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {'lote_origen_id': self.lote_origen1.id, 'cantidad_kg': Decimal('40.000'), 'genera_nuevo_lote': True},
            {'lote_origen_id': self.lote_origen2.id, 'cantidad_kg': Decimal('40.000'), 'genera_nuevo_lote': True},
        ]
        with self.assertRaises(ValidationError):
            ConsumoMezclaService.consumir(
                self.op, self.lote_output, consumos, self.user,
                consumo_total=Decimal('100.000')
            )

    # EP: stock insuficiente → ValidationError + rollback
    def test_dado_stock_insuficiente_cuando_consumir_entonces_rollback(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {'lote_origen_id': self.lote_origen1.id, 'cantidad_kg': Decimal('200.000'), 'genera_nuevo_lote': True},
        ]
        with self.assertRaises(ValidationError):
            ConsumoMezclaService.consumir(self.op, self.lote_output, consumos, self.user)

        # Verificar rollback: stock no cambió
        stock = StockBodega.objects.get(bodega=self.comp1.bodega, producto=self.comp1.producto, lote=self.lote_origen1)
        self.assertEqual(stock.cantidad, Decimal('100.00'))

    # ISO 27001 A.12.4: crea MovimientoInventario por cada componente
    def test_cuando_consumir_entonces_crea_movimientos_kardex(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {'lote_origen_id': self.lote_origen1.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
            {'lote_origen_id': self.lote_origen2.id, 'cantidad_kg': Decimal('50.000'), 'genera_nuevo_lote': True},
        ]
        ConsumoMezclaService.consumir(self.op, self.lote_output, consumos, self.user)
        movs = MovimientoInventario.objects.filter(
            tipo_movimiento='CONSUMO',
            documento_ref=f'OP-{self.op.codigo}'
        )
        self.assertEqual(movs.count(), 2)
```

- [ ] **5.2 Agregar StockBodegaFactory a factories.py**

En `gestion/tests/factories.py` agregar:
```python
class StockBodegaFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.StockBodega'

    bodega = factory.SubFactory(BodegaFactory)
    producto = factory.SubFactory(ProductoFactory)
    lote = None
    cantidad = Decimal('100.00')
```

- [ ] **5.3 Ejecutar tests — RED**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_consumo_mezcla_service -v 2
```
Esperado: `ImportError: cannot import name 'ConsumoMezclaService'`

- [ ] **5.4 Implementar `gestion/services/consumo_mezcla.py`**

```python
import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import MovimientoInventario, StockBodega
from gestion.models import ConsumoLoteDetalle, LoteProduccion

logger = logging.getLogger(__name__)

TOLERANCIA_KG = Decimal('0.01')


class ConsumoMezclaService:
    """
    SRP: gestiona el consumo de múltiples lotes de entrada para producir un lote de salida.
    COBIT DSS06: valida integridad de suma de componentes.
    ISO 27001 A.12.4: ConsumoLoteDetalle es inmutable post-creación.
    """

    @staticmethod
    @transaction.atomic
    def consumir(orden, lote_output, consumos_data: list, user,
                 consumo_total: Decimal = None) -> None:
        """
        consumos_data: list de dict {lote_origen_id, cantidad_kg, genera_nuevo_lote}
        consumo_total: si se provee, valida que sum(cantidad_kg) == consumo_total ±TOLERANCIA
        """
        suma = sum(Decimal(str(c['cantidad_kg'])) for c in consumos_data)

        if consumo_total is not None:
            diferencia = abs(suma - consumo_total)
            if diferencia > TOLERANCIA_KG:
                raise ValidationError(
                    f'La suma de cantidades ({suma} kg) no coincide con el consumo '
                    f'total esperado ({consumo_total} kg). Diferencia: {diferencia} kg.'
                )

        for consumo in consumos_data:
            lote_origen = LoteProduccion.objects.select_for_update().get(
                id=consumo['lote_origen_id']
            )
            cantidad = Decimal(str(consumo['cantidad_kg'])).quantize(Decimal('0.001'))

            # Determinar bodega y producto del origen desde ComponenteMezclaOP
            componente = orden.componentes_mezcla.filter(
                producto=lote_origen.orden_produccion.producto_salida
            ).first()

            if componente:
                bodega_origen = componente.bodega
                producto_origen = componente.producto
            else:
                # Fallback: tomar de la OP del lote origen
                bodega_origen = lote_origen.orden_produccion.bodega_salida
                producto_origen = lote_origen.orden_produccion.producto_salida

            stock = StockBodega.objects.select_for_update().get(
                bodega=bodega_origen,
                producto=producto_origen,
                lote=lote_origen
            )

            if stock.cantidad < cantidad:
                raise ValidationError(
                    f'Stock insuficiente para lote {lote_origen.codigo_lote}. '
                    f'Disponible: {stock.cantidad} kg. Requerido: {cantidad} kg.'
                )

            stock.cantidad -= cantidad
            stock._justificacion_auditoria = f'Consumo en mezcla OP-{orden.codigo}'
            stock.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='CONSUMO',
                producto=producto_origen,
                lote=lote_origen,
                bodega_origen=bodega_origen,
                cantidad=cantidad,
                documento_ref=f'OP-{orden.codigo}',
                usuario=user,
                saldo_resultante=stock.cantidad,
            )

            ConsumoLoteDetalle.objects.create(
                lote_produccion=lote_output,
                lote_origen=lote_origen,
                cantidad_consumida=cantidad,
                genera_nuevo_lote=consumo.get('genera_nuevo_lote', True),
            )

        logger.info(
            'Mezcla de lotes consumida',
            extra={'sd': {
                'op': orden.codigo,
                'lote_output': lote_output.codigo_lote,
                'componentes': len(consumos_data),
                'total_kg': str(suma),
            }}
        )

    @staticmethod
    @transaction.atomic
    def revertir(lote_output, user, justificacion: str) -> None:
        """Revierte todos los ConsumoLoteDetalle de un lote_output."""
        consumos = ConsumoLoteDetalle.objects.filter(
            lote_produccion=lote_output
        ).select_related('lote_origen')

        for consumo in consumos:
            lote_origen = consumo.lote_origen
            componente = lote_output.orden_produccion.componentes_mezcla.filter(
                producto=lote_origen.orden_produccion.producto_salida
            ).first()

            if componente:
                bodega = componente.bodega
                producto = componente.producto
            else:
                bodega = lote_origen.orden_produccion.bodega_salida
                producto = lote_origen.orden_produccion.producto_salida

            stock = StockBodega.objects.select_for_update().get(
                bodega=bodega, producto=producto, lote=lote_origen
            )
            cantidad = consumo.cantidad_consumida.quantize(Decimal('0.01'))
            stock.cantidad += cantidad
            stock._justificacion_auditoria = justificacion
            stock.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='DEVOLUCION',
                producto=producto,
                lote=lote_origen,
                bodega_destino=bodega,
                cantidad=cantidad,
                documento_ref=f'REV-{lote_output.codigo_lote}',
                usuario=user,
                saldo_resultante=stock.cantidad,
                observaciones=justificacion,
            )

        consumos.delete()
```

- [ ] **5.5 Ejecutar tests — GREEN**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_consumo_mezcla_service -v 2
```
Esperado: `Ran 5 tests in X.XXXs — OK`

- [ ] **5.6 Commit**
```bash
git add gestion/services/consumo_mezcla.py gestion/tests/test_consumo_mezcla_service.py gestion/tests/factories.py
git commit -m "feat: ConsumoMezclaService — consumo atomico de mezcla de lotes con trazabilidad"
```

---

### Task 6: Actualizar RegistroLoteService

**Files:**
- Modify: `gestion/services/registro_lote.py`
- Modify: `gestion/tests/test_registro_lote_transformacion.py`

- [ ] **6.1 Escribir tests nuevos (RED)**

Crear `gestion/tests/test_registro_lote_transformacion.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from inventory.models import StockBodega, MovimientoInventario
from gestion.tests.factories import (
    OrdenProduccionFactory, ComponenteMezclaOPFactory,
    MaquinaConMermaFactory, LoteProduccionFactory,
    CustomUserFactory, StockBodegaFactory
)


class RegistroLoteTransformacionTest(TestCase):
    """TDD — RegistroLoteService con producto_entrada != producto_salida."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        # Stock de entrada disponible
        StockBodegaFactory(
            bodega=self.op.bodega_entrada,
            producto=self.op.producto_entrada,
            lote=None,
            cantidad=Decimal('200.00')
        )

    # EP: OP simple sin mezcla — consume producto_entrada, produce producto_salida
    def test_dado_op_simple_cuando_registrar_lote_entonces_transforma_productos(self):
        from gestion.services.registro_lote import RegistroLoteService
        lote_data = {
            'peso_neto_producido': Decimal('90.000'),
            'peso_merma': Decimal('10.000'),
            'tipo_merma': 'maquina',
            'unidades_empaque': 1,
            'presentacion': 'cono',
            'turno': 'Dia',
        }
        lote = RegistroLoteService.registrar_lote(self.op, lote_data, self.user)

        # Verifica consumo de producto_entrada
        stock_entrada = StockBodega.objects.get(
            bodega=self.op.bodega_entrada, producto=self.op.producto_entrada, lote=None
        )
        self.assertEqual(stock_entrada.cantidad, Decimal('100.00'))  # 200 - 100

        # Verifica producción de producto_salida en bodega_salida
        stock_salida = StockBodega.objects.get(
            bodega=self.op.bodega_salida, producto=self.op.producto_salida, lote=lote
        )
        self.assertEqual(stock_salida.cantidad, Decimal('90.00'))

    # EP: OP con mezcla — delega a ConsumoMezclaService
    def test_dado_op_con_mezcla_cuando_registrar_entonces_crea_consumo_detalle(self):
        from gestion.services.registro_lote import RegistroLoteService
        from gestion.models import ConsumoLoteDetalle
        lote_origen1 = LoteProduccionFactory()
        StockBodegaFactory(
            bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
            lote=lote_origen1, cantidad=Decimal('50.00')
        )
        lote_data = {
            'peso_neto_producido': Decimal('45.000'),
            'peso_merma': Decimal('5.000'),
            'tipo_merma': 'material',
            'unidades_empaque': 1,
            'presentacion': 'cono',
            'turno': 'Dia',
            'consumos': [
                {'lote_origen_id': lote_origen1.id, 'cantidad_kg': Decimal('50.000'),
                 'genera_nuevo_lote': True}
            ]
        }
        lote = RegistroLoteService.registrar_lote(self.op, lote_data, self.user)
        self.assertEqual(ConsumoLoteDetalle.objects.filter(lote_produccion=lote).count(), 1)

    # EP: merma vendible — MermaStockService crea stock
    def test_dado_maquina_con_merma_cuando_registrar_entonces_crea_stock_merma(self):
        from gestion.services.registro_lote import RegistroLoteService
        maquina = MaquinaConMermaFactory()
        lote_data = {
            'peso_neto_producido': Decimal('90.000'),
            'peso_merma': Decimal('10.000'),
            'tipo_merma': 'maquina',
            'maquina': maquina.id,
            'unidades_empaque': 1,
            'presentacion': 'cono',
            'turno': 'Dia',
        }
        lote = RegistroLoteService.registrar_lote(self.op, lote_data, self.user)
        self.assertTrue(
            StockBodega.objects.filter(
                bodega=maquina.bodega_merma,
                producto=maquina.producto_merma,
                lote=lote
            ).exists()
        )

    # STT: OP pendiente → en_proceso → finalizada
    def test_estado_op_transicion_correcta(self):
        from gestion.services.registro_lote import RegistroLoteService
        self.assertEqual(self.op.estado, 'pendiente')
        lote_data = {
            'peso_neto_producido': Decimal('90.000'),
            'peso_merma': Decimal('5.000'),
            'tipo_merma': 'corte',
            'unidades_empaque': 1, 'presentacion': 'cono', 'turno': 'Dia',
        }
        RegistroLoteService.registrar_lote(self.op, lote_data, self.user)
        self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'en_proceso')

        lote_data2 = {
            'peso_neto_producido': Decimal('10.000'),
            'peso_merma': Decimal('0.000'),
            'tipo_merma': 'maquina',
            'unidades_empaque': 1, 'presentacion': 'cono', 'turno': 'Noche',
        }
        RegistroLoteService.registrar_lote(self.op, lote_data2, self.user)
        self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'finalizada')
```

- [ ] **6.2 Ejecutar tests — RED**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_registro_lote_transformacion -v 2
```

- [ ] **6.3 Modificar `gestion/services/registro_lote.py`**

Reemplazar el método `registrar_lote` para usar los nuevos campos y servicios:

```python
import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock
from gestion.services.consumo_mezcla import ConsumoMezclaService
from gestion.services.merma_stock import MermaStockService

logger = logging.getLogger(__name__)


class RegistroLoteService:
    """
    Orquesta el registro de un lote de producción.
    Delega consumo de mezcla a ConsumoMezclaService (SRP).
    Delega merma vendible a MermaStockService (SRP).
    """

    @staticmethod
    @transaction.atomic
    def registrar_lote(orden, lote_data: dict, user, completar_orden: bool = False):
        from gestion.models import LoteProduccion, Maquina

        peso_neto = Decimal(str(lote_data['peso_neto_producido'])).quantize(Decimal('0.01'))
        peso_merma = Decimal(str(lote_data.get('peso_merma', 0))).quantize(Decimal('0.01'))
        consumo_total = peso_neto + peso_merma

        # Validaciones de OP
        if not orden.producto_entrada_id or not orden.bodega_entrada_id:
            raise ValidationError('La OP debe tener producto_entrada y bodega_entrada.')
        if not orden.producto_salida_id or not orden.bodega_salida_id:
            raise ValidationError('La OP debe tener producto_salida y bodega_salida.')

        # Código de lote
        codigo_lote = lote_data.get('codigo_lote') or orden.generate_next_lote_codigo()

        consumos_mezcla = lote_data.get('consumos')
        tiene_mezcla = orden.componentes_mezcla.exists() and consumos_mezcla

        if tiene_mezcla:
            # La mezcla gestiona su propio consumo de stock — se ejecuta después de crear el lote
            pass
        else:
            # Consumo simple de producto_entrada
            stock_entrada, _ = safe_get_or_create_stock(
                orden.bodega_entrada, orden.producto_entrada, lote=None
            )
            stock_entrada = StockBodega.objects.select_for_update().get(
                id=stock_entrada.id
            )
            if stock_entrada.cantidad < consumo_total:
                raise ValidationError(
                    f'Stock insuficiente en {orden.bodega_entrada.nombre}. '
                    f'Disponible: {stock_entrada.cantidad} kg. Requerido: {consumo_total} kg.'
                )
            stock_entrada.cantidad -= consumo_total
            stock_entrada._justificacion_auditoria = f'Consumo (y merma) automático OP-{orden.codigo}'
            stock_entrada.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='CONSUMO',
                producto=orden.producto_entrada,
                bodega_origen=orden.bodega_entrada,
                cantidad=peso_neto,
                documento_ref=f'OP-{orden.codigo}',
                usuario=user,
                saldo_resultante=stock_entrada.cantidad,
            )
            if peso_merma > 0:
                MovimientoInventario.objects.create(
                    tipo_movimiento='MERMA',
                    producto=orden.producto_entrada,
                    bodega_origen=orden.bodega_entrada,
                    cantidad=peso_merma,
                    documento_ref=f'MERMA-OP-{orden.codigo}',
                    usuario=user,
                    saldo_resultante=stock_entrada.cantidad,
                )

        # Resolver maquina
        maquina = None
        maquina_id = lote_data.get('maquina')
        if maquina_id:
            try:
                maquina = Maquina.objects.get(id=maquina_id)
            except Maquina.DoesNotExist:
                pass

        # Crear LoteProduccion
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            codigo_lote=codigo_lote,
            peso_neto_producido=peso_neto,
            peso_merma=peso_merma,
            tipo_merma=lote_data.get('tipo_merma', ''),
            clasificacion_calidad=lote_data.get('clasificacion_calidad', 'primera'),
            maquina=maquina,
            operario=lote_data.get('operario') or user,
            turno=lote_data.get('turno', ''),
            hora_inicio=lote_data.get('hora_inicio'),
            hora_final=lote_data.get('hora_final'),
            unidades_empaque=lote_data.get('unidades_empaque', 1),
            presentacion=lote_data.get('presentacion', 'cono'),
        )

        # Consumo de mezcla (después de crear lote para tener FK)
        if tiene_mezcla:
            ConsumoMezclaService.consumir(
                orden, lote, consumos_mezcla, user,
                consumo_total=consumo_total
            )

        # Merma vendible
        if maquina and peso_merma > 0:
            MermaStockService.registrar(lote, user)

        # Producción de producto_salida en bodega_salida
        stock_salida, _ = safe_get_or_create_stock(
            orden.bodega_salida, orden.producto_salida, lote=lote
        )
        stock_salida.cantidad += peso_neto
        stock_salida._justificacion_auditoria = f'Producción lote {codigo_lote}'
        stock_salida.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=orden.producto_salida,
            lote=lote,
            bodega_destino=orden.bodega_salida,
            cantidad=peso_neto,
            documento_ref=f'OP-{orden.codigo}',
            usuario=user,
            saldo_resultante=stock_salida.cantidad,
        )

        # Actualizar estado OP
        total_producido = sum(
            l.peso_neto_producido
            for l in orden.lotes.all()
        )
        if completar_orden or total_producido >= orden.peso_neto_requerido:
            orden.estado = 'finalizada'
        else:
            orden.estado = 'en_proceso'
        orden.save(update_fields=['estado'])

        logger.info('Lote registrado', extra={'sd': {
            'lote': codigo_lote,
            'op': orden.codigo,
            'producto_entrada': orden.producto_entrada.codigo,
            'producto_salida': orden.producto_salida.codigo,
            'peso_neto': str(peso_neto),
            'peso_merma': str(peso_merma),
        }})

        return lote
```

- [ ] **6.4 Ejecutar todos los tests de service**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests.test_registro_lote_transformacion gestion.tests.test_merma_stock_service gestion.tests.test_consumo_mezcla_service -v 2
```
Esperado: todos GREEN.

- [ ] **6.5 Ejecutar suite completa para detectar regresiones**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests -v 1
```
Esperado: misma cantidad de tests que antes + los nuevos, todos OK.

- [ ] **6.6 Commit**
```bash
git add gestion/services/registro_lote.py gestion/tests/test_registro_lote_transformacion.py
git commit -m "feat: RegistroLoteService usa producto_entrada/salida, delega mezcla y merma"
```

---

## SP-3: API / Views y Serializers

### Task 7: Serializers — OrdenProduccion y ComponenteMezclaOP

**Files:**
- Modify: `gestion/serializers.py`

- [ ] **7.1 Actualizar `OrdenProduccionSerializer`**

Localizar `OrdenProduccionSerializer` en `gestion/serializers.py`. Reemplazar el campo `producto` por:

```python
class ComponenteMezclaOPSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponenteMezclaOP
        fields = ['id', 'producto', 'bodega', 'porcentaje', 'cantidad_kg']

    def validate_porcentaje(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError('El porcentaje debe ser mayor a 0 y máximo 100.')
        return value

    def validate(self, data):
        # Calcular cantidad_kg automáticamente si no se envía
        orden = self.context.get('orden')
        if orden and 'porcentaje' in data:
            data['cantidad_kg'] = (
                data['porcentaje'] / Decimal('100') * orden.peso_neto_requerido
            ).quantize(Decimal('0.001'))
        return data


class OrdenProduccionSerializer(serializers.ModelSerializer):
    componentes_mezcla = ComponenteMezclaOPSerializer(many=True, required=False)
    producto_entrada_detail = ProductoSerializer(source='producto_entrada', read_only=True)
    producto_salida_detail = ProductoSerializer(source='producto_salida', read_only=True)

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'codigo', 'estado', 'prioridad',
            'producto_entrada', 'producto_entrada_detail',
            'producto_salida', 'producto_salida_detail',
            'bodega_entrada', 'bodega_salida',
            'bodega_quimicos', 'formula_color',
            'peso_neto_requerido', 'area', 'sede',
            'maquina_asignada', 'operario_asignado',
            'observaciones', 'inventario_descontado',
            'fecha_inicio_planificada', 'fecha_fin_planificada',
            'componentes_mezcla', 'peso_producido',
        ]
        read_only_fields = ['peso_producido', 'inventario_descontado']

    def validate(self, data):
        componentes = data.get('componentes_mezcla', [])
        if componentes:
            total = sum(c['porcentaje'] for c in componentes)
            if abs(total - Decimal('100')) > Decimal('0.01'):
                raise serializers.ValidationError({
                    'componentes_mezcla': f'La suma de porcentajes debe ser 100%. Actual: {total}%'
                })
        return data

    def create(self, validated_data):
        componentes_data = validated_data.pop('componentes_mezcla', [])
        orden = super().create(validated_data)
        for comp_data in componentes_data:
            comp_data['cantidad_kg'] = (
                comp_data['porcentaje'] / Decimal('100') * orden.peso_neto_requerido
            ).quantize(Decimal('0.001'))
            ComponenteMezclaOP.objects.create(orden=orden, **comp_data)
        return orden
```

- [ ] **7.2 Actualizar `RegistrarLoteSerializer`**

Localizar `RegistrarLoteSerializer` y agregar campo `consumos`:

```python
class ConsumoLoteDetalleInputSerializer(serializers.Serializer):
    lote_origen_id = serializers.IntegerField()
    cantidad_kg = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    genera_nuevo_lote = serializers.BooleanField(default=True)


class RegistrarLoteSerializer(serializers.Serializer):
    codigo_lote = serializers.CharField(required=False, allow_blank=True)
    peso_neto_producido = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    peso_merma = serializers.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'), min_value=Decimal('0'))
    tipo_merma = serializers.ChoiceField(choices=['maquina', 'material', 'setup', 'corte', 'otro'], required=False)
    clasificacion_calidad = serializers.ChoiceField(choices=['primera', 'segunda', 'saldo'], default='primera')
    maquina = serializers.IntegerField(required=False, allow_null=True)
    operario = serializers.IntegerField(required=False, allow_null=True)
    turno = serializers.CharField(required=False, default='')
    hora_inicio = serializers.DateTimeField(required=False, allow_null=True)
    hora_final = serializers.DateTimeField(required=False, allow_null=True)
    unidades_empaque = serializers.IntegerField(default=1, min_value=1)
    presentacion = serializers.CharField(default='cono')
    consumos = ConsumoLoteDetalleInputSerializer(many=True, required=False)
    completar_orden = serializers.BooleanField(default=False)

    def validate(self, data):
        if data.get('peso_merma', 0) > 0 and not data.get('tipo_merma'):
            raise serializers.ValidationError({
                'tipo_merma': 'tipo_merma es obligatorio cuando peso_merma > 0.'
            })
        return data
```

- [ ] **7.3 Commit serializers**
```bash
git add gestion/serializers.py
git commit -m "feat: serializers para transformacion, mezcla y lote con consumos"
```

---

### Task 8: Actualizar Views

**Files:**
- Modify: `gestion/views/production_views.py`

- [ ] **8.1 Actualizar `perform_create` en `OrdenProduccionViewSet`**

Reemplazar `perform_create`:

```python
def perform_create(self, serializer):
    user = self.request.user
    sede = getattr(user, 'sede', None) or serializer.validated_data.get('sede')
    orden = serializer.save(sede=sede)
    if orden.formula_color and orden.bodega_quimicos:
        DescargaQuimicosService.descargar_para_op(orden, user)
        logger.info(f'Descarga química ejecutada para OP-{orden.codigo}',
                    extra={'sd': {'op': orden.codigo, 'usuario': user.username}})
```

- [ ] **8.2 Actualizar `perform_update` en `OrdenProduccionViewSet`**

El método ya valida justificación — solo actualizar referencias de campo:
Cambiar cualquier referencia a `orden.producto` por `orden.producto_entrada` dentro del método.

- [ ] **8.3 Agregar `ComponenteMezclaOPViewSet`**

Agregar antes de `LoteProduccionViewSet`:

```python
class ComponenteMezclaOPViewSet(viewsets.ModelViewSet):
    """
    CRUD de componentes de mezcla. ISO 27001 A.9.4: solo jefe_area.
    """
    serializer_class = ComponenteMezclaOPSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]

    def get_queryset(self):
        orden_id = self.kwargs.get('orden_pk') or self.request.query_params.get('orden')
        qs = ComponenteMezclaOP.objects.select_related('producto', 'bodega', 'orden')
        if orden_id:
            qs = qs.filter(orden_id=orden_id)
        return qs.filter(orden__sede=self.request.user.sede)

    def perform_destroy(self, instance):
        justificacion = self.request.data.get('justificacion', '')
        if not justificacion:
            raise ValidationError({'justificacion': 'Justificación requerida para eliminar componente.'})
        instance._justificacion_auditoria = justificacion
        instance.delete()
```

- [ ] **8.4 Actualizar endpoint `rechazar` en `LoteProduccionViewSet`**

En el método `rechazar`, agregar reversión de mezcla y merma al inicio, antes de revertir el output:

```python
# Al inicio del método rechazar (después de obtener el lote):
from gestion.services.consumo_mezcla import ConsumoMezclaService
from gestion.services.merma_stock import MermaStockService

justificacion = request.data.get('justificacion', '')
if not justificacion:
    return Response({'error': 'Justificación requerida.'}, status=400)

# 1. Revertir mezcla (ConsumoLoteDetalle)
if lote.consumos_detalle.exists():
    ConsumoMezclaService.revertir(lote, request.user, justificacion)

# 2. Revertir merma vendible
MermaStockService.revertir(lote, request.user, justificacion)

# 3. (resto del código existente para revertir output y MP simple)
```

- [ ] **8.5 Registrar nueva ruta en `urls.py`**

En `gestion/urls.py` o el archivo de rutas de producción:
```python
router.register(r'componentes-mezcla', ComponenteMezclaOPViewSet, basename='componente-mezcla')
```

- [ ] **8.6 Ejecutar tests de integración**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests -v 1
```
Esperado: todos OK.

- [ ] **8.7 Commit**
```bash
git add gestion/views/production_views.py gestion/urls.py
git commit -m "feat: viewsets actualizados para transformacion, mezcla y merma"
```

---

## SP-4: Frontend CRUD Dashboards

### Task 9: Tipos TypeScript compartidos

**Files:**
- Create: `frontend/src/types/produccion.ts`

- [ ] **9.1 Crear tipos**

```typescript
// frontend/src/types/produccion.ts

export interface ComponenteMezclaOP {
  id: number
  producto: number
  producto_detail?: { id: number; codigo: string; descripcion: string }
  bodega: number
  bodega_detail?: { id: number; nombre: string }
  porcentaje: string
  cantidad_kg: string
}

export interface OrdenProduccion {
  id: number
  codigo: string
  estado: 'pendiente' | 'en_proceso' | 'finalizada'
  prioridad: 'baja' | 'normal' | 'alta' | 'urgente'
  producto_entrada: number
  producto_entrada_detail?: ProductoDetail
  producto_salida: number
  producto_salida_detail?: ProductoDetail
  bodega_entrada: number
  bodega_salida: number
  peso_neto_requerido: string
  peso_producido: string
  componentes_mezcla: ComponenteMezclaOP[]
  inventario_descontado: boolean
}

export interface ProductoDetail {
  id: number
  codigo: string
  descripcion: string
  tipo: string
}

export interface ConsumoInput {
  lote_origen_id: number
  cantidad_kg: string
  genera_nuevo_lote: boolean
}

export interface RegistrarLotePayload {
  peso_neto_producido: string
  peso_merma: string
  tipo_merma?: string
  maquina?: number
  turno: string
  unidades_empaque: number
  presentacion: string
  consumos?: ConsumoInput[]
  completar_orden?: boolean
}
```

- [ ] **9.2 Commit**
```bash
git add frontend/src/types/produccion.ts
git commit -m "feat: tipos TypeScript para transformacion y mezcla"
```

---

### Task 10: JefePlantaDashboard — Formulario OP actualizado

**Files:**
- Modify: `frontend/src/components/jefe-planta/JefePlantaDashboard.tsx`

- [ ] **10.1 Actualizar el formulario de nueva OP**

Localizar el formulario de creación de `OrdenProduccion`. Reemplazar el selector único de `producto` por dos selectores:

```tsx
{/* Producto de Entrada */}
<div className="space-y-2">
  <Label htmlFor="producto_entrada">Producto de Entrada (MP)</Label>
  <Select
    value={form.producto_entrada?.toString()}
    onValueChange={(v) => setForm(f => ({ ...f, producto_entrada: parseInt(v) }))}
  >
    <SelectTrigger><SelectValue placeholder="Seleccionar producto de entrada" /></SelectTrigger>
    <SelectContent>
      {productos.map(p => (
        <SelectItem key={p.id} value={p.id.toString()}>
          {p.codigo} — {p.descripcion}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

{/* Bodega de Entrada */}
<div className="space-y-2">
  <Label htmlFor="bodega_entrada">Bodega de Entrada</Label>
  <Select
    value={form.bodega_entrada?.toString()}
    onValueChange={(v) => setForm(f => ({ ...f, bodega_entrada: parseInt(v) }))}
  >
    <SelectTrigger><SelectValue placeholder="Seleccionar bodega de entrada" /></SelectTrigger>
    <SelectContent>
      {bodegas.map(b => (
        <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

{/* Producto de Salida */}
<div className="space-y-2">
  <Label htmlFor="producto_salida">Producto de Salida (PT)</Label>
  <Select
    value={form.producto_salida?.toString()}
    onValueChange={(v) => setForm(f => ({ ...f, producto_salida: parseInt(v) }))}
  >
    <SelectTrigger><SelectValue placeholder="Seleccionar producto de salida" /></SelectTrigger>
    <SelectContent>
      {productos.map(p => (
        <SelectItem key={p.id} value={p.id.toString()}>
          {p.codigo} — {p.descripcion}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

{/* Bodega de Salida */}
<div className="space-y-2">
  <Label htmlFor="bodega_salida">Bodega de Salida</Label>
  <Select
    value={form.bodega_salida?.toString()}
    onValueChange={(v) => setForm(f => ({ ...f, bodega_salida: parseInt(v) }))}
  >
    <SelectTrigger><SelectValue placeholder="Seleccionar bodega de salida" /></SelectTrigger>
    <SelectContent>
      {bodegas.map(b => (
        <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

Actualizar la función de submit para enviar `producto_entrada`, `producto_salida`, `bodega_entrada`, `bodega_salida` en lugar de `producto` y `bodega`.

- [ ] **10.2 Commit**
```bash
git add frontend/src/components/jefe-planta/JefePlantaDashboard.tsx
git commit -m "feat: formulario OP con producto_entrada/salida y bodega_entrada/salida"
```

---

### Task 11: ManageMaquinas — CRUD con config de merma

**Files:**
- Create: `frontend/src/components/jefe-area/ManageMaquinas.tsx`

- [ ] **11.1 Crear componente**

```tsx
// frontend/src/components/jefe-area/ManageMaquinas.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { AlertDialog, AlertDialogAction, AlertDialogCancel,
         AlertDialogContent, AlertDialogDescription,
         AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Textarea } from '@/components/ui/textarea'

interface Maquina {
  id: number
  nombre: string
  estado: 'operativa' | 'mantenimiento' | 'inactiva'
  capacidad_maxima: string
  eficiencia_ideal: string
  producto_merma: number | null
  producto_merma_detail?: { id: number; codigo: string; descripcion: string }
  bodega_merma: number | null
  bodega_merma_detail?: { id: number; nombre: string }
}

interface ManageMaquinasProps {
  areaId?: number
}

export function ManageMaquinas({ areaId }: ManageMaquinasProps) {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Maquina | null>(null)
  const [deleting, setDeleting] = useState<Maquina | null>(null)
  const [justificacion, setJustificacion] = useState('')
  const [form, setForm] = useState({
    nombre: '', estado: 'operativa', capacidad_maxima: '',
    eficiencia_ideal: '0.85', producto_merma: '', bodega_merma: ''
  })

  const { data: maquinas = [] } = useQuery<Maquina[]>({
    queryKey: ['maquinas', areaId],
    queryFn: () => api.get(`/maquinas/${areaId ? `?area=${areaId}` : ''}`).then(r => r.data.results ?? r.data)
  })

  const { data: productosMerma = [] } = useQuery({
    queryKey: ['productos-merma'],
    queryFn: () => api.get('/productos/?tipo=merma').then(r => r.data.results ?? r.data)
  })

  const { data: bodegas = [] } = useQuery({
    queryKey: ['bodegas'],
    queryFn: () => api.get('/bodegas/').then(r => r.data.results ?? r.data)
  })

  const saveMutation = useMutation({
    mutationFn: (data: object) => editing
      ? api.patch(`/maquinas/${editing.id}/`, data)
      : api.post('/maquinas/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maquinas'] })
      setDialogOpen(false)
      toast.success(editing ? 'Máquina actualizada' : 'Máquina creada')
    },
    onError: () => toast.error('Error al guardar')
  })

  const deleteMutation = useMutation({
    mutationFn: ({ id, justificacion }: { id: number; justificacion: string }) =>
      api.delete(`/maquinas/${id}/`, { data: { justificacion } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maquinas'] })
      setDeleteDialogOpen(false)
      toast.success('Máquina eliminada')
    },
    onError: () => toast.error('Error al eliminar')
  })

  const openCreate = () => {
    setEditing(null)
    setForm({ nombre: '', estado: 'operativa', capacidad_maxima: '',
               eficiencia_ideal: '0.85', producto_merma: '', bodega_merma: '' })
    setDialogOpen(true)
  }

  const openEdit = (m: Maquina) => {
    setEditing(m)
    setForm({
      nombre: m.nombre, estado: m.estado,
      capacidad_maxima: m.capacidad_maxima,
      eficiencia_ideal: m.eficiencia_ideal,
      producto_merma: m.producto_merma?.toString() ?? '',
      bodega_merma: m.bodega_merma?.toString() ?? ''
    })
    setDialogOpen(true)
  }

  const handleSubmit = () => {
    saveMutation.mutate({
      nombre: form.nombre, estado: form.estado,
      capacidad_maxima: form.capacidad_maxima,
      eficiencia_ideal: form.eficiencia_ideal,
      producto_merma: form.producto_merma || null,
      bodega_merma: form.bodega_merma || null,
      area: areaId
    })
  }

  const estadoBadge = (e: string) => ({
    operativa: 'default', mantenimiento: 'secondary', inactiva: 'destructive'
  } as const)[e] ?? 'default'

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Máquinas</h3>
        <Button onClick={openCreate}>+ Nueva Máquina</Button>
      </div>

      <div className="border rounded-md">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="p-3 text-left">Nombre</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3 text-left">Capacidad (kg/turno)</th>
              <th className="p-3 text-left">Producto Merma</th>
              <th className="p-3 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {maquinas.map(m => (
              <tr key={m.id} className="border-t hover:bg-muted/50">
                <td className="p-3 font-medium">{m.nombre}</td>
                <td className="p-3">
                  <Badge variant={estadoBadge(m.estado)}>{m.estado}</Badge>
                </td>
                <td className="p-3">{m.capacidad_maxima} kg</td>
                <td className="p-3">
                  {m.producto_merma_detail
                    ? <span className="text-green-700">{m.producto_merma_detail.codigo}</span>
                    : <span className="text-muted-foreground">Sin configurar</span>}
                </td>
                <td className="p-3 space-x-2">
                  <Button size="sm" variant="outline" onClick={() => openEdit(m)}>Editar</Button>
                  <Button size="sm" variant="destructive"
                    onClick={() => { setDeleting(m); setJustificacion(''); setDeleteDialogOpen(true) }}>
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Dialog Crear/Editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar Máquina' : 'Nueva Máquina'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input value={form.nombre} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={form.estado} onValueChange={v => setForm(f => ({ ...f, estado: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="operativa">Operativa</SelectItem>
                  <SelectItem value="mantenimiento">Mantenimiento</SelectItem>
                  <SelectItem value="inactiva">Inactiva</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Capacidad máx. (kg)</Label>
                <Input type="number" value={form.capacidad_maxima}
                  onChange={e => setForm(f => ({ ...f, capacidad_maxima: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Eficiencia ideal</Label>
                <Input type="number" step="0.01" min="0" max="1" value={form.eficiencia_ideal}
                  onChange={e => setForm(f => ({ ...f, eficiencia_ideal: e.target.value }))} />
              </div>
            </div>
            <div className="border-t pt-4">
              <p className="text-sm font-medium text-muted-foreground mb-3">Configuración de Merma Vendible</p>
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label>Producto de Merma</Label>
                  <Select value={form.producto_merma}
                    onValueChange={v => setForm(f => ({ ...f, producto_merma: v }))}>
                    <SelectTrigger><SelectValue placeholder="Sin merma vendible" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Sin merma vendible</SelectItem>
                      {productosMerma.map((p: { id: number; codigo: string; descripcion: string }) => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.codigo} — {p.descripcion}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Bodega de Merma</Label>
                  <Select value={form.bodega_merma}
                    onValueChange={v => setForm(f => ({ ...f, bodega_merma: v }))}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar bodega" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Sin bodega asignada</SelectItem>
                      {bodegas.map((b: { id: number; nombre: string }) => (
                        <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <Button className="w-full" onClick={handleSubmit} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Guardando...' : 'Guardar'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* AlertDialog Eliminar */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar Máquina</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará "{deleting?.nombre}" permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-2">
            <Label>Justificación (obligatoria)</Label>
            <Textarea value={justificacion} onChange={e => setJustificacion(e.target.value)}
              placeholder="Ingrese el motivo de la eliminación..." className="mt-2" />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={justificacion.length < 10 || deleteMutation.isPending}
              onClick={() => deleting && deleteMutation.mutate({ id: deleting.id, justificacion })}>
              {deleteMutation.isPending ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
```

- [ ] **11.2 Integrar en `JefeAreaDashboard.tsx`**

Importar y agregar como pestaña en el dashboard:
```tsx
import { ManageMaquinas } from './ManageMaquinas'

// En el TabsContent de máquinas (o crear pestaña nueva):
<TabsContent value="maquinas">
  <ManageMaquinas areaId={user?.area} />
</TabsContent>
```

- [ ] **11.3 Commit**
```bash
git add frontend/src/components/jefe-area/ManageMaquinas.tsx frontend/src/components/jefe-area/JefeAreaDashboard.tsx
git commit -m "feat: ManageMaquinas CRUD con configuracion de merma vendible"
```

---

### Task 12: ComponenteMezclaPanel — CRUD de receta de mezcla

**Files:**
- Create: `frontend/src/components/jefe-area/ComponenteMezclaPanel.tsx`

- [ ] **12.1 Crear componente**

```tsx
// frontend/src/components/jefe-area/ComponenteMezclaPanel.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import type { ComponenteMezclaOP } from '@/types/produccion'

interface Props {
  ordenId: number
  pesoNeto: number
  readonly?: boolean
}

export function ComponenteMezclaPanel({ ordenId, pesoNeto, readonly = false }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ producto: '', bodega: '', porcentaje: '' })

  const { data: componentes = [] } = useQuery<ComponenteMezclaOP[]>({
    queryKey: ['componentes-mezcla', ordenId],
    queryFn: () => api.get(`/componentes-mezcla/?orden=${ordenId}`).then(r => r.data.results ?? r.data)
  })

  const { data: productos = [] } = useQuery({
    queryKey: ['productos'],
    queryFn: () => api.get('/productos/').then(r => r.data.results ?? r.data)
  })

  const { data: bodegas = [] } = useQuery({
    queryKey: ['bodegas'],
    queryFn: () => api.get('/bodegas/').then(r => r.data.results ?? r.data)
  })

  const addMutation = useMutation({
    mutationFn: (data: object) => api.post('/componentes-mezcla/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['componentes-mezcla', ordenId] })
      setForm({ producto: '', bodega: '', porcentaje: '' })
      toast.success('Componente agregado')
    },
    onError: (e: { response?: { data?: { componentes_mezcla?: string } } }) =>
      toast.error(e.response?.data?.componentes_mezcla ?? 'Error al agregar')
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/componentes-mezcla/${id}/`,
      { data: { justificacion: 'Eliminado por jefe de área' } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['componentes-mezcla', ordenId] })
      toast.success('Componente eliminado')
    }
  })

  const totalPorcentaje = componentes.reduce(
    (sum, c) => sum + parseFloat(c.porcentaje), 0
  )

  return (
    <div className="space-y-4 border rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Receta de Mezcla</h4>
        <div className={`text-sm font-semibold ${Math.abs(totalPorcentaje - 100) < 0.01 ? 'text-green-600' : 'text-destructive'}`}>
          Total: {totalPorcentaje.toFixed(1)}% {Math.abs(totalPorcentaje - 100) < 0.01 ? '✓' : '(debe ser 100%)'}
        </div>
      </div>

      {/* Barra visual de porcentajes */}
      {componentes.length > 0 && (
        <div className="h-4 rounded-full overflow-hidden flex">
          {componentes.map((c, i) => (
            <div key={c.id}
              style={{ width: `${c.porcentaje}%`, backgroundColor: `hsl(${i * 60}, 60%, 50%)` }}
              title={`${c.producto_detail?.codigo}: ${c.porcentaje}%`}
            />
          ))}
        </div>
      )}

      {/* Lista de componentes */}
      <div className="space-y-2">
        {componentes.map(c => (
          <div key={c.id} className="flex items-center justify-between p-2 bg-muted rounded">
            <div className="text-sm">
              <span className="font-medium">{c.producto_detail?.codigo}</span>
              <span className="text-muted-foreground ml-2">desde {c.bodega_detail?.nombre}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold">{c.porcentaje}%</span>
              <span className="text-muted-foreground text-xs">
                ({(parseFloat(c.porcentaje) * pesoNeto / 100).toFixed(1)} kg estimados)
              </span>
              {!readonly && (
                <Button size="sm" variant="ghost" className="text-destructive h-6 px-2"
                  onClick={() => deleteMutation.mutate(c.id)}>✕</Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Formulario agregar componente */}
      {!readonly && (
        <div className="grid grid-cols-3 gap-2 items-end pt-2 border-t">
          <div className="space-y-1">
            <Label className="text-xs">Producto</Label>
            <Select value={form.producto} onValueChange={v => setForm(f => ({ ...f, producto: v }))}>
              <SelectTrigger className="h-8"><SelectValue placeholder="Producto" /></SelectTrigger>
              <SelectContent>
                {productos.map((p: { id: number; codigo: string; descripcion: string }) => (
                  <SelectItem key={p.id} value={p.id.toString()}>
                    {p.codigo}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Bodega</Label>
            <Select value={form.bodega} onValueChange={v => setForm(f => ({ ...f, bodega: v }))}>
              <SelectTrigger className="h-8"><SelectValue placeholder="Bodega" /></SelectTrigger>
              <SelectContent>
                {bodegas.map((b: { id: number; nombre: string }) => (
                  <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">% Mezcla</Label>
            <div className="flex gap-1">
              <Input type="number" min="1" max="100" className="h-8"
                placeholder="50" value={form.porcentaje}
                onChange={e => setForm(f => ({ ...f, porcentaje: e.target.value }))} />
              <Button size="sm" className="h-8 px-3"
                disabled={!form.producto || !form.bodega || !form.porcentaje}
                onClick={() => addMutation.mutate({
                  orden: ordenId, producto: parseInt(form.producto),
                  bodega: parseInt(form.bodega), porcentaje: form.porcentaje
                })}>+</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **12.2 Commit**
```bash
git add frontend/src/components/jefe-area/ComponenteMezclaPanel.tsx
git commit -m "feat: ComponenteMezclaPanel CRUD con validacion visual de porcentajes"
```

---

### Task 13: OperarioDashboard — formulario lote con consumos de mezcla

**Files:**
- Modify: `frontend/src/components/operario/OperarioDashboard.tsx`

- [ ] **13.1 Actualizar el modal de registro de lote**

En el componente `OperarioDashboard.tsx`, localizar el Dialog de registro de lote. Agregar lógica para consumos de mezcla:

```tsx
// Agregar al estado del componente:
const [consumos, setConsumos] = useState<Array<{
  lote_origen_id: number | null;
  cantidad_kg: string;
  genera_nuevo_lote: boolean;
  codigo_ref: string;
}>>([])

// Cuando se selecciona una OP, si tiene componentes_mezcla, inicializar consumos:
useEffect(() => {
  if (selectedOrden?.componentes_mezcla?.length > 0) {
    setConsumos(selectedOrden.componentes_mezcla.map(c => ({
      lote_origen_id: null,
      cantidad_kg: c.cantidad_kg,
      genera_nuevo_lote: true,
      codigo_ref: c.producto_detail?.codigo ?? ''
    })))
  } else {
    setConsumos([])
  }
}, [selectedOrden])
```

Agregar en el formulario del Dialog, después del campo `peso_merma`:

```tsx
{/* Consumos de mezcla — solo si la OP tiene componentes */}
{selectedOrden?.componentes_mezcla?.length > 0 && (
  <div className="space-y-3 border rounded p-3 bg-muted/30">
    <p className="text-sm font-medium">Lotes de Entrada (Mezcla)</p>
    {consumos.map((consumo, idx) => (
      <div key={idx} className="grid grid-cols-2 gap-2 items-end">
        <div className="space-y-1">
          <Label className="text-xs">{consumo.codigo_ref} — Lote origen</Label>
          <Input
            placeholder="ID de lote origen"
            type="number"
            value={consumo.lote_origen_id ?? ''}
            onChange={e => {
              const updated = [...consumos]
              updated[idx].lote_origen_id = parseInt(e.target.value) || null
              setConsumos(updated)
            }}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Cantidad (kg)</Label>
          <Input
            type="number"
            step="0.001"
            value={consumo.cantidad_kg}
            onChange={e => {
              const updated = [...consumos]
              updated[idx].cantidad_kg = e.target.value
              setConsumos(updated)
            }}
          />
        </div>
      </div>
    ))}
  </div>
)}
```

Actualizar la función de submit para incluir `consumos` en el payload:

```tsx
const payload: RegistrarLotePayload = {
  peso_neto_producido: form.peso_neto_producido,
  peso_merma: form.peso_merma || '0',
  tipo_merma: form.tipo_merma || undefined,
  maquina: form.maquina ? parseInt(form.maquina) : undefined,
  turno: form.turno,
  unidades_empaque: parseInt(form.unidades_empaque) || 1,
  presentacion: form.presentacion,
  consumos: consumos.length > 0
    ? consumos.filter(c => c.lote_origen_id !== null).map(c => ({
        lote_origen_id: c.lote_origen_id!,
        cantidad_kg: c.cantidad_kg,
        genera_nuevo_lote: c.genera_nuevo_lote
      }))
    : undefined
}
```

- [ ] **13.2 Commit**
```bash
git add frontend/src/components/operario/OperarioDashboard.tsx
git commit -m "feat: OperarioDashboard soporta consumos de mezcla al registrar lote"
```

---

### Task 14: AdminSistemas — Productos con tipo merma

**Files:**
- Modify: `frontend/src/components/admin-sistemas/ManageProductos.tsx`

- [ ] **14.1 Agregar tipo 'merma' al selector de tipo de producto**

En `ManageProductos.tsx`, localizar el `<Select>` del campo `tipo`. Agregar la opción:
```tsx
<SelectItem value="merma">Merma / Desperdicio Vendible</SelectItem>
```

Agregar filtro por tipo en la tabla:
```tsx
// Junto a otros filtros existentes:
<Select value={filtroTipo} onValueChange={setFiltroTipo}>
  <SelectTrigger className="w-40"><SelectValue placeholder="Tipo" /></SelectTrigger>
  <SelectContent>
    <SelectItem value="">Todos</SelectItem>
    <SelectItem value="hilo">Hilo</SelectItem>
    <SelectItem value="tela">Tela</SelectItem>
    <SelectItem value="quimico">Químico</SelectItem>
    <SelectItem value="merma">Merma</SelectItem>
    <SelectItem value="insumo">Insumo</SelectItem>
  </SelectContent>
</Select>
```

- [ ] **14.2 Commit**
```bash
git add frontend/src/components/admin-sistemas/ManageProductos.tsx
git commit -m "feat: ManageProductos agrega tipo merma y filtro por tipo"
```

---

## Verificación Final

### Task 15: Tests de integración completos

- [ ] **15.1 Ejecutar toda la suite backend**
```bash
docker exec texcore-backend-1 python manage.py test gestion.tests inventory.tests -v 1
```
Esperado: todos los tests existentes siguen OK + nuevos tests GREEN.

- [ ] **15.2 Verificar migrations están todas aplicadas**
```bash
docker exec texcore-backend-1 python manage.py showmigrations gestion inventory
```
Esperado: todas con `[X]`.

- [ ] **15.3 Verificar que el servidor levanta sin errores**
```bash
docker exec texcore-backend-1 python manage.py check --deploy
```

- [ ] **15.4 Verificar frontend compila sin errores TypeScript**
```bash
docker exec texcore-frontend-1 npm run build 2>&1 | tail -20
```
Esperado: `built in X.XXs` sin errores de tipo.

- [ ] **15.5 Commit final y merge preparation**
```bash
git add .
git commit -m "feat: produccion flexible — transformacion, mezcla de lotes y merma vendible (ISO27001+COBIT)"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `producto_entrada` + `producto_salida` en OrdenProduccion (Tasks 2, 3, 7, 10)
- ✅ `ComponenteMezclaOP` con validación sum=100 (Tasks 2, 3, 7, 12)
- ✅ `ConsumoLoteDetalle` inmutable (Tasks 2, 5, 8)
- ✅ Merma vendible por máquina (Tasks 2, 3, 4, 11)
- ✅ `MermaStockService` SRP (Task 4)
- ✅ `ConsumoMezclaService` SRP (Task 5)
- ✅ `RegistroLoteService` actualizado (Task 6)
- ✅ ISO 27001 A.9.4 en ViewSets (Task 8)
- ✅ ISO 27001 A.12.4 — AuditableModel en nuevos modelos (Task 2)
- ✅ COBIT DSS06 — validación sum(porcentaje)==100 (Tasks 5, 7)
- ✅ COBIT MEA01 — documento_ref MERMA- para KPIs (Task 4)
- ✅ TDD con EP, BVA, STT (Tasks 4, 5, 6)
- ✅ Factories nuevas (Task 1)
- ✅ Frontend JefePlanta OP form (Task 10)
- ✅ Frontend JefeArea ManageMaquinas (Task 11)
- ✅ Frontend ComponenteMezclaPanel (Task 12)
- ✅ Frontend OperarioDashboard consumos mezcla (Task 13)
- ✅ Frontend AdminSistemas tipo merma (Task 14)
