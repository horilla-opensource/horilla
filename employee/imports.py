from import_export import resources
from employee.models import Employee

class EmployeeResource(resources.ModelResource):

    class Meta:
        model = Employee
        # exclude = ('id',)
        fields = '__all__'

    def before_save_instance(self, instance, using_transactions, dry_run):
        pass

