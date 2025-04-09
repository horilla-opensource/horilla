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
    
    model_type = request.GET.get('model', 'objective')
    if model_type == 'objective':
        data = Objective.objects.values(
            "title","managers__employee_first_name","managers__employee_last_name",
            "assignees__employee_first_name","assignees__employee_last_name",
            "key_result_id__title","key_result_id__target_value","duration_unit","duration",
            "company_id__company","key_result_id__progress_type",
        )
        DURATION_UNIT = {
            "days" :"Days",
            "months" :"Months",
            "years" :"Years",
        }
        KEY_RESULT_TARGET = {
            "%" :"%",
            "#" :"Number",
            "Currency" :"Currency",
        }
        data_list = [
            {
                "Objective":item["title"],
                "Manager":f"{item['managers__employee_first_name']} {item['managers__employee_last_name']}",
                "Assignees":f"{item['assignees__employee_first_name']} {item['assignees__employee_last_name']}",
                "Key Results":item["key_result_id__title"],
                "Key Result Target":f'{item["key_result_id__target_value"]} {KEY_RESULT_TARGET.get(item["key_result_id__progress_type"])}',
                "Duration":f'{item["duration"]} {DURATION_UNIT.get(item["duration_unit"])}',
                "Company":item["company_id__company"]

            }for item in data
        ]
    elif model_type == 'feedback':

        data_list = []

        PERIOD = {
            "days": "Days",
            "months": "Months",
            "years": "Years",
        }

        feedbacks = Feedback.objects.select_related(
            "manager_id", "employee_id", "question_template_id"
        ).prefetch_related(
            "colleague_id", "subordinate_id",
            "question_template_id__question",
            "feedback_answer__question_id",  # related_name
            "feedback_answer__employee_id",
        )

        for feedback in feedbacks:
            manager = f"{feedback.manager_id.employee_first_name} {feedback.manager_id.employee_last_name}" if feedback.manager_id else ""
            employee = f"{feedback.employee_id.employee_first_name} {feedback.employee_id.employee_last_name}" if feedback.employee_id else ""

            answerable_employees = list(feedback.colleague_id.all()) + list(feedback.subordinate_id.all())
            answerable_names = ', '.join(
                f"{e.employee_first_name} {e.employee_last_name}" for e in answerable_employees
            ) or "-"

            questions = feedback.question_template_id.question.all()

            # Fetch ALL answers for this feedback and map them grouped by question
            answers = feedback.feedback_answer.select_related("employee_id", "question_id")

            for question in questions:
                question_answers = [ans for ans in answers if ans.question_id_id == question.id]

                # If no one answered this question, still show the question
                if not question_answers:
                    data_list.append({
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
                        "Cycle Period": f"{feedback.cyclic_feedback_days_count} {PERIOD.get(feedback.cyclic_feedback_period)}" if feedback.cyclic_feedback_days_count else "-"
                    })
                else:
                    for answer in question_answers:
                        answer_value = answer.answer.get("answer") if answer.answer else ""
                        answered_by = f"{answer.employee_id.employee_first_name} {answer.employee_id.employee_last_name}" if answer.employee_id else "-"
                        data_list.append({
                            "Manager": manager,
                            "Employee": employee,
                            "Answerable Employees": answerable_names,
                            "Questions": question.question,
                            "Answer": answer_value,
                            "Answered Employees": answered_by,
                            "Status": feedback.status,
                            "Start Date": feedback.start_date,
                            "End Date": feedback.end_date,
                            "Is Cyclic": "Yes" if feedback.cyclic_feedback else "No",
                            "Cycle Period": f"{feedback.cyclic_feedback_days_count} {PERIOD.get(feedback.cyclic_feedback_period)}" if feedback.cyclic_feedback_days_count else "-"
                        })
    else:
        data_list =[]
    return JsonResponse(data_list, safe = False)
