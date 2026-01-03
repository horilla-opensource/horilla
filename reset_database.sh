#!/bin/bash
# Complete HRMS Database Reset Script
# This will give you a fresh start

echo "======================================================================="
echo "HRMS COMPLETE DATABASE RESET"
echo "======================================================================="
echo ""
echo "⚠️  WARNING: This will:"
echo "  - Delete the entire database"
echo "  - Remove all users, companies, employees, attendance, etc."
echo "  - Create a fresh database"
echo "  - You'll need to create a new superuser"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Activate virtual environment
source horillavenv/bin/activate

# Backup current database
echo "📦 Creating backup..."
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Delete database
echo "🗑️  Deleting database..."
rm db.sqlite3
echo "✅ Database deleted"

# Run migrations
echo "🔧 Creating fresh database..."
python manage.py migrate
echo "✅ Fresh database created"

echo ""
echo "======================================================================="
echo "SUCCESS! Database has been reset"
echo "======================================================================="
echo ""
echo "Next steps:"
echo "1. Create a superuser:"
echo "   python manage.py createsuperuser"
echo ""
echo "2. Start the server:"
echo "   python manage.py runserver"
echo ""
echo "3. Login and create your companies and users from scratch!"
echo "======================================================================="
