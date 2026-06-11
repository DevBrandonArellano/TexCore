# Integración Completa de Flujo Multi-Área en TexCore

## Resumen Ejecutivo

Se ha completado la integración de un sistema de producción multi-etapas con transferencias interárea en TexCore. El sistema ahora soporta:

1. **Etapas de Producción Sequential** - Dentro de cada área con máquinas, bodegas intermedias
2. **Transferencias Interárea** - Movimiento de productos entre áreas con trazabilidad
3. **Flujo Visual** - Dashboard mostrando el flujo completo de órdenes a través de áreas
4. **Gestión Integrada** - Panel de Jefe de Área con todas las herramientas necesarias

---

## Cambios Realizados

### 1. Backend - Modelos de Datos

**Archivo**: `gestion/models.py`

#### EtapaProduccion (Modelo existente - línea ~1202)
```python
class EtapaProduccion(models.Model):
    area = ForeignKey(Area, on_delete=CASCADE)
    nombre = CharField(max_length=255)
    orden = PositiveIntegerField()  # Orden secuencial en el área
    maquina = ForeignKey(Maquina, on_delete=PROTECT)
    bodega_entrada = ForeignKey(Bodega, on_delete=PROTECT)
    bodega_salida = ForeignKey(Bodega, on_delete=PROTECT)
    tiempo_procesamiento_minutos = PositiveIntegerField(null=True)
    
    class Meta:
        unique_together = ['area', 'orden']
        ordering = ['area', 'orden']
```

#### TransferenciaInterarea (Modelo existente - línea ~1247)
```python
class TransferenciaInterarea(models.Model):
    orden_area_origen = ForeignKey(OrdenProduccion, on_delete=CASCADE)
    orden_area_destino = ForeignKey(OrdenProduccion, on_delete=CASCADE)
    bodega_origen = ForeignKey(Bodega, on_delete=PROTECT)
    bodega_destino = ForeignKey(Bodega, on_delete=PROTECT)
    cantidad_transferida = DecimalField(max_digits=12, decimal_places=3)
    fecha_transferencia = DateTimeField(auto_now_add=True)
    usuario_responsable = ForeignKey(CustomUser, on_delete=PROTECT)
    observaciones = TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha_transferencia']
        indexes = [
            Index(fields=['orden_area_origen', 'orden_area_destino']),
            Index(fields=['fecha_transferencia']),
        ]
```

---

### 2. Backend - Serializers

**Archivo**: `gestion/serializers.py` (líneas 1176-1210)

```python
class EtapaProduccionSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    bodega_entrada_nombre = serializers.CharField(source='bodega_entrada.nombre', read_only=True)
    bodega_salida_nombre = serializers.CharField(source='bodega_salida.nombre', read_only=True)
    
    class Meta:
        model = EtapaProduccion
        fields = [
            'id', 'area', 'area_nombre', 'nombre', 'orden',
            'maquina', 'maquina_nombre',
            'bodega_entrada', 'bodega_entrada_nombre',
            'bodega_salida', 'bodega_salida_nombre',
            'tiempo_procesamiento_minutos',
            'fecha_creacion', 'fecha_modificacion'
        ]

class TransferenciaInterareaSerializer(serializers.ModelSerializer):
    orden_area_origen = OrdenProduccionSerializer(read_only=True)
    orden_area_destino = OrdenProduccionSerializer(read_only=True)
    bodega_origen_nombre = serializers.CharField(source='bodega_origen.nombre', read_only=True)
    bodega_destino_nombre = serializers.CharField(source='bodega_destino.nombre', read_only=True)
    usuario_responsable_nombre = serializers.CharField(source='usuario_responsable.get_full_name', read_only=True)
    
    class Meta:
        model = TransferenciaInterarea
        fields = [
            'id', 'orden_area_origen', 'orden_area_destino',
            'bodega_origen', 'bodega_origen_nombre',
            'bodega_destino', 'bodega_destino_nombre',
            'cantidad_transferida', 'fecha_transferencia',
            'usuario_responsable', 'usuario_responsable_nombre',
            'observaciones', 'fecha_creacion', 'fecha_modificacion'
        ]
```

---

### 3. Backend - ViewSets y Endpoints

**Archivo**: `gestion/views/production_views.py` (líneas 975-1037)

