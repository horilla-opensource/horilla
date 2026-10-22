"""The currency shown must be the selected company's, not a leftover "$".

PayrollSettings is per company, but HorillaCompanyManager also lets the row
without a company through. A typical install ends up with two rows:

    id 1  "$"  no company   created by default_currency() on the first page
                            load, before a company was set up or selected
    id 2  "£"  Company A    created when the currency was saved in settings

Most lookups used .objects.first(), which orders by id and so returned the
"$" row: payroll pages and payslips showed "$" although the settings page
showed "£". The currency_symbol_position filter already preferred the
company's row, so the dashboard showed "£" and the two disagreed.
"""

from django.test import RequestFactory, TestCase

from base.models import Company
from base.templatetags.horillafilters import currency_symbol_position
from horilla.horilla_middlewares import set_selected_company
from payroll.context_processors import default_currency
from payroll.models.tax_models import PayrollSettings


class CurrencySettingsTests(TestCase):
    def setUp(self):
        set_selected_company(None)
        self.company = Company.objects.create(company="Company A", hq=True)
        # Created first, so it has the lower id -- as on a real install.
        self.global_row = PayrollSettings.objects.create(
            currency_symbol="$", position="postfix", company_id=None
        )
        self.company_row = PayrollSettings.objects.create(
            currency_symbol="£", position="prefix", company_id=self.company
        )

    def tearDown(self):
        set_selected_company(None)

    def _context(self):
        request = RequestFactory().get("/")
        request.session = {}
        return default_currency(request)

    def test_selected_company_uses_its_own_row(self):
        set_selected_company(str(self.company.id))

        self.assertEqual(PayrollSettings.for_selected_company(), self.company_row)
        self.assertEqual(self._context(), {"currency": "£", "position": "prefix"})
        self.assertEqual(currency_symbol_position("100"), "£ 100")

    def test_no_company_selected_uses_the_row_without_a_company(self):
        self.assertEqual(PayrollSettings.for_selected_company(), self.global_row)
        self.assertEqual(self._context(), {"currency": "$", "position": "postfix"})

    def test_all_companies_uses_the_row_without_a_company(self):
        set_selected_company("all")

        self.assertEqual(PayrollSettings.for_selected_company(), self.global_row)

    def test_no_company_selected_and_no_row_without_a_company(self):
        self.global_row.delete()

        self.assertEqual(PayrollSettings.for_selected_company(), self.company_row)

    def test_no_rows(self):
        PayrollSettings.objects.all().delete()

        self.assertIsNone(PayrollSettings.for_selected_company())
