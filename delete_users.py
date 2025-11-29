#!/usr/bin/env python
"""
Delete all users except 'admin' - Force delete with all related records
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from employee.models import Employee
from django.db import transaction

def delete_users_except_admin():
    """
    Delete all users except 'admin' - including all related records
    """
    print()
    print('=' * 70)
    print('DELETE ALL USERS EXCEPT ADMIN (WITH ALL RELATED DATA)')
    print('=' * 70)
    print()
    print('⚠️  WARNING: This will delete:')
    print('  - Users')
    print('  - Employee records')
    print('  - Attendance records')
    print('  - Leave records')
    print('  - Contracts')
    print('  - All other related data')
    print()
    
    # Get all users
    all_users = User.objects.all()
    print(f'Total users in database: {all_users.count()}')
    print()
    
    # List users to be deleted
    users_to_delete = all_users.exclude(username='admin')
    
    if users_to_delete.count() == 0:
        print('✅ No users to delete. Only "admin" exists.')
        return
    
    print('Users to be DELETED:')
    for user in users_to_delete:
        print(f'  - {user.username} ({user.email})')
    print()
    
    # Delete users with transaction
    deleted_count = 0
    with transaction.atomic():
        for user in users_to_delete:
            username = user.username
            email = user.email
            
            # Delete employee (this will cascade to related records)
            try:
                employee = Employee.objects.filter(employee_user_id=user).first()
                if employee:
                    # This will cascade delete all related records
                    employee.delete()
                    print(f'✅ Deleted employee and all related records for {username}')
            except Exception as e:
                print(f'⚠️  Warning deleting employee for {username}: {str(e)[:100]}')
            
            # Delete user
            try:
                user.delete()
                deleted_count += 1
                print(f'✅ Deleted user: {username} ({email})')
            except Exception as e:
                print(f'❌ Error deleting {username}: {str(e)[:100]}')
    
    print()
    print('=' * 70)
    print(f'SUCCESS! Deleted {deleted_count} user(s)')
    print('=' * 70)
    print()
    
    # Show remaining users
    remaining_users = User.objects.all()
    print(f'Remaining users: {remaining_users.count()}')
    for user in remaining_users:
        print(f'  ✅ {user.username} ({user.email}) - Superuser: {user.is_superuser}')
    print()
    print('💡 You can now create new users from scratch!')
    print('=' * 70)

if __name__ == '__main__':
    delete_users_except_admin()
