from django.db import models
from django.contrib.auth.models import AbstractUser

class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Area(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='areas')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'

class CustomUser(AbstractUser):
    # Django's AbstractUser already has:
    # username, first_name, last_name, email, password, is_active, etc.
    
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    superior = models.ManyToManyField('self', symmetrical=False, related_name='inferiors_set', blank=True)

    def __str__(self):
        return self.username

class Material(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit_of_measure = models.CharField(max_length=50) # e.g., "kg", "meters", "units"

    def __str__(self):
        return f"{self.name} ({self.unit_of_measure})"

class Batch(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='batches')
    code = models.CharField(max_length=100, unique=True)
    initial_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50) # Redundant with Material, but good for snapshot
    date_received = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.code} of {self.material.name}"

class Inventory(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('material', 'sede', 'area') # Ensure unique inventory per material, sede, and area

    def __str__(self):
        return f"{self.material.name} in {self.sede.nombre} - {self.area.nombre}: {self.quantity}"

class ProcessStep(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class MaterialMovement(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='movements')
    from_sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='material_out_sede', null=True, blank=True)
    from_area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='material_out_area', null=True, blank=True)
    to_sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='material_in_sede')
    to_area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='material_in_area')
    process_step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='material_movements')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    movement_type = models.CharField(max_length=20, choices=[('in', 'In'), ('out', 'Out'), ('transfer', 'Transfer')])
    timestamp = models.DateTimeField(auto_now_add=True)
    responsible_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='material_movements')

    def __str__(self):
        return f"Movement of {self.quantity} from {self.from_area} to {self.to_area} for Batch {self.batch.code}"

class Chemical(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit_of_measure = models.CharField(max_length=50) # e.g., "liters", "kg", "grams"

    def __str__(self):
        return f"{self.name} ({self.code})"

class Formula(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    # Many-to-many relationship with Chemical through an intermediate model (FormulaChemical)
    chemicals = models.ManyToManyField(Chemical, through='FormulaChemical')

    def __str__(self):
        return self.name

class FormulaChemical(models.Model):
    formula = models.ForeignKey(Formula, on_delete=models.CASCADE)
    chemical = models.ForeignKey(Chemical, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50) # Snapshot of unit at time of formula creation

    class Meta:
        unique_together = ('formula', 'chemical')

    def __str__(self):
        return f"{self.quantity} {self.unit_of_measure} of {self.chemical.name} in {self.formula.name}"