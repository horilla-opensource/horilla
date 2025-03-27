$(document).ready(function () {

    // this function is used to generate csrf token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }


    $select = $("#id_period").select2({
        minimumResultsForSearch: -1,
    }).on("change", function () {
        let $this = $(this)
        periodChange($this)
    });

    $select.data('select2').$selection.addClass('oh-select--lg--custom'); //adding css class for the select

    // period assigning to dates
    function periodChange(period_data) {
        var period_id = period_data.val();

        // Check if period_id is not "create_new_period" before making the request
        if (period_id !== "create_new_period") {
            $.ajax({
                url: '/pms/period-change',
                type: "POST",
                dataType: "json",
                data: JSON.stringify(period_id),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                success: (data) => {
                    // Adding data to start and end date
                    $('#id_start_date').val(data.start_date);
                    $('#id_end_date').val(data.end_date);
                },
                error: (error) => {
                    console.log('Error', error);
                }
            });
        }
    }

});
