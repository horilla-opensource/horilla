$(".all-feedbacks").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-feedback-row").prop("checked", true);
    } else {
        $(".all-feedback-row").prop("checked", false);
    }
});

$(".self-feedbacks").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".self-feedback-row").prop("checked", true);
    } else {
        $(".self-feedback-row").prop("checked", false);
    }
});

$(".requested-feedbacks").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".requested-feedback-row").prop("checked", true);
    } else {
        $(".requested-feedback-row").prop("checked", false);
    }
});

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




$(document).on('click', '#archiveFeedback', function (e) {
    e.preventDefault();

    var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
    var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];

    if (announy_ids.length > 0) {
        ids = [];
    }

    if (ids.length === 0 && announy_ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                $.ajax({
                    type: "POST",
                    url: "/pms/feedback-bulk-archive?is_active=False",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                        announy_ids: JSON.stringify(announy_ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            window.location.reload();
                        } else {
                        }
                    },
                });
            }
        });
    }
});


$(document).on('click', '#UnarchiveFeedback', function (e) {
    e.preventDefault();

    var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
    var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];

    if (announy_ids.length > 0) {
        ids = [];
    }

    if (ids.length === 0 && announy_ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkUnArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                $.ajax({
                    type: "POST",
                    url: "/pms/feedback-bulk-archive?is_active=True",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                        announy_ids: JSON.stringify(announy_ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            window.location.reload();
                        } else {
                        }
                    },
                });
            }
        });
    }
});

$(document).on('click', '#deleteFeedback', function (e) {
    e.preventDefault();

    var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
    var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];

    if (ids.length === 0 && announy_ids.length === 0) {
        Swal.fire({
            text: i18nMessages.confirmBulkArchive,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkDelete,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                $.ajax({
                    type: "POST",
                    url: "/pms/feedback-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                        announy_ids: JSON.stringify(announy_ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            window.location.reload();
                        } else {
                        }
                    },
                });
            }
        });
    }
});
