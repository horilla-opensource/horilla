$(document).ready(function () {

    $("#id_period").on("change", function () {
        period_id = $(this).val();
        if (period_id === "create_new_period") {
            $.ajax({
                type: "GET",
                url: "create-period",
                success: function (response) {
                    $("#PeriodModal").addClass("oh-modal--show");
                    $("#periodModalTarget").html(response);
                },
            });
        }
    });
    $("#id_cyclic_feedback").on("change", function () {
        if (this.checked) {
            $("#cyclic_feedback_period").show();
            $("#id_cyclic_feedback_days_count").attr("required", true);
            $("#id_cyclic_feedback_period").attr("required", true);
        } else {
            $("#cyclic_feedback_period").hide();
            $("#id_cyclic_feedback_days_count").attr("required", false);
            $("#id_cyclic_feedback_period").attr("required", false);
        }
    });
});

function validateFeedBack(event) {
    var button = $(event.srcElement);
    var employeElement = $("#id_employee_id");
    var managerElement = $("#id_manager_id");
    var questionTemplateElement = $("#id_question_template_id");
    if (employeElement.val() == "") {
        $(employeElement).siblings(".errorlist").first().show();
    } else {
        $(employeElement).siblings(".errorlist").first().hide();
    }

    if (managerElement.val() == "") {
        $(managerElement).siblings(".errorlist").first().show();
    } else {
        $(managerElement).siblings(".errorlist").first().hide();
    }

    if (questionTemplateElement.val() == "") {
        $(questionTemplateElement).siblings(".errorlist").first().show();
    } else {
        $(questionTemplateElement).siblings(".errorlist").first().hide();
    }
}
