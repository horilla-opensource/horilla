function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


$(".all-time-sheet").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-time-sheet-row").prop("checked", true);
    } else {
        $(".all-time-sheet-row").prop("checked", false);
    }
});


$("#deleteTimeSheet").click(function (e) {
    e.preventDefault();

    var checkedRows = $(".all-time-sheet-row").filter(":checked");
    if (checkedRows.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkDelete,
            icon: "error",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                var checkedRows = $(".all-time-sheet-row").filter(":checked");
                ids = [];
                checkedRows.each(function () {
                    ids.push($(this).attr("id"));
                });

                $.ajax({
                    type: "POST",
                    url: "/project/time-sheet-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload(); // Reload the current page
                        } else {
                            // console.log("Unexpected HTTP status:", jqXHR.status);
                        }
                    },
                });
            }
        });
    }
});


function deleteTimeSheet() {
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkDelete,
            icon: "error",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                // var checkedRows = $(".all-time-sheet-row").filter(":checked");
                // ids = [];
                // checkedRows.each(function () {
                //   ids.push($(this).attr("id"));
                // });

                $.ajax({
                    type: "POST",
                    url: "/project/time-sheet-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload(); // Reload the current page
                        } else {
                            // console.log("Unexpected HTTP status:", jqXHR.status);
                        }
                    },
                });
            }
        });
    }
};
