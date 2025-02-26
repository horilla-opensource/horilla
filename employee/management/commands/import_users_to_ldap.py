from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from ldap3 import ALL, ALL_ATTRIBUTES, Connection, Server

from employee.models import Employee

User = get_user_model()


class Command(BaseCommand):
    help = "Import users from Django to LDAP"

    def handle(self, *args, **kwargs):
        # LDAP server details
        ldap_server = "localhost"
        bind_dn = "cn=admin,dc=test,dc=com"  # Replace with your bind DN
        bind_password = "cool"  # Change to your LDAP admin password

        # Connect to the LDAP server
        server = Server(ldap_server, get_info=ALL)

        try:
            conn = Connection(server, bind_dn, bind_password, auto_bind=True)

            # Fetch all users from Django
            users = Employee.objects.all()

            for user in users:

                # Prepare user data for LDAPclear
                dn = f"uid={user.employee_user_id.username},ou=users,dc=test,dc=com"
                attributes = {
                    "objectClass": ["inetOrgPerson"],
                    "givenName": user.employee_first_name,
                    "sn": user.employee_last_name,
                    "cn": f"{user.employee_first_name} {user.employee_last_name}",
                    "uid": user.email,
                    "mail": user.email,
                    "telephoneNumber": user.phone,
                    "userPassword": user.phone,
                }

                #    Check if the user already exists in LDAP
                conn.search(
                    "ou=users,dc=test,dc=com",
                    f"(uid={user.employee_user_id.username})",
                    attributes=ALL_ATTRIBUTES,
                )

                if conn.entries:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{user.employee_first_name} {user.employee_last_name} already exists in LDAP. Skipping..."
                        )
                    )
                else:
                    # Add user to LDAP
                    if not conn.add(dn, attributes=attributes):
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to add {user.employee_first_name} {user.employee_last_name}: {conn.result}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Successfully added {user.employee_first_name} {user.employee_last_name} to LDAP."
                            )
                        )

            conn.unbind()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
