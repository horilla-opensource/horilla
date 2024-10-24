$(document).ready(function () {
    $('#id_cyclic_feedback').change()
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
});

function changeCyclicFeedback(element) {
    if (element.checked) {
        $("#cyclic_feedback_period").show();
        $("#id_cyclic_feedback_days_count").attr("required", true);
        $("#id_cyclic_feedback_period").attr("required", true);
    } else {
        $("#cyclic_feedback_period").hide();
        $("#id_cyclic_feedback_days_count").attr("required", false);
        $("#id_cyclic_feedback_period").attr("required", false);
    }
}
