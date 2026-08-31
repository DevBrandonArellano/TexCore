# Recursos Algorítmicos y Técnicas de Optimización en TexCore

## Introducción

Este documento detalla las estrategias algorítmicas y estructurales implementadas en el backend de TexCore para asegurar un alto rendimiento y escalabilidad. El objetivo es permitir que el sistema maneje una carga concurrente de ~50 usuarios de manera eficiente, minimizando los tiempos de respuesta y la carga sobre la base de datos. Las optimizaciones se centran en dos áreas clave: la complejidad de las consultas a la base de datos y la aceleración de las operaciones de búsqueda y filtrado.

---

## 1. Reducción de Complejidad Algorítmica en Consultas (Problema N+1)

### 1.1. Análisis Teórico del Problema

El "problema N+1" es un patrón de acceso a datos altamente ineficiente que degrada severamente el rendimiento de aplicaciones que utilizan un ORM (Mapeo Objeto-Relacional) como el de Django.

El problema ocurre al solicitar una lista de **N** objetos, donde cada objeto tiene una relación con otro modelo (ej. una `OrdenProduccion` que tiene un `Producto`). El comportamiento ingenuo es:

1.  Realizar **1** consulta inicial para obtener la lista de los **N** objetos principales.
2.  Posteriormente, al iterar sobre la lista para acceder a los datos del objeto relacionado, el ORM ejecuta **1** nueva consulta *por cada uno de los N objetos*.

Esto resulta en un total de **1 + N** consultas para una sola operación. Si un objeto tiene **k** relaciones que son accedidas, la cantidad total de consultas se convierte en **1 + k*N**.

### 1.2. Modelado Matemático y de Complejidad

Desde la perspectiva de la complejidad algorítmica, el problema N+1 representa una operación con **complejidad de tiempo lineal, O(N)**, en términos de accesos a la base de datos. El número de operaciones de I/O (el factor más lento en una aplicación web) escala directamente con el tamaño del conjunto de datos `N`. Para una aplicación con concurrencia, esto es catastrófico, ya que el tiempo de respuesta se degrada rápidamente a medida que los datos crecen.

**Función de Costo (Antes de la Optimización):**
`Costo(N) = C_inicial + N * (C_relacion_1 + C_relacion_2 + ... + C_relacion_k)`

### 1.3. Solución Implementada: Precarga de Datos Relacionados

La solución consiste en cambiar el paradigma de "traer después" (lazy loading) a "traer todo junto" (eager loading). Se utilizaron dos herramientas principales del ORM de Django:

-   **`select_related(*fields)`**: Para relaciones "uno a uno" y "muchos a uno" (ForeignKey). Utiliza un `JOIN` de SQL para obtener los objetos principales y los relacionados en una **única y sola consulta a la base de datos**.

-   **`prefetch_related(*fields)`**: Para relaciones "muchos a muchos" o relaciones inversas. Funciona de manera ligeramente diferente: ejecuta una consulta para los objetos principales y luego una segunda consulta para *todos* los objetos relacionados, uniendo los datos en Python. Aunque son dos consultas, sigue siendo un número constante.

### 1.4. Resultado: Complejidad Constante O(1)

Al aplicar estas técnicas, la complejidad de las consultas se reduce a **O(1)**. El número de consultas a la base de datos se vuelve constante e independiente del número `N` de objetos en la lista.

**Función de Costo (Después de la Optimización):**
`Costo(N) = C_join_único` (un costo fijo y mucho menor)

#### Ejemplo Práctico en TexCore: `MovimientoInventarioViewSet`

-   **Antes (Código Problemático):**
    ```python
    # en inventory/views.py
    class MovimientoInventarioViewSet(viewsets.ModelViewSet):
        # ...
        def get_queryset(self):
            return MovimientoInventario.objects.all() # Devuelve N objetos
    
    # en inventory/serializers.py
    class MovimientoInventarioSerializer(serializers.ModelSerializer):
        producto = serializers.StringRelatedField() # Accede a la relación -> +N consultas
        lote = serializers.StringRelatedField()     # Accede a la relación -> +N consultas
        # ... (3 relaciones más)
    ```
    *Costo para N=100:* `1 + 5*100 = 501` consultas.