```python
class EtapaProduccionViewSet(viewsets.ModelViewSet):
    queryset = EtapaProduccion.objects.select_related('area', 'maquina', 'bodega_entrada', 'bodega_salida')
    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ['area', 'maquina']
    ordering = ['area', 'orden']
    
    def get_queryset(self):
        user = self.request.user
        # Admin ve todas, Jefe de Área ve solo su área
        if user.is_superuser or user.groups.filter(name='Admin Sistemas').exists():
            return self.queryset
        if hasattr(user, 'area') and user.area:
            return self.queryset.filter(area=user.area)
        return EtapaProduccion.objects.none()

class TransferenciaInterareaViewSet(viewsets.ModelViewSet):
    queryset = TransferenciaInterarea.objects.select_related(
        'orden_area_origen', 'orden_area_destino',
        'bodega_origen', 'bodega_destino', 'usuario_responsable'
    )
    serializer_class = TransferenciaInterareaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    ordering = ['-fecha_transferencia']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='Admin Sistemas').exists():
            return self.queryset
        if hasattr(user, 'area') and user.area:
            # Jefe de Área ve transferencias salientes y entrantes
            return self.queryset.filter(
                orden_area_origen__area=user.area
            ) | self.queryset.filter(
                orden_area_destino__area=user.area
            )
        return TransferenciaInterarea.objects.none()
    
    def perform_create(self, serializer):
        # Auto-asigna al usuario logueado
        serializer.save(usuario_responsable=self.request.user)
```

**Endpoints Disponibles**:
- `GET/POST /api/etapas-produccion/` - Listar/crear etapas
- `GET/PATCH/DELETE /api/etapas-produccion/{id}/` - Detalle/editar/eliminar
- `GET/POST /api/transferencias-interarea/` - Listar/registrar transferencias
- `GET /api/transferencias-interarea/{id}/` - Ver transferencia

---

### 4. Frontend - Componentes

#### EtapasProduccion.tsx
**Ruta**: `frontend/src/components/produccion/EtapasProduccion.tsx`

Componente para gestionar las etapas secuenciales de un área:
- ✅ Crear etapa con: nombre, orden, máquina, bodega entrada/salida, tiempo procesamiento
- ✅ Editar etapa existente
- ✅ Eliminar etapa
- ✅ Mostrar flujo visual con ChevronRight entre etapas
- ✅ Filtrar por área
- ✅ Validaciones en tiempo real

```tsx
<EtapasProduccion areaId={profile.user.area} />
```

#### TransferenciasInterarea.tsx
**Ruta**: `frontend/src/components/produccion/TransferenciasInterarea.tsx`

Componente para registrar transferencias de productos entre áreas:
- ✅ Crear transferencia especificando: orden destino, cantidad, observaciones
- ✅ Ver historial de transferencias salientes
- ✅ Mostrar bodegas origen/destino
- ✅ Registrar usuario responsable automáticamente
- ✅ Validaciones de cantidad y estado

```tsx
<TransferenciasInterarea areaId={profile.user.area} />
```

#### FlujoProduccion.tsx
**Ruta**: `frontend/src/components/produccion/FlujoProduccion.tsx`

Componente para visualizar el flujo completo:
- ✅ Mostrar todas las órdenes recientes
- ✅ Para cada orden, mostrar etapas secuenciales
- ✅ Visualizar bodega entrada/salida de cada etapa
- ✅ Mostrar máquina asignada a cada etapa
- ✅ Barra de progreso de peso producido
- ✅ Estado de la orden con iconos

---

### 5. Frontend - Integración en Dashboard

**Archivo**: `frontend/src/components/jefe-area/JefeAreaDashboard.tsx`

Se agregaron tres nuevas secciones al dashboard de Jefe de Área:

```tsx
{/* Flujo de Producción - Visualización General */}
{profile?.user.area && <FlujoProduccion />}

{/* Etapas de Producción - Configuración */}
{profile?.user.area && <EtapasProduccion areaId={profile.user.area} />}

{/* Transferencias Interárea */}
{profile?.user.area && <TransferenciasInterarea areaId={profile.user.area} />}
```

Ubicación en el dashboard:
1. KPIs (sin cambios)
2. Planificación y Asignación de Órdenes (sin cambios)
3. **NUEVO: Flujo de Producción General** ← Nueva sección
4. **NUEVO: Etapas de Producción** ← Nueva sección
5. **NUEVO: Transferencias Interárea** ← Nueva sección
6. Estado de Máquinas (sin cambios)
7. Alertas de Inventario (sin cambios)
8. Gestión de Lotes (sin cambios)
9. Gestión de Máquinas (sin cambios)

---

### 6. Configuración de URLs

**Archivo**: `gestion/urls.py`

Se registraron dos nuevos routers:
```python
router.register(r'etapas-produccion', EtapaProduccionViewSet, basename='etapa-produccion')
router.register(r'transferencias-interarea', TransferenciaInterareaViewSet, basename='transferencia-interarea')
```

---

## Flujo de Uso - Jefe de Área

### Paso 1: Configuración Inicial (Una sola vez)
1. Jefe de Área accede al dashboard
2. En sección "Etapas de Producción", configura las etapas:
   - Etapa 1: Teñido
     - Máquina: Tinturadora #1
     - Entrada: Bodega MP Tintura
     - Salida: Bodega Secado
     - Tiempo: 120 min
   - Etapa 2: Secado
     - Máquina: Secadora Industrial
     - Entrada: Bodega Secado
     - Salida: Bodega Final Tintura
     - Tiempo: 60 min

