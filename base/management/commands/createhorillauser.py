import uuid

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from employee.models import Employee


class Command(BaseCommand):
    help = "Creates a new user"

    def add_arguments(self, parser):
        parser.add_argument("--first_name", type=str, help="First name of the new user")
        parser.add_argument("--last_name", type=str, help="Last name of the new user")
        parser.add_argument("--username", type=str, help="Username of the new user")
        parser.add_argument("--password", type=str, help="Password for the new user")
        parser.add_argument("--email", type=str, help="Email of the new user")
        parser.add_argument("--phone", type=str, help="Phone number of the new user")

    def handle(self, *args, **options):
        if not options["first_name"]:
            first_name = input("Enter first name: ")
            last_name = input("Enter last name: ")
            username = input("Enter username: ")
            password = input("Enter password: ")
            email = input("Enter email: ")
            phone = input("Enter phone number: ")
        else:
            first_name = options["first_name"]
            last_name = options["last_name"]
            username = options["username"]
            password = options["password"]
            email = options["email"]
            phone = options["phone"]

        adminuser = User.objects.filter(username=first_name).first()
        if adminuser is not None:
            self.stdout.write(self.style.WARNING('User "%s" already exist' % adminuser))
        else:
            try:
                user = User.objects.create_superuser(
                    username=username, email=email, password=password
                )
                employee = Employee()
                employee.employee_user_id = user
                employee.employee_first_name = first_name
                employee.employee_last_name = last_name
                employee.email = email
                employee.phone = phone
                employee.save()
                bot = User.objects.filter(username="Horilla Bot").first()
                if bot is None:
                    User.objects.create_user(
                        username="Horilla Bot",
                        password=str(uuid.uuid4()),
                    )

                self.stdout.write(
                    self.style.SUCCESS('Employee "%s" created successfully' % employee)
                )
            except Exception as e:
                user.delete()
                raise CommandError('Error creating user "%s": %s' % (username, e))