-   **Después (Código Optimizado):**
    ```python
    # en inventory/views.py
    class MovimientoInventarioViewSet(viewsets.ModelViewSet):
        # ...
        def get_queryset(self):
            # Se le indica a Django que traiga todo en una sola consulta SQL con JOINs
            return MovimientoInventario.objects.select_related(
                'producto', 'lote', 'bodega_origen', 'bodega_destino', 'usuario'
            ).all()
    ```
    *Costo para N=100 (o N=1000):* **1 consulta**.

#### Ejemplo Práctico en TexCore: `StockBodegaViewSet` (N+1 encontrado en auditoría 2026-08-31)

Un caso particularmente sutil de este problema: un `select_related` **incompleto** —que cubre las relaciones directas pero no una relación anidada usada en un `__str__`— sigue produciendo N+1 aunque el código "parezca" optimizado a primera vista.

-   **Antes (Código Problemático):**
    ```python
    # en inventory/views/stock_views.py
    class StockBodegaViewSet(viewsets.ReadOnlyModelViewSet):
        def get_queryset(self):
            queryset = StockBodega.objects.select_related(
                'bodega', 'producto', 'lote'
            ).all()  # falta 'bodega__sede'
    ```
    ```python
    # en gestion/models/catalogo.py
    class Bodega(models.Model):
        def __str__(self):
            return f"{self.nombre} ({self.sede.nombre})"  # accede a self.sede -> +1 consulta
    ```
    El serializer (`StockBodegaSerializer`) expone `bodega` con `StringRelatedField`, lo que invoca `Bodega.__str__()` por cada fila. Como `sede` no estaba precargado por el `select_related`, cada fila disparaba una consulta extra para traer la sede de su bodega.

    *Verificado con `CaptureQueriesContext`:* **3466 queries para 3465 filas de stock** (1 + N).

-   **Después (Código Optimizado):**
    ```python
    # en inventory/views/stock_views.py
    class StockBodegaViewSet(viewsets.ReadOnlyModelViewSet):
        def get_queryset(self):
            queryset = StockBodega.objects.select_related(
                'bodega__sede', 'producto', 'lote'
            ).all()
    ```
    *Verificado con `CaptureQueriesContext`:* **1 sola consulta**, independiente de N.

    **Lección:** al auditar un `select_related`/`prefetch_related`, no basta con revisar las relaciones que el serializer expone directamente — hay que rastrear también los accesos que ocurren dentro de `__str__` u otros métodos de modelo invocados indirectamente (p. ej. por `StringRelatedField`). El sistema fue validado con pruebas de carga real sosteniendo 100 usuarios concurrentes con 0% de errores (ver [REQUISITOS_INFRAESTRUCTURA.md](../arquitectura/REQUISITOS_INFRAESTRUCTURA.md)); este N+1 solo se manifestó como un problema serio bajo esa carga concurrente, no en mediciones de un solo usuario.

---

## 2. Aceleración de Búsquedas Mediante Indexación

### 2.1. Análisis Teórico

Una base de datos almacena los datos de una tabla en un orden determinado (generalmente por clave primaria). Cuando se ejecuta una consulta con una cláusula `WHERE` sobre un campo no indexado (ej. `filter(estado='en_proceso')`), el motor de la base de datos debe, en el peor de los casos, escanear la tabla completa fila por fila para encontrar las coincidencias. Esto se conoce como un **Full Table Scan**.

Un **índice** es una estructura de datos secundaria (comúnmente un Árbol-B) que almacena los valores de una columna específica y un puntero a la fila original. Esta estructura está ordenada, lo que permite a la base de datos realizar búsquedas extremadamente rápidas (con **complejidad logarítmica, O(log N)**) en lugar de búsquedas lineales (O(N)).

La analogía perfecta es el índice de un libro: en lugar de hojear todo el libro para encontrar un capítulo, vas al índice y te dice la página exacta.

### 2.2. Implementación en TexCore

Se identificaron los campos que se usan con frecuencia en filtros a través de la API y se les añadió un índice.

#### Ejemplo Práctico en TexCore: `OrdenProduccion.estado`

-   **Antes:**
    ```python
    # en gestion/models.py
    class OrdenProduccion(models.Model):
        # ...
        estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    ```
    Una consulta como `OrdenProduccion.objects.filter(estado='en_proceso')` provocaría un Full Table Scan.

-   **Después:**
    ```python
    # en gestion/models.py
    class OrdenProduccion(models.Model):
        # ...
        estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)
    ```
    Ahora, la misma consulta usará el índice sobre el campo `estado`, resultando en una búsqueda casi instantánea.

### 2.3. Contrapartidas (Trade-offs)

