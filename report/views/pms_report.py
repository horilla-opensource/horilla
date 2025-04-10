from django.http import JsonResponse
from django.shortcuts import render

from horilla_views.cbv_methods import login_required
from pms.models import EmployeeKeyResult, Feedback, Objective


@login_required
def pms_report(request):

    if not request.user.is_superuser:
        return render(request, "404.html")
    return render(request, "report/pms_report.html")


@login_required
def pms_pivot(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    model_type = request.GET.get("model", "objective")
    if model_type == "objective":
        data = Objective.objects.values(
            "title",
            "managers__employee_first_name",
            "managers__employee_last_name",
            "assignees__employee_first_name",
            "assignees__employee_last_name",
            "key_result_id__title",
            "key_result_id__target_value",
            "duration_unit",
            "duration",
            "company_id__company",
            "key_result_id__progress_type",
            "key_result_id__duration",
            "assignees__employee_work_info__department_id__department",
            "assignees__employee_work_info__job_role_id__job_role",
            "assignees__employee_work_info__job_position_id__job_position",
        )
        DURATION_UNIT = {
            "days": "Days",
            "months": "Months",
            "years": "Years",
        }
        KEY_RESULT_TARGET = {
            "%": "%",
            "#": "Number",
            "Currency": "Currency",
        }
        data_list = [
            {
                "Objective": item["title"],
                "Objective Duration": f'{item["duration"]} {DURATION_UNIT.get(item["duration_unit"])}',
                "Manager": (
                    f"{item['managers__employee_first_name']} {item['managers__employee_last_name']}"
                    if item["managers__employee_first_name"]
                    else "-"
                ),
                "Assignees": f"{item['assignees__employee_first_name']} {item['assignees__employee_last_name']}",
                "Assignee Department": (
                    item["assignees__employee_work_info__department_id__department"]
                    if item["assignees__employee_work_info__department_id__department"]
                    else "-"
                ),
                "Assignee Job Position": (
                    item["assignees__employee_work_info__job_position_id__job_position"]
                    if item[
                        "assignees__employee_work_info__job_position_id__job_position"
                    ]
                    else "-"
                ),
                "Assignee Job Role": (
                    item["assignees__employee_work_info__job_role_id__job_role"]
                    if item["assignees__employee_work_info__job_role_id__job_role"]
                    else "-"
                ),
                "Key Results": item["key_result_id__title"],
                "Key Result Duration": f'{item["key_result_id__duration"]} {"Days"}',
                "Key Result Target": f'{item["key_result_id__target_value"]} {KEY_RESULT_TARGET.get(item["key_result_id__progress_type"])}',
                "Company": item["company_id__company"],
            }
            for item in data
        ]
    elif model_type == "feedback":

        data_list = []

        PERIOD = {
            "days": "Days",
            "months": "Months",
            "years": "Years",
        }

        feedbacks = Feedback.objects.select_related(
            "manager_id", "employee_id", "question_template_id"
        ).prefetch_related(
            "colleague_id",
            "subordinate_id",
            "question_template_id__question",
            "feedback_answer__question_id",  # related_name
            "feedback_answer__employee_id",
        )

        for feedback in feedbacks:
            manager = (
                f"{feedback.manager_id.employee_first_name} {feedback.manager_id.employee_last_name}"
                if feedback.manager_id
                else ""
            )
            employee = (
                f"{feedback.employee_id.employee_first_name} {feedback.employee_id.employee_last_name}"
                if feedback.employee_id
                else ""
            )

            answerable_employees = list(feedback.colleague_id.all()) + list(
                feedback.subordinate_id.all()
            )
            answerable_names = (
                ", ".join(
                    f"{e.employee_first_name} {e.employee_last_name}"
                    for e in answerable_employees
                )
                or "-"
            )

            questions = feedback.question_template_id.question.all()

            # Fetch ALL answers for this feedback and map them grouped by question
            answers = feedback.feedback_answer.select_related(
                "employee_id", "question_id"
            )

            for question in questions:
                question_answers = [
                    ans for ans in answers if ans.question_id_id == question.id
                ]

                # If no one answered this question, still show the question
                if not question_answers:
                    data_list.append(
                        {
                            "Manager": manager,
                            "Employee": employee,
                            "Answerable Employees": answerable_names,
                            "Questions": question.question,
                            "Answer": "",
                            "Answered Employees": "-",
                            "Status": feedback.status,
                            "Start Date": feedback.start_date,
                            "End Date": feedback.end_date,
                            "Is Cyclic": "Yes" if feedback.cyclic_feedback else "No",
                            "Cycle Period": (
                                f"{feedback.cyclic_feedback_days_count} {PERIOD.get(feedback.cyclic_feedback_period)}"
                                if feedback.cyclic_feedback_days_count
                                else "-"
                            ),
                        }
                    )
                else:
                    for answer in question_answers:
                        answer_value = (
                            answer.answer.get("answer") if answer.answer else ""
                        )
                        answered_by = (
                            f"{answer.employee_id.employee_first_name} {answer.employee_id.employee_last_name}"
                            if answer.employee_id
                            else "-"
                        )
                        data_list.append(
                            {
                                "Manager": manager,
                                "Employee": employee,
                                "Answerable Employees": answerable_names,
                                "Questions": question.question,
                                "Answer": answer_value,
                                "Answered Employees": answered_by,
                                "Status": feedback.status,
                                "Start Date": feedback.start_date,
                                "End Date": feedback.end_date,
                                "Is Cyclic": (
                                    "Yes" if feedback.cyclic_feedback else "No"
                                ),
                                "Cycle Period": (
                                    f"{feedback.cyclic_feedback_days_count} {PERIOD.get(feedback.cyclic_feedback_period)}"
                                    if feedback.cyclic_feedback_days_count
                                    else "-"
                                ),
                            }
                        )
    elif model_type == "employeeobjective":
        data = EmployeeKeyResult.objects.values(
            "key_result",
            "employee_objective_id__employee_id__employee_first_name",
            "employee_objective_id__employee_id__employee_last_name",
            "employee_objective_id__objective_id__title",
            "employee_objective_id__objective_id__duration_unit",
            "employee_objective_id__objective_id__duration",
            "start_value",
            "current_value",
            "target_value",
            "start_date",
            "end_date",
            "status",
            "progress_type",
            "employee_objective_id__employee_id__employee_work_info__department_id__department",
            "employee_objective_id__employee_id__employee_work_info__job_role_id__job_role",
            "employee_objective_id__employee_id__employee_work_info__job_position_id__job_position",
        )
        DURATION_UNIT = {
            "days": "Days",
            "months": "Months",
            "years": "Years",
        }
        KEY_RESULT_TARGET = {
            "%": "%",
            "#": "Number",
            "Currency": "Currency",
        }

        data_list = [
            {
                "Employee": f"{item['employee_objective_id__employee_id__employee_first_name']} {item['employee_objective_id__employee_id__employee_last_name']}",
                "Department": (
                    item[
                        "employee_objective_id__employee_id__employee_work_info__department_id__department"
                    ]
                    if item[
                        "employee_objective_id__employee_id__employee_work_info__department_id__department"
                    ]
                    else "-"
                ),
                "Job Position": (
                    item[
                        "employee_objective_id__employee_id__employee_work_info__job_position_id__job_position"
                    ]
                    if item[
                        "employee_objective_id__employee_id__employee_work_info__job_position_id__job_position"
                    ]
                    else "-"
                ),
                "Job Role": (
                    item[
                        "employee_objective_id__employee_id__employee_work_info__job_role_id__job_role"
                    ]
                    if item[
                        "employee_objective_id__employee_id__employee_work_info__job_role_id__job_role"
                    ]
                    else "-"
                ),
                "Employee Keyresult": item["key_result"],
                "Objective": item["employee_objective_id__objective_id__title"],
                "Objective Duration": f'{item["employee_objective_id__objective_id__duration"]} {DURATION_UNIT.get(item["employee_objective_id__objective_id__duration_unit"])}',
                "Keyresult Start Value": f'{item["start_value"]} {KEY_RESULT_TARGET.get(item["progress_type"])}',
                "Keyresult Target Value": f'{item["target_value"]} {KEY_RESULT_TARGET.get(item["progress_type"])}',
                "Keyresult Current Value": (
                    f'{item["current_value"]} {KEY_RESULT_TARGET.get(item["progress_type"])}'
                    if item["current_value"]
                    else "-"
                ),
                "Keyresult Start Date": (
                    item["start_date"] if item["start_date"] else "-"
                ),
                "Keyresult End Date": item["end_date"] if item["end_date"] else "-",
                "status": item["status"],
            }
            for item in data
        ]

    else:
        data_list = []
    return JsonResponse(data_list, safe=False)
