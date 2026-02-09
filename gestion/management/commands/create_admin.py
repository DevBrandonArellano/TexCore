from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='sistemas').exists():
            User.objects.create_superuser('sistemas', 'sistemas@example.com', 'Sistemas2026*')
            self.stdout.write(self.style.SUCCESS('Successfully created new superuser "sistemas"'))
        else:
            self.stdout.write(self.style.WARNING('Superuser "sistemas" already exists.'))
