from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from project.models import Project  
from employee.models import Employee  

class Finance(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="finance")

    def __str__(self):
        return f"Finance for {self.project.name}"

class EmployeeAllocation(models.Model):
    finance = models.ForeignKey(Finance, on_delete=models.CASCADE, related_name="employee_allocations")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_allocations")
    percentage_allocation = models.FloatField(default=0.0)
    allocated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.employee} - {self.percentage_allocation}%"

class CostDistribution(models.Model):
    project = models.ForeignKey(Project, related_name='distributions', on_delete=models.CASCADE)
    category = models.CharField(max_length=255)
    percentage = models.FloatField()

    def __str__(self):
        return f"{self.category}: {self.percentage}%"

class ProfitDistribution(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)  
    category = models.CharField(max_length=100)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    def allocated_profit(self, total_profit):
        """Calculate allocated profit based on percentage"""
        return (Decimal(self.percentage) / Decimal(100)) * total_profit

    def __str__(self):
        return f"{self.category} - {self.percentage}%"

class AdditionalCost(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="additional_costs")
    cost_name = models.CharField(max_length=255)
    cost_value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cost_name}: {self.cost_value}"

from django.db import models
from django.utils.timezone import now



