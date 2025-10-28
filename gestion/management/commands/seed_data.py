from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from gestion.models import CustomUser, Sede, Area

class Command(BaseCommand):
    help = 'Seeds the database with initial data, including users for each role.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')

        # 1. Create default Sede and Area
        sede, created = Sede.objects.get_or_create(nombre='Sede Principal')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created Sede: {sede.nombre}'))
        
        area, created = Area.objects.get_or_create(nombre='Area General', sede=sede)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created Area: {area.nombre}'))

        # 2. Create a user for each group
        password = 'password123'
        # These should match the group names created by setup_permissions.py
        group_names = ['operario', 'jefe_area', 'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas']

        for group_name in group_names:
            username = f'user_{group_name}'
            if not CustomUser.objects.filter(username=username).exists():
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    email=f'{username}@example.com',
                    first_name=group_name.replace('_', ' ').title(),
                    last_name='Test',
                    sede=sede,
                    area=area
                )
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                    self.stdout.write(self.style.SUCCESS(f'Successfully created user: {username} and added to group: {group_name}'))
                except Group.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Group {group_name} does not exist. Please run setup_permissions first.'))
            else:
                self.stdout.write(self.style.WARNING(f'User {username} already exists. Skipping.'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
