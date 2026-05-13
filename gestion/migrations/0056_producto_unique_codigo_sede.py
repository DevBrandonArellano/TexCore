from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0055_add_critical_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='codigo',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name='producto',
            unique_together={('codigo', 'sede')},
        ),
    ]
