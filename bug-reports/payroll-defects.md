# Horilla HRMS: Payroll Defect Audit Log

This document compiles five verified, highly reproducible payroll defects discovered within the Horilla HRMS codebase. Each report details the component, severity, priority, replication steps, root cause analysis, precise code references, and recommended remediations.

---

## Defect 1: Server Crash (Django `NoReverseMatch`) on Single Payslip Submission Redirect

*   **Defect ID:** HOR-PAY-001
*   **Title:** Server Crash (Django `NoReverseMatch`) on Single Payslip Submission Redirect
*   **Severity:** Blocker / Critical (Crashes the application server session immediately upon submission, preventing users from creating individual payslips through the UI)
*   **Priority:** High
*   **Component:** `payroll` (Views & URL routing integration)
*   **Reproduction Steps:**
    1. Log in to the Horilla HRMS application as an Administrator or Payroll Manager.
    2. Navigate to **Payroll** -> **Payslips**.
    3. Click on the **Create Payslip** button (which opens a modal or directly navigates to `/payroll/create-payslip`).
    4. Select an active employee (e.g., Michael Brown) from the dropdown list.
    5. Fill in the **Start Date** and **End Date** (e.g., `2026-06-01` and `2026-06-30`).
    6. Click **Save** to submit the form.
    7. Observe the HTTP 500 error response and check the Django traceback/log.
