import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.contrib.auth.models import User
from base.models import Company
from employee.models import Employee, EmployeeWorkInformation

def cleanup():
    usernames = ['testa', 'testb']
    company_names = ['Testcompany']

    print("Starting cleanup...")

    for username in usernames:
        user = User.objects.filter(username=username).first()
        if user:
            print(f"Found user: {username}")
            # Delete related EmployeeWorkInformation first (if any)
            if hasattr(user, 'employee_get'):
                emp = user.employee_get
                if hasattr(emp, 'employee_work_info'):
                    print(f"Deleting Work Info for {username}")
                    emp.employee_work_info.delete()
                
                print(f"Deleting Employee profile for {username}")
                emp.delete()
            
            print(f"Deleting User {username}")
            user.delete()
        else:
            print(f"User {username} not found")

    for company_name in company_names:
        companies = Company.objects.filter(company=company_name)
        for company in companies:
            print(f"Deleting Company: {company.company}")
            # Check if any other employees are linked to this company?
            # For now, just force delete, assuming cascade or manual cleanup above handled it.
            # If protected, we might need to find other employees.
            company.delete()

    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
