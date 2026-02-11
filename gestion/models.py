from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100, default='Ubicación no especificada')
    status = models.CharField(max_length=10, choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')], default='activo')

    def __str__(self):
        return self.nombre

class Area(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='areas')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'

class CustomUser(AbstractUser):
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    superior = models.ManyToManyField('self', symmetrical=False, related_name='inferiors_set', blank=True)
    bodegas_asignadas = models.ManyToManyField('Bodega', blank=True, related_name='usuarios_asignados')

    def __str__(self):
        return self.username

class Producto(models.Model):
    TIPO_CHOICES = [('hilo', 'Hilo'), ('tela', 'Tela'), ('subproducto', 'Subproducto'), ('quimico', 'Químico'), ('insumo', 'Insumo')]
    UNIDAD_CHOICES = [('kg', 'Kg'), ('metros', 'Metros'), ('unidades', 'Unidades')]
    codigo = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    unidad_medida = models.CharField(max_length=20, choices=UNIDAD_CHOICES)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    presentacion = models.CharField(max_length=100, blank=True, null=True)
    pais_origen = models.CharField(max_length=100, blank=True, null=True)
    calidad = models.CharField(max_length=100, blank=True, null=True)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"

class Batch(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    code = models.CharField(max_length=100, unique=True)
    initial_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50)
    date_received = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.code} of {self.producto.descripcion if self.producto else 'N/A'}"

class Bodega(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='bodegas')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'

class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operativa', 'Operativa'),
        ('mantenimiento', 'Mantenimiento'),
        ('inactiva', 'Inactiva')
    ]
    nombre = models.CharField(max_length=100, unique=True)
    capacidad_maxima = models.DecimalField(max_digits=10, decimal_places=2, help_text="Capacidad máxima de producción por turno (ej. kg)")
    eficiencia_ideal = models.DecimalField(max_digits=3, decimal_places=2, help_text="Eficiencia ideal (0.00 a 1.00)")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='operativa')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"

class ProcessStep(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class FormulaColor(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    nombre_color = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    productos = models.ManyToManyField(
        Producto,
        through='DetalleFormula',
        limit_choices_to={'tipo': 'quimico'}
    )

    def __str__(self):
        return self.nombre_color

class DetalleFormula(models.Model):
    formula_color = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'quimico'}
    )
    gramos_por_kilo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('formula_color', 'producto')

    def __str__(self):
        return f"{self.gramos_por_kilo} g/kg of {self.producto.descripcion} in {self.formula_color.nombre_color}"

class Cliente(models.Model):
    NIVEL_PRECIO_CHOICES = [('mayorista', 'Mayorista'), ('normal', 'Normal')]
    ruc_cedula = models.CharField(max_length=20, unique=True)
    nombre_razon_social = models.CharField(max_length=255)
    direccion_envio = models.TextField()
    nivel_precio = models.CharField(max_length=20, choices=NIVEL_PRECIO_CHOICES)
    tiene_beneficio = models.BooleanField(default=False)
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    vendedor_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_asignados')

    @property
    def saldo_pendiente(self):
        """
        Calcula dinámicamente el saldo pendiente sumando el total de todos los pedidos no pagados.
        Total de pedido = suma(peso * precio_unitario) de sus detalles.
        """
        from django.db.models import Sum, F
        total = self.pedidoventa_set.filter(esta_pagado=False).aggregate(
            total=Sum(F('detalles__peso') * F('detalles__precio_unitario'), output_field=models.DecimalField())
        )['total'] or 0
        return total

    def __str__(self):
        return self.nombre_razon_social

class OrdenProduccion(models.Model):
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('en_proceso', 'En Proceso'), ('finalizada', 'Finalizada')]
    codigo = models.CharField(max_length=100, unique=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    formula_color = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, null=True, blank=True)
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='ordenes_produccion', null=True, blank=True)
    peso_neto_requerido = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)
    inventario_descontado = models.BooleanField(default=False)
    fecha_creacion = models.DateField(auto_now_add=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"OP-{self.codigo} para {self.producto.descripcion if self.producto else 'N/A'}"

class LoteProduccion(models.Model):
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='lotes', null=True, blank=True)
    codigo_lote = models.CharField(max_length=100, unique=True)
    peso_neto_producido = models.DecimalField(max_digits=10, decimal_places=2)
    operario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.SET_NULL, null=True, related_name='lotes_producidos')
    turno = models.CharField(max_length=50)
    hora_inicio = models.DateTimeField()
    hora_final = models.DateTimeField()
    
    # Nuevos campos para Empaquetado
    peso_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tara = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unidades_empaque = models.IntegerField(default=1) # Ej: 12 rollos por caja, o 1 cono por funda
    presentacion = models.CharField(max_length=100, blank=True, null=True) # Ej: Caja, Funda, Cono

    def __str__(self):
        return self.codigo_lote
    
    def save(self, *args, **kwargs):
        # Recalcular peso neto si bruto y tara están presentes (y es lógica de empaque)
        # Nota: peso_neto_producido es el campo principal de inventario.
        # Si estamos en flujo de empaque, podríamos actualizarlo o usar uno nuevo.
        # Por ahora asumimos que el peso_neto_producido ES el resultado final validado.
        if self.peso_bruto and self.tara:
            calculated_net = self.peso_bruto - self.tara
            # self.peso_neto_producido = calculated_net # Optional: force sync
        super().save(*args, **kwargs)

class PedidoVenta(models.Model):
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('despachado', 'Despachado'), ('facturado', 'Facturado')]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    guia_remision = models.CharField(max_length=100)
    fecha_pedido = models.DateField(auto_now_add=True)
    fecha_despacho = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    esta_pagado = models.BooleanField(default=False)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True)
    vendedor_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_creados')

    def __str__(self):
        return f"Pedido {self.id} para {self.cliente.nombre_razon_social if self.cliente else 'N/A'}"

class DetallePedido(models.Model):
    pedido_venta = models.ForeignKey(PedidoVenta, on_delete=models.CASCADE, related_name='detalles', null=True, blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField()
    piezas = models.IntegerField()
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.id} para Pedido {self.pedido_venta.id if self.pedido_venta else 'N/A'}"