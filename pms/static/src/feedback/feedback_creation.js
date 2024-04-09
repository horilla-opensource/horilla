$(document).ready(function () {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(
                        cookie.substring(name.length + 1)
                    );
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrf_token = getCookie("csrftoken");
    var employee_id = $("#id_employee_id").val();

    // this function is used to populate key-result in feedback form
    var $select = $("#id_employee_id")
        .select2({})
        .on("change", function (e) {
            const employee_id = $(this).val();
            userKeyResults(employee_id, csrf_token);
        });

    $select.data("select2").$selection.addClass("oh-select--lg--custom"); //adding css class for the select

    // this condition is used when the form is returned with an errror
    if (employee_id) {
        userKeyResults(employee_id, csrf_token);
    }

    // this section is ajax passing of employee id  passing
    function userKeyResults(employee_id, csrf_token) {
        $.ajax({
            url: "/pms/feedback-creation-ajax",
            type: "POST",
            dataType: "json",
            data: { employee_id: employee_id, csrfmiddlewaretoken: csrf_token },
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            success: (data) => {
                // data is a dictionary containt a list of key results object
                //  this condition is used assign key result of this employee
                $("#id_employee_key_results_id").find("option").remove();
                $("#id_employee_key_results_id").removeAttr("required");
                var key_results = data.key_results;
                var reporting_manager = data.reporting_manager;
                $.each(key_results, function (key, value) {
                    // looping all key_results
                    var options = $(`<option value=" ${value.id}">`).text(
                        value.key_result
                    );
                    $("#id_employee_key_results_id")
                        .append(options)
                        .trigger("change");
                });

                if (reporting_manager) {
                    //  assigning the reporting manager of the employee
                    var options = $(
                        `<option value=" ${reporting_manager.id}" selected="selected">`
                    ).text(
                        `${reporting_manager.employee_first_name}${reporting_manager.employee_last_name}`
                    );
                    $("#id_manager_id").append(options).trigger("change");
                } else {
                    var options = $(
                        `<option value=" " selected="selected">`
                    ).text(`---------`);
                    $("#id_manager_id").append(options).trigger("change");
                }
            },
            error: (error) => {
                console.log(error);
            },
        });
    }

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
