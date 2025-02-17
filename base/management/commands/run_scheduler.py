from django.core.management.base import BaseCommand
from leave.scheduler import leave_reset  # Adjust the import based on your scheduler's location

class Command(BaseCommand):
    help = 'Manually run the leave reset scheduler'

    def handle(self, *args, **kwargs):
        leave_reset()  # Call the scheduler function
        self.stdout.write(self.style.SUCCESS('Scheduler has been run successfully.'))