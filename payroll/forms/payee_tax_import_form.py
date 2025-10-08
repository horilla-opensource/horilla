from django import forms


class PayeeTaxImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Select a CSV file",
        help_text="Max. 42 megabytes",
        required=True,
    )