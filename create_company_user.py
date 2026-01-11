#!/usr/bin/env python
"""
Script to create company-restricted users for HRMS
Usage: python create_company_user.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from base.models import Company
from employee.models import Employee, EmployeeWorkInformation
from django.db import transaction

def create_company_user(company_id, username, email, password, first_name, last_name):
    """
    Create a company-restricted user with employee record
    """
    try:
        with transaction.atomic():
            # Get company
            company = Company.objects.get(id=company_id)
            print(f'📍 Target Company: {company.company}')
            
            # Check if user exists
            if User.objects.filter(username=username).exists():
                print(f'❌ User {username} already exists!')
                return None
            
            # Create user (NOT superuser)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,  # Can access admin
                is_superuser=False,  # Company-restricted
                first_name=first_name,
                last_name=last_name
            )
            print(f'✅ Created User: {user.username}')
            
            # Create employee
            employee = Employee.objects.create(
                employee_user_id=user,
                employee_first_name=first_name,
                employee_last_name=last_name,
                email=email,
                phone='0000000000',
                badge_id=f'{company.company[:3].upper()}-{user.id:04d}'
            )
            print(f'✅ Created Employee: {employee.get_full_name()}')
            
            # Check if work info already exists
            if not EmployeeWorkInformation.objects.filter(employee_id=employee).exists():
                work_info = EmployeeWorkInformation.objects.create(
                    employee_id=employee,
                    company_id=company,
                    email=email
                )
                print(f'✅ Assigned to Company: {company.company}')
            else:
                print(f'⚠️  Work info already exists for this employee')
            
            print()
            print('=' * 70)
            print('SUCCESS! COMPANY-RESTRICTED USER CREATED')
            print('=' * 70)
            print(f'Username: {username}')
            print(f'Password: {password}')
            print(f'Email: {email}')
            print(f'Company: {company.company} (ID: {company.id})')
            print(f'Superuser: NO ← Restricted to company only')
            print(f'Staff: YES ← Can access admin panel')
            print('=' * 70)
            print()
            print('🔒 This user CANNOT:')
            print('  • Switch to "All Company" view')
            print('  • See other companies\' data')
            print('  • Access superuser features')
            print()
            print('✅ This user CAN:')
            print('  • Login to the system')
            print(f'  • See only {company.company} data')
            print('  • Manage their company employees/data')
            print('=' * 70)
            
            return user
            
    except Company.DoesNotExist:
        print(f'❌ Company with ID {company_id} does not exist!')
        return None
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    print()
    print('=' * 70)
    print('HRMS COMPANY USER CREATOR')
    print('=' * 70)
    print()
    
    # List available companies
    print('Available Companies:')
    for company in Company.objects.all():
        print(f'  ID {company.id}: {company.company}')
    print()
    
    # Create user for Marsel Tech Labs (ID: 3)
    create_company_user(
        company_id=3,
        username='marseltech_admin',
        email='admin@marseltech.com',
        password='MarselTech123!',
        first_name='Marsel',
        last_name='Tech Admin'
    )
    
    print()
    print('💡 To create more users, edit this script and run again!')
    print()
