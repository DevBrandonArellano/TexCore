from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0006_etiquetadespacho'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionSistema',
            fields=[
                ('id', models.BigAutoField(auto_now_add=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=100, unique=True)),
                ('valor', models.TextField()),
                ('descripcion', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
    ]
