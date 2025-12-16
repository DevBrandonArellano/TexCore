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
