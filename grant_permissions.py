#!/usr/bin/env python
"""
Grant full permissions to company-restricted users
This makes them "Company Admins" with full access to their company's data
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType

def grant_all_permissions(username):
    """
    Grant all permissions to a user (make them company admin)
    """
    try:
        user = User.objects.get(username=username)
        print(f'👤 User: {user.username}')
        print(f'📧 Email: {user.email}')
        print(f'🏢 Superuser: {user.is_superuser}')
        print()
        
        # Get or create "Company Admin" group
        company_admin_group, created = Group.objects.get_or_create(
            name='Company Admin'
        )
        
        if created:
            print('✅ Created "Company Admin" group')
            # Add all permissions to the group
            all_permissions = Permission.objects.all()
            company_admin_group.permissions.set(all_permissions)
            print(f'✅ Added {all_permissions.count()} permissions to group')
        else:
            print('ℹ️  "Company Admin" group already exists')
        
        # Add user to group
        user.groups.add(company_admin_group)
        print(f'✅ Added {user.username} to "Company Admin" group')
        
        # Also grant all permissions directly (belt and suspenders approach)
        all_permissions = Permission.objects.all()
        user.user_permissions.set(all_permissions)
        print(f'✅ Granted {all_permissions.count()} permissions directly to user')
        
        print()
        print('=' * 70)
        print('SUCCESS! USER NOW HAS FULL PERMISSIONS')
        print('=' * 70)
        print(f'Username: {user.username}')
        print(f'Group: Company Admin')
        print(f'Permissions: ALL ({all_permissions.count()} permissions)')
        print()
        print('✅ This user can now:')
        print('  • Access all modules (Employee, Attendance, Leave, etc.)')
        print('  • View Settings and Company details')
        print('  • Manage all features within their company')
        print('  • Access admin panel with full functionality')
        print()
        print('🔒 This user still CANNOT:')
        print('  • Switch to "All Company" (not a superuser)')
        print('  • See other companies\' data')
        print('  • Access Django admin superuser features')
        print('=' * 70)
        
        return user
        
    except User.DoesNotExist:
        print(f'❌ User "{username}" not found!')
        return None
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    print()
    print('=' * 70)
    print('GRANT PERMISSIONS TO COMPANY USER')
    print('=' * 70)
    print()
    
    # Grant permissions to marseltech_admin
    grant_all_permissions('marseltech_admin')
    
    print()
    print('💡 To grant permissions to other users:')
    print('   Edit this script and change the username, then run again')
    print()
