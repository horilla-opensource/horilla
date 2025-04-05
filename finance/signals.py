# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.utils.timezone import now
# from .models import Finance, FinanceReport

# @receiver(post_save, sender=Finance)
# def update_finance_report(sender, instance, **kwargs):
#     today = now().date()
#     first_day_of_month = today.replace(day=1)

#     # Check if a report already exists for this month
#     report, created = FinanceReport.objects.get_or_create(
#         project=instance.project,
#         month=first_day_of_month,
#         defaults={
#             "total_expenses": instance.total_expenses(),
#             "revenue": instance.revenue,
#             "profit_or_loss": instance.profit_or_loss(),
#         }
#     )

#     # If the report exists, update it dynamically
#     if not created:
#         report.total_expenses = instance.total_expenses()
#         report.revenue = instance.revenue
#         report.profit_or_loss = instance.profit_or_loss()
#         report.save()

# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # from django.utils.timezone import now
# # from .models import Finance, FinanceReport

# # # @receiver(post_save, sender=Finance)
# # # def update_finance_report(sender, instance, **kwargs):
# # #     current_time = now()
# # #     time_bucket = current_time.replace(second=0, microsecond=0)  # Round to the nearest minute

# # #     print(f"🔔 Signal Triggered at {current_time}")  # Debugging

# # #     report, created = FinanceReport.objects.get_or_create(
# # #         project=instance.project,
# # #         month=time_bucket,  # Using minute-based timestamp
# # #         defaults={
# # #             "total_expenses": instance.total_expenses(),
# # #             "revenue": instance.revenue,
# # #             "profit_or_loss": instance.profit_or_loss(),
# # #         }
# # #     )

# # #     if not created:
# # #         print(f"✅ Updating Report for {time_bucket}")  # Debugging
# # #         report.total_expenses = instance.total_expenses()
# # #         report.revenue = instance.revenue
# # #         report.profit_or_loss = instance.profit_or_loss()
# # #         report.save()
# # from django.db.models import Sum
# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # from django.utils.timezone import now
# # from .models import (
# #     Finance, FinanceReport,  AdditionalCost, EmployeeAllocation
# # )

# # @receiver(post_save, sender=Finance)
# # def update_finance_report(sender, instance, created, **kwargs):
# #     """
# #     Signal handler to update finance reports whenever a Finance instance is saved.
# #     Creates a new FinanceReport and archives the old one to FinanceReportHistory.
# #     """
# #     try:
# #         current_time = now()
# #         minute_start = current_time.replace(second=0, microsecond=0)  # Round to minute

# #         print(f"🔔 Signal Triggered at {current_time}")  # Debugging

# #         # Fetch the latest existing FinanceReport (if any)
# #         latest_report = FinanceReport.objects.filter(project=instance.project).order_by('-timestamp').first()

# #         # Move old FinanceReport to FinanceReportHistory before creating a new one
# #         if latest_report:
# #             # The issue is in this block - wrap it with careful validation
# #             history = FinanceReportHistory(
# #                 project=instance.project,  # Use instance.project directly in case latest_report is incomplete
# #                 timestamp=latest_report.timestamp if hasattr(latest_report, 'timestamp') else current_time,
# #                 total_expenses=latest_report.total_expenses if hasattr(latest_report, 'total_expenses') else 0,
# #                 revenue=latest_report.revenue if hasattr(latest_report, 'revenue') else 0,
# #                 profit_or_loss=latest_report.profit_or_loss if hasattr(latest_report, 'profit_or_loss') else 0
# #             )
# #             history.save()
# #             print(f"📌 Old FinanceReport moved to History: {history.timestamp}")

# #         # Calculate expenses
# #         total_additional_costs = AdditionalCost.objects.filter(
# #             project=instance.project
# #         ).aggregate(Sum("cost_value"))["cost_value__sum"] or 0
        
# #         total_employee_allocations = EmployeeAllocation.objects.filter(
# #             finance=instance
# #         ).aggregate(Sum("allocated_cost"))["allocated_cost__sum"] or 0

# #         total_expenses = total_additional_costs + total_employee_allocations
        
# #         # Calculate revenue (assumed to be stored in the Finance instance)
# #         revenue = getattr(instance, 'revenue', 0)
        
# #         # Calculate profit/loss
# #         profit_or_loss = revenue - total_expenses

# #         # Create new Finance Report
# #         new_report = FinanceReport(
# #             project=instance.project,
# #             timestamp=minute_start,
# #             total_expenses=total_expenses,
# #             revenue=revenue,
# #             profit_or_loss=profit_or_loss,
# #         )
# #         new_report.save()

# #         print(f"✅ New FinanceReport Created at {minute_start}")  # Debugging
        
# #     except Exception as e:
# #         print(f"❌ Error in finance signal: {e}")
#         # You can choose to raise or not depending on your error handling needs
#         # raise