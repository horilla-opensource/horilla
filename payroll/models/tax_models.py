"""
tax_models.py

This module contains the models for the tax calculation of taxable income.
"""


import math
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from base.models import Company

from payroll.models.models import FilingStatus


class PayrollSettings(models.Model):
    """
    Payroll settings model"""

    currency_symbol = models.CharField(null=True, default="$", max_length=5)
    company_id = models.ForeignKey(Company,null=True, editable=False, on_delete=models.PROTECT)
    objects = models.Manager()

    def __str__(self):
        return f"Payroll Settings {self.currency_symbol}"

    def save(self, *args, **kwargs):
        if 1 < PayrollSettings.objects.count():
            raise ValidationError("You cannot add more conditions.")

        return super().save(*args, **kwargs)


class TaxBracket(models.Model):
    """
    TaxBracket model
    """

    filing_status_id = models.ForeignKey(
        FilingStatus,
        on_delete=models.CASCADE,
        verbose_name=_("Filing status"),
    )
    min_income = models.FloatField(null=False, blank=False,verbose_name=_("Min. Income"))
    max_income = models.FloatField(null=True, blank=True,verbose_name=_("Max. Income"))
    tax_rate = models.FloatField(null=False, blank=False, default=0.0,verbose_name=_("Tax Rate"))
    objects = models.Manager()

    def __str__(self):
        if self.max_income != math.inf:
            return (
                f"{self.filing_status_id}"
                f"{self.tax_rate}% tax rate on "
                f"{self.min_income} and {self.max_income}"
            )
        return (
            f"{self.tax_rate}% tax rate on taxable income equal or above "
            f"{self.min_income} for {self.filing_status_id}"
        )

    def get_display_max_income(self):
        """
        Retrieves the maximum income.
        Returns:
            float or None: The maximum income if it is a finite value, otherwise None.
        """
        if self.max_income != math.inf:
            return self.max_income
        return None

    def clean(self):
        super().clean()

        existing_bracket = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id,
            min_income=self.min_income,
            max_income=self.max_income,
            tax_rate=self.tax_rate,
        ).exclude(pk=self.pk)
        if existing_bracket.exists():
            raise ValidationError("This tax bracket already exists")

        if self.max_income is None:
            self.max_income = math.inf

        if self.min_income >= self.max_income:
            raise ValidationError(
                {"max_income": "Maximum income must be greater than minimum income."}
            )

        existing_brackets = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id
        ).exclude(pk=self.pk)
        if existing_brackets.filter(max_income__gte=self.min_income).exists():
            tax_bracket = existing_brackets.filter(
                max_income__gte=self.min_income
            ).first()
            if tax_bracket.min_income <= self.max_income:
                raise ValidationError(
                    {
                        "min_income": format_lazy(
                            "The minimum income of this tax bracket must be \
                                greater than the maximum income of {}.",
                            tax_bracket,
                        )
                    }
                )


class FederalTax(models.Model):
    """
    FederalTax models
    """

    filing_status_id = models.ForeignKey(
        FilingStatus, models.CASCADE, verbose_name=_("Filing Status")
    )
    taxable_gross = models.IntegerField(null=False, blank=False)
