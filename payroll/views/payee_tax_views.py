import csv
import io
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from payroll.models.tax_models import PayeeTax
from payroll.forms.payee_tax_import_form import PayeeTaxImportForm



@login_required
# @permission_required("payroll.add_filingstatus", raise_exception=True)
def import_payee_tax(request):
    """
    Upload and import PayeeTax data from CSV file.
    """
    if request.method == "POST":
        form = PayeeTaxImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]

            # Validate file type
            if not csv_file.name.endswith(".csv"):
                messages.error(request, "Please upload a valid CSV file.")
                return redirect("import-payee-tax")

            try:
                # Decode and parse CSV
                data_set = csv_file.read().decode("utf-8")
                io_string = io.StringIO(data_set)
                reader = csv.DictReader(io_string)

                # Optional: clear existing data before import
                # PayeeTax.objects.all().delete()

                count = 0
                for row in reader:
                    PayeeTax.objects.update_or_create(
                        start_range=row["start_range"],
                        end_range=row["end_range"],
                        defaults={"tax_amount": row["tax_amount"]}
                    )
                    count += 1

                messages.success(request, f"{count} tax records imported successfully!")
                return redirect("import-payee-tax")

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")

    else:
        form = PayeeTaxImportForm()

    return render(request, "payroll/tax/import_payee_tax.html", {"form": form})