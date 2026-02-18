#!/usr/bin/env python
"""
Delete all companies from the database for a fresh start
WARNING: This will delete all company-related data
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from base.models import Company
from django.db import transaction

def delete_all_companies():
    """
    Delete all companies from the database
    """
    print()
    print('=' * 70)
    print('DELETE ALL COMPANIES')
    print('=' * 70)
    print()
    print('⚠️  WARNING: This will delete:')
    print('  - All companies')
    print('  - All employees assigned to those companies')
    print('  - All attendance, leave, payroll records')
    print('  - All company-specific data')
    print()
    
    # Get all companies
    all_companies = Company.objects.all()
    print(f'Total companies in database: {all_companies.count()}')
    print()
    
    if all_companies.count() == 0:
        print('✅ No companies to delete. Database is clean.')
        return
    
    print('Companies to be DELETED:')
    for company in all_companies:
        print(f'  - {company.company} (ID: {company.id})')
    print()
    
    # Delete companies
    deleted_count = 0
    with transaction.atomic():
        for company in all_companies:
            company_name = company.company
            company_id = company.id
            
            try:
                company.delete()
                deleted_count += 1
                print(f'✅ Deleted company: {company_name} (ID: {company_id})')
            except Exception as e:
                print(f'❌ Error deleting {company_name}: {str(e)[:100]}')
    
    print()
    print('=' * 70)
    print(f'SUCCESS! Deleted {deleted_count} company/companies')
    print('=' * 70)
    print()
    
    # Show remaining companies
    remaining_companies = Company.objects.all()
    print(f'Remaining companies: {remaining_companies.count()}')
    if remaining_companies.count() > 0:
        for company in remaining_companies:
            print(f'  ✅ {company.company} (ID: {company.id})')
    else:
        print('  ✅ Database is clean - no companies remaining')
    print()
    print('💡 You can now create new companies from scratch!')
    print('   Go to: Settings → Base → Company → Create')
    print('=' * 70)

if __name__ == '__main__':
    delete_all_companies()