### Paso 2: Completar Detalle de Orden
1. Jefe de Planta crea orden básica
2. Jefe de Área completa detalles vía `PATCH /ordenes-produccion/{id}/completar_detalles/`

### Paso 3: Ejecutar Producción
1. Operario ejecuta lotes
2. Sistema registra producción automáticamente

### Paso 4: Transferir a Siguiente Área
1. Jefe de Área ve "Transferencias Interárea"
2. Hace clic en "Nueva Transferencia"
3. Selecciona orden destino (siguiente área)
4. Ingresa cantidad
5. Agrega observaciones (opcional)
6. Sistema registra transferencia y usuario responsable

### Paso 5: Siguiente Área Continúa
1. Jefe de Área siguiente recibe transferencia
2. Su bodega_entrada es automáticamente la bodega final del área anterior
3. Ejecuta sus propias etapas
4. Transfiere al siguiente

---

## Validaciones y Seguridad

### Permisos por Rol
- **Admin Sistemas**: Ve todo
- **Jefe de Área**: Ve solo su área y transferencias salientes/entrantes
- **Operario**: No accede a estos endpoints (protegidos)

### Validaciones Implementadas
- ✅ Orden secuencial única por área
- ✅ Usuario responsable auto-asignado en transferencias
- ✅ Máquinas y bodegas validadas (PROTECT en FK)
- ✅ Timestamps automáticos
- ✅ Cantidad de transferencia limitada por producción

---

## Pruebas Recomendadas

### Test 1: Crear Etapas
```bash
POST /api/etapas-produccion/
{
  "area": 2,
  "nombre": "Teñido",
  "orden": 1,
  "maquina": 5,
  "bodega_entrada": 10,
  "bodega_salida": 11,
  "tiempo_procesamiento_minutos": 120
}
```

### Test 2: Registrar Transferencia
```bash
POST /api/transferencias-interarea/
{
  "orden_area_origen": 5,
  "orden_area_destino": 6,
  "bodega_origen": 11,
  "bodega_destino": 12,
  "cantidad_transferida": 480.00,
  "observaciones": "Sin defectos"
}
```

### Test 3: Ver Flujo General
```bash
GET /api/etapas-produccion/?area=2
GET /api/transferencias-interarea/?orden_area_origen=5
```

---

## Archivos Modificados

### Backend
- ✅ `gestion/models.py` - EtapaProduccion, TransferenciaInterarea (existentes)
- ✅ `gestion/serializers.py` - EtapaProduccionSerializer, TransferenciaInterareaSerializer
- ✅ `gestion/views/production_views.py` - EtapaProduccionViewSet, TransferenciaInterareaViewSet
- ✅ `gestion/views/__init__.py` - Exportar nuevos ViewSets
- ✅ `gestion/urls.py` - Registrar routers

### Frontend
- ✅ `frontend/src/components/produccion/EtapasProduccion.tsx` - Nuevo
- ✅ `frontend/src/components/produccion/TransferenciasInterarea.tsx` - Existente
- ✅ `frontend/src/components/produccion/FlujoProduccion.tsx` - Nuevo
- ✅ `frontend/src/components/jefe-area/JefeAreaDashboard.tsx` - Integración

### Migraciones
- ✅ `gestion/migrations/0071_areaprocessstep_ordenproduccionsubproceso.py` - Existente
- ✅ `gestion/migrations/0072_etapaproduccion_transferenciainterarea.py` - Existente

### Documentación
- ✅ `.gemini/flujo_roles_ordenes_produccion.md` - Existente
- ✅ `.gemini/flujo_etapas_multiarea.md` - Existente
- ✅ `.gemini/integracion_multiarea.md` - **Este archivo**

---

## Notas Importantes

1. **Bodegas Intermedias**: Cada etapa dentro de un área tiene su propia bodega_entrada y bodega_salida, permitiendo bodegas intermedias

2. **Bodega Final = Bodega Entrada Siguiente**: La bodega_salida del última etapa de un área es la bodega_entrada del área siguiente

3. **Orden Separada por Área**: No es una etapa dentro de una orden, es una orden completamente nueva con su propio código

4. **Trazabilidad Completa**: Se registran todas las transferencias, bodegas, máquinas, operarios y tiempos

5. **Cascada de Áreas**: El producto fluye de bodega en bodega, etapa a etapa, área a área

---

## Próximos Pasos Opcionales

1. **Dashboard Operario**: Mostrar lotes asignados y sus etapas actuales
2. **Reportes de Flujo**: Analizar tiempo por etapa, cuellos de botella
3. **Predicciones**: Estimar cuándo se completará una orden basado en velocidad
4. **Alertas**: Notificar cuando una orden está lista para transferencia
5. **QR/Códigos**: Trackear lotes mediante códigos para auditoría

---

## Contacto y Soporte

Para preguntas sobre esta integración, consultar:
- `.gemini/flujo_etapas_multiarea.md` - Detalles técnicos del modelo
- `.gemini/flujo_roles_ordenes_produccion.md` - Detalles de roles y permisos
