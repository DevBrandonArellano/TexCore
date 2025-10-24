from django.core.management.base import BaseCommand
from django.db import transaction
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

        # 2. Create a user for each role
        password = 'password123'
        roles = CustomUser.ROLE_CHOICES

        for role_value, role_name in roles:
            username = f'user_{role_value}'
            if not CustomUser.objects.filter(username=username).exists():
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    email=f'{username}@example.com',
                    first_name=role_name,
                    last_name='Test',
                    role=role_value,
                    sede=sede,
                    area=area
                )
                self.stdout.write(self.style.SUCCESS(f'Successfully created user: {username} (Role: {role_name})'))
            else:
                self.stdout.write(self.style.WARNING(f'User {username} already exists. Skipping.'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
