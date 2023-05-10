from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from employee.models import Employee

class Command(BaseCommand):
    help = 'Creates a new user'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        first_name = input('Enter first name: ')
        last_name = input('Enter last name: ')
        username = input('Enter username: ')
        password = input('Enter password: ')
        email = input('Enter email: ')
        phone = input('Enter phone number: ')
        try:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            employee = Employee()
            employee.employee_user_id =user
            employee.employee_first_name = first_name
            employee.employee_last_name = last_name
            employee.email = email
            employee.phone = phone
            employee.save()
            bot = User.objects.filter(username="Horilla Bot").first()
            if bot is None:
                User.objects.create_user(
                    username="Horilla Bot",
                    password="#HorillaBot!!(*&*&^(33))",
                )

            self.stdout.write(self.style.SUCCESS('Employee "%s" created successfully' % employee))
        except Exception as e:
            user.delete()
            raise CommandError('Error creating user "%s": %s' % (username, e))