*   **Expected Result:** The payslip should be generated and stored in the database. The application should redirect the user to the detail view of the newly created payslip (e.g., `/view-payslip/<payslip_id>/`), accompanied by a success notification.
*   **Actual Result:** The server encounters a `NoReverseMatch` exception and returns a `500 Internal Server Error` response. The redirection fails entirely.
*   **Root Cause Analysis:** 
    In the view function `create_payslip` in [payroll/views/component_views.py](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L939-L944), after saving the payslip, it attempts to redirect the user using:
    ```python
    return HorillaRedirect(
        request,
        redirect_to=reverse(
            "view-payslip", kwargs={"payslip_id": payslip.pk}
        ),
    )
    ```
    However, the named URL route `"view-payslip"` is defined in [payroll/urls/component_urls.py](file:///C:/purabh/horilla-hr/payroll/urls/component_urls.py#L89) as:
    ```python
    path("view-payslip/", component_views.view_payslip, name="view-payslip"),
    ```
    This route is parameterless and maps to a general list view of payslips. Since it does not accept any parameters, passing the keyword argument `kwargs={"payslip_id": payslip.pk}` to `reverse()` causes a `NoReverseMatch` exception. The correct URL route name for the detailed payslip view is `"view-created-payslip"`, defined in [payroll/urls/urls.py](file:///C:/purabh/horilla-hr/payroll/urls/urls.py#L73-L77) as:
    ```python
    path(
        "view-payslip/<int:payslip_id>/",
        views.view_created_payslip,
        name="view-created-payslip",
        kwargs={"model": Payslip},
    ),
    ```
*   **Code Reference:**
    *   View implementation: [payroll/views/component_views.py:L939-L944](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L939-L944)
    *   Parameterless URL definition: [payroll/urls/component_urls.py:L89](file:///C:/purabh/horilla-hr/payroll/urls/component_urls.py#L89)
    *   Detail URL definition: [payroll/urls/urls.py:L73-L77](file:///C:/purabh/horilla-hr/payroll/urls/urls.py#L73-L77)
*   **Recommended Fix:** Change `"view-payslip"` to `"view-created-payslip"` in the redirection target in [payroll/views/component_views.py](file:///C:/purabh/horilla-hr/payroll/views/component_views.py):
    ```diff
    -                 return HorillaRedirect(
    -                     request,
    -                     redirect_to=reverse(
    -                         "view-payslip", kwargs={"payslip_id": payslip.pk}
    -                     ),
    -                 )
    +                 return HorillaRedirect(
    +                     request,
    +                     redirect_to=reverse(
    +                         "view-created-payslip", kwargs={"payslip_id": payslip.pk}
    +                     ),
    +                 )
    ```

---

## Defect 2: Scope Mutation / Variable Pollution of `start_date` in Bulk Payslip Generation Loop

*   **Defect ID:** HOR-PAY-002
*   **Title:** Scope Mutation / Variable Pollution of `start_date` in Bulk Payslip Generation Loop Underpaying Subsequent Employees
*   **Severity:** Critical (Causes severe financial calculation errors, incorrect pay calculations, and loss of computed basic pay for employees processed after the first one)
*   **Priority:** High
*   **Component:** `payroll` (Views & Business Logic)
*   **Reproduction Steps:**
    1. Set up two active employees with active contracts:
        *   **Employee A:** Contract starts on `2026-06-15`.
        *   **Employee B:** Contract starts on `2026-06-01`.
    2. Navigate to **Payroll** -> **Payslips** -> **Bulk Payslip** (or `/payroll/generate-payslip`).
    3. Select both **Employee A** and **Employee B** in the employee selection dropdown.
    4. Set the payroll **Start Date** to `2026-06-01` and **End Date** to `2026-06-30`.
    5. Submit the form to generate payslips in bulk.
    6. Audit the generated payslip details and date ranges for both employees.
*   **Expected Result:**
    *   Employee A's payslip should be calculated from `2026-06-15` (since their contract starts later than the requested start date).
    *   Employee B's payslip should be calculated from `2026-06-01` (since their contract was already active on `2026-06-01`).
*   **Actual Result:**
    *   Employee A's payslip is correctly calculated from `2026-06-15`.
    *   Employee B's payslip is incorrectly calculated from `2026-06-15` instead of `2026-06-01`, leading to a deduction of 14 days of pay.
*   **Root Cause Analysis:** 
    In the view function `generate_payslip` in [payroll/views/component_views.py](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L763-L774), the variable `start_date` is read from the submitted form *outside* the employee loop:
    ```python
    start_date = form.cleaned_data["start_date"]
    ```
    Inside the loop, the contract start date is checked, and if the contract starts *after* `start_date`, the code modifies the local `start_date` variable directly:
    ```python
    for employee in employees:
        ...
        if start_date < contract.contract_start_date:
            start_date = contract.contract_start_date
        payslip = payroll_calculation(employee, start_date, end_date)
    ```
    Because Python does not have block scope (only function scope), mutating `start_date` within the loop mutates the variable for all subsequent iterations. Therefore, once the loop processes an employee with a later contract start date, all subsequent employees will use that mutated, later date instead of the requested bulk start date.
*   **Code Reference:**
    *   Scope mutation: [payroll/views/component_views.py:L763-L774](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L763-L774)
*   **Recommended Fix:** Ensure `start_date` is reset to the initial user-requested start date at the beginning of each iteration:
    ```diff
    -             start_date = form.cleaned_data["start_date"]
    +             requested_start_date = form.cleaned_data["start_date"]
                  end_date = form.cleaned_data["end_date"]
     
                  group_name = form.cleaned_data["group_name"]
                  for employee in employees:
    +                 start_date = requested_start_date
                      contract = Contract.objects.filter(
                          employee_id=employee, contract_status="active"
                      ).first()
    ```

---

## Defect 3: Backend Server Crash (`TypeError`) on Payslip Calculation for Employee with Inactive/Missing Contract

*   **Defect ID:** HOR-PAY-003
*   **Title:** Backend Server Crash (`TypeError`) on Payslip Calculation for Employee with Missing/Inactive Contract
*   **Severity:** High (Causes server-side crash when attempting calculations for employees without active contracts)
*   **Priority:** High
*   **Component:** `payroll` (Wage Computation Orchestrator)
*   **Reproduction Steps:**
    1. Create or select an employee who does not have any active contract (e.g., contract status is "draft", "terminated", or no contract exists at all).
    2. Navigate to **Payroll** -> **Payslips** -> **Create Payslip** (or trigger a POST request to `/payroll/create-payslip`).
    3. Select the contractless employee.
    4. Specify any date range and click **Save**.
    5. Check the server response and the traceback in the console.
*   **Expected Result:** The system should reject the request gracefully, displaying a user-friendly validation error such as "This employee does not have an active contract during the selected period."
*   **Actual Result:** The server crashes with `TypeError: 'NoneType' object is not subscriptable` in `payroll_calculation`.
*   **Root Cause Analysis:** 
    The orchestrator view function `payroll_calculation` in [payroll/views/component_views.py](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L124-L125) calls `compute_salary_on_period(employee, start_date, end_date)`.
    Inside `compute_salary_on_period` in [payroll/methods/methods.py](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L508-L509), the function filters for active contracts. If no active contract is found, it returns `None`:
    ```python
    contract = Contract.objects.filter(
        employee_id=employee, contract_status="active"
    ).first()
    if contract is None:
        return contract
    ```
    The orchestrator view then immediately attempts to access keys from the result:
    ```python
    basic_pay_details = compute_salary_on_period(employee, start_date, end_date)
    contract = basic_pay_details["contract"]
    ```
    Since `basic_pay_details` is `None`, this indexing operation raises a `TypeError` and crashes the thread.
*   **Code Reference:**
    *   View orchestrator: [payroll/views/component_views.py:L124-L125](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L124-L125)
    *   Helper method: [payroll/methods/methods.py:L508-L509](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L508-L509)
*   **Recommended Fix:** Raise a standard validation error inside `payroll_calculation` or handle `None` values gracefully before indexing:
    ```python
    basic_pay_details = compute_salary_on_period(employee, start_date, end_date)
    if basic_pay_details is None:
        raise ValidationError(_("An active contract is required to compute payroll for this employee."))
    contract = basic_pay_details["contract"]
    ```

---

## Defect 4: Stubbed `find_half_day_leaves()` Function Causing Incorrect Leave / LOP Calculation

*   **Defect ID:** HOR-PAY-004
*   **Title:** Stubbed `find_half_day_leaves()` Function Causing Incorrect Leave / LOP Calculation
*   **Severity:** Medium (Causes incorrect leave counts and Loss of Pay (LOP) calculations for half-day absences, leading to payroll inaccuracies)
*   **Priority:** High
*   **Component:** `payroll` (Leave & Absences Integration)
*   **Reproduction Steps:**
    1. Create an unpaid leave type (or a paid leave type) in the Leave module.
    2. Log a half-day leave request for an employee within a pay period (e.g., a half-day unpaid leave request).
    3. Approve the half-day leave request.
    4. Navigate to **Payroll** -> **Payslips** and generate a payslip for that employee covering the period of the leave.
    5. Audit the calculated `paid_leaves`, `unpaid_leaves`, and the corresponding basic salary / Loss of Pay (LOP) deduction.
*   **Expected Result:** The half-day leave should be computed as `0.5` days. The total unpaid/paid leave days should accurately reflect this fractional value, and the salary should be deducted by `0.5 * daily_rate` for unpaid half-day leaves.
*   **Actual Result:** The half-day leave is treated as a full day (1.0 day) if the date is in the leave query dates list. The helper returns zero for half-day leave variables, resulting in incorrect calculations.
*   **Root Cause Analysis:** 
    The function `find_half_day_leaves()` in [payroll/methods/methods.py](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L199-L223) is completely stubbed out:
    ```python
    def find_half_day_leaves():
        paid_queryset = []
        unpaid_queryset = []
        paid_leaves = list(filter(None, list(set(paid_queryset))))
        unpaid_leaves = list(filter(None, list(set(unpaid_queryset))))
        ...
        paid_half = len(paid_leaves) * 0.5
        unpaid_half = len(unpaid_leaves) * 0.5
        queryset = paid_leaves + unpaid_leaves
        total_leaves = len(queryset) * 0.50
        return {
            "half_day_query_set": queryset,
            "half_day_leaves": total_leaves,
            "half_paid_leaves": paid_half,
            "half_unpaid_leaves": unpaid_half,
        }
    ```
    It takes no parameters, runs no database queries, and returns `0` counts for all half-day parameters. 
    In `get_leaves()` in [payroll/methods/methods.py](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L92-L100), this function is called:
    ```python
    half_day_data = find_half_day_leaves()
    unpaid_half = half_day_data["half_unpaid_leaves"]
    paid_half = half_day_data["half_paid_leaves"]
    ...
    paid_leave = len(paid_leave_dates) - paid_half
    unpaid_leave = len(unpaid_leave_dates) - unpaid_half
    ```
    Because `unpaid_half` and `paid_half` are always `0`, the half-day leave dates are counted as full-day absences (1.0 day instead of 0.5 day), resulting in double deductions (over-penalization) for unpaid leaves or full payment credit instead of half credit.
*   **Code Reference:**
    *   Definition: [payroll/methods/methods.py:L199-L223](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L199-L223)
    *   Call site: [payroll/methods/methods.py:L92](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L92)
*   **Recommended Fix:** Implement actual database query logic to fetch half-day leaves for the employee during the given start and end date range. The signature should accept parameters:
    ```python
    def find_half_day_leaves(employee, start_date, end_date):
        # Query approved half-day leave requests for the employee and date range
        # and compute actual counts
        ...
    ```
    And pass `employee`, `start_date`, and `end_date` at the call site:
    ```python
    half_day_data = find_half_day_leaves(employee, start_date, end_date)
    ```

---

## Defect 5: UI/State Mismatch: Client-Side GET Submission Fallback on Direct URL Access of Create Payslip

*   **Defect ID:** HOR-PAY-005
*   **Title:** UI/State Mismatch: Client-Side GET Submission Fallback on Direct URL Access of Create Payslip
*   **Severity:** Medium (Causes silent submission failures and UI state confusion where the form parameters are leaked into the URL and no records are created)
*   **Priority:** Medium
*   **Component:** `payroll` (Templates & View Integration)
*   **Reproduction Steps:**
    1. Open a new browser window or tab.
    2. Navigate directly to `http://127.0.0.1:8000/payroll/create-payslip`.
    3. Observe that the page loads as a bare HTML form fragment (no styling or main navigation header is present because it is designed to be rendered within an HTMX modal).
    4. Select an employee, fill in start and end dates, and click the **Save** button.
    5. Observe the browser's address bar and the page state.
*   **Expected Result:** Either the direct GET request should be rejected (redirected to the main payroll list view), or the form should handle standard POST submissions gracefully and redirect.
*   **Actual Result:** The browser performs a `GET` submission, appending the form parameters to the URL query string (e.g., `/payroll/create-payslip?csrfmiddlewaretoken=...&employee_id=1&start_date=2026-06-01&end_date=2026-06-30`). The page reloads, showing the same bare form with no payslips generated and no error message.
*   **Root Cause Analysis:** 
    The template file [payroll/templates/payroll/payslip/create_payslip.html](file:///C:/purabh/horilla-hr/payroll/templates/payroll/payslip/create_payslip.html#L11-L12) is a partial HTMX template. It defines the form as:
    ```html
    <form hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget" class="oh-profile-section pt-1"
        id="payslipCreateForm">
    ```
    It relies on the HTMX library (`hx-post`) to issue an AJAX POST request.
    However, this file is a partial template and does not include parent layouts or the HTMX library script tags. When accessed directly via its GET route, the browser renders it without HTMX.
    When the user submits the form, since there is no `method="POST"` attribute on the `<form>` tag, the browser falls back to the default HTML standard form submission method, which is `GET`.
    The browser sends a GET request to the same URL (`/payroll/create-payslip`) with the form inputs as query parameters.
    The view handling `/payroll/create-payslip` (`create_payslip` in `payroll/views/component_views.py`) only processes data when `request.method == "POST"`. For `GET` requests, it simply renders the template again, completely ignoring the submitted parameters.
*   **Code Reference:**
    *   Form template definition: [payroll/templates/payroll/payslip/create_payslip.html:L11-L12](file:///C:/purabh/horilla-hr/payroll/templates/payroll/payslip/create_payslip.html#L11-L12)
    *   GET handling in view: [payroll/views/component_views.py:L946-L950](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L946-L950)
*   **Recommended Fix:** 
    Add a `method="post"` attribute to the `<form>` element to ensure standard HTML submissions fallback to POST instead of GET. In the view, detect if the request is an HTMX request (e.g., using `request.headers.get('HX-Request')`). If a direct non-HTMX GET request is received, redirect the user to the main payslip view `/payroll/view-payslip/` so they access the form through the modal interface as designed.
    ```diff
    -     <form hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget" class="oh-profile-section pt-1"
    -         id="payslipCreateForm">
    +     <form method="post" hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget" class="oh-profile-section pt-1"
    +         id="payslipCreateForm">
    ```
