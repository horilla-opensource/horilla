from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from base.models import Company
from employee.models import Employee, EmployeeWorkInformation
from django.urls import reverse

class DataIsolationTest(TestCase):
    def setUp(self):
        # Create Company A
        self.company_a = Company.objects.create(company="Company A")
        self.user_a = User.objects.create_user(username="user_a", password="password")
        self.employee_a = Employee.objects.create(
            employee_user_id=self.user_a,
            employee_first_name="User",
            employee_last_name="A",
            email="usera@example.com",
            phone="1234567890"
        )
        # Update the automatically created Work Info
        work_info_a = self.employee_a.employee_work_info
        work_info_a.company_id = self.company_a
        work_info_a.save()

        # Create Company B
        self.company_b = Company.objects.create(company="Company B")
        self.user_b = User.objects.create_user(username="user_b", password="password")
        self.employee_b = Employee.objects.create(
            employee_user_id=self.user_b,
            employee_first_name="User",
            employee_last_name="B",
            email="userb@example.com",
            phone="0987654321"
        )
        # Update the automatically created Work Info
        work_info_b = self.employee_b.employee_work_info
        work_info_b.company_id = self.company_b
        work_info_b.save()
        
        # Assign 'view_company' permission to both users so they can access the view
        permission = Permission.objects.get(codename="view_company")
        self.user_a.user_permissions.add(permission)
        self.user_b.user_permissions.add(permission)

        self.client = Client()

    def test_company_view_isolation(self):
        """
        Test that a user can ONLY see their own company in the company_view.
        """
        # Login as User A
        self.client.login(username="user_a", password="password")
        
        response = self.client.get(reverse("company-view"))
        self.assertEqual(response.status_code, 200)
        
        # Check that Company A is in the context/content
        self.assertContains(response, "Company A")
        
        # Check that Company B is NOT in the context/content
        self.assertNotContains(response, "Company B")
        
        # Verify context data explicitly
        companies = response.context["companies"]
        self.assertTrue(companies.filter(id=self.company_a.id).exists())
        self.assertFalse(companies.filter(id=self.company_b.id).exists())

    def test_cross_company_access_denied(self):
        """
        Test that User A cannot access Company B's data (simulated).
        """
        # This is a placeholder for future views. 
        # For now, we verified the main vulnerability in company_view.
        pass