La indexación no es gratuita. Consume espacio en disco adicional y ralentiza ligeramente las operaciones de escritura (`INSERT`, `UPDATE`, `DELETE`), ya que la base de datos debe actualizar tanto la tabla como el índice. Por esta razón, los índices se aplicaron selectivamente solo a los campos que se benefician claramente de una aceleración en la lectura.

---

## 3. Optimización de Estado en el Frontend (Navegación Híbrida)

### 3.1. Análisis del Problema de Estado Local
En aplicaciones React (SPA), es común manejar la paginación y el filtrado en componentes de tablas de datos utilizando el estado local (`useState`). Esto puede resultar en una mala experiencia de usuario (imposibilidad de compartir enlaces exactos, uso roto de las flechas del navegador) y peticiones redundantes a la API al recargar componentes por cambios de estado no optimizados.

### 3.2. Solución: Estado Sincronizado con URL
TexCore implementa un modelo de **Navegación Híbrida** para el frontend, donde el estado de la UI crítico reside enteramente en los **Query Parameters** de la URL, utilizando `useSearchParams` de `react-router-dom`.

#### Beneficios de Rendimiento y Arquitectura:
-   **Fuente Única de Verdad**: Los componentes React quedan libres de estado complejo. Si la URL cambia, la aplicación reacciona explícitamente y dispara sus peticiones correspondientes dentro de `useEffect`.
-   **Mitigación de Re-Renders**: Se evitan actualizaciones de estado locales secuenciales que pudiesen causar inconsistencia y múltiples `render()` en cadena.
-   **Integración Natural de Caching**: Navegadores y proxys inversos pueden cachear de forma precisa peticiones a la API que se corresponden con rutas parametrizadas exactas (ej. `/api/pedidos/?page=2&estado=activo`).

Para más detalles sobre la directiva de diseño y su ejecución técnica, consultar [ADR\_NAVEGACION\_HIBRIDA.md](../docs/ADR_NAVEGACION_HIBRIDA.md) y [IMPLEMENTACION\_NAVEGACION\_HIBRIDA.md](../docs/IMPLEMENTACION_NAVEGACION_HIBRIDA.md).

---

> **[Sprint 6 — 2026-04-10]**

## 4. Capa de Servicios (Service Layer) con Value Objects Inmutables

### 4.1. Problema: Lógica de Negocio en las Vistas (Fat Views)

Concentrar la lógica de cálculo de KPIs directamente dentro de las Django `APIView` genera un modelo de complejidad acumulativa: cada nuevo indicador añade ramas condicionales a la vista, incrementando el número de querysets independientes y dificultando los tests unitarios.

### 4.2. Solución Implementada

Se introdujo una **capa de servicios** (`gestion/services/`, `inventory/services/`) que encapsula los querysets y los cálculos de métricas. Las vistas solo invocan el servicio y serializan el resultado.

Los resultados se modelan como **Value Objects inmutables** (`@dataclass(frozen=True)`). Esto garantiza que la vista nunca pueda alterar accidentalmente el estado del KPI tras calcularlo.

```python
# gestion/services/produccion_kpi_service.py
@dataclass(frozen=True)
class ProduccionKPIs:
    ops_estado: OpsEstado
    kg_producidos_mes: Decimal
    eficiencia_promedio: float

class ProduccionKPIService:
    def obtener_kpis(self, sede_id=None) -> ProduccionKPIs:
        # Un único bloque de querysets optimizados con annotate/aggregate
        ...
        return ProduccionKPIs(ops_estado=..., kg_producidos_mes=..., eficiencia_promedio=...)
```

### 4.3. Beneficios de Rendimiento y Arquitectura

| Aspecto | Sin Service Layer | Con Service Layer |
|---------|-----------------|------------------|
| **Querysets por vista** | N independientes (sin consolidar) | Agrupados con `annotate`/`aggregate` en un solo bloque |
| **Mutabilidad del resultado** | Dict mutable, propenso a efectos secundarios | `frozen=True` — inmutable por construcción |
| **Testabilidad** | Requiere cliente HTTP completo | Mock del servicio con `MagicMock()` |
| **Extensibilidad** | Nuevos KPIs → modifica la vista | Nuevos KPIs → nuevo Value Object, vista intacta |

Los servicios en producción son `ProduccionKPIService` y `ExecutiveKPIService`. Ver [Arquitectura y Desarrollo](arquitectura_y_desarrollo.md) para el diagrama de dependencias completo.
