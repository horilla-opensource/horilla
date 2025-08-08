function makeEmpListUnique(list) {
    return Array.from(new Set(list));
}

function makePayslipListUnique(list) {
    return Array.from(new Set(list));
}

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

function bulkSendViaMail() {
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    maildata = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (maildata.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: gettext("Do you want to send the payslip by mail?"),
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {

                // ids.push($("#selectedInstances").attr("data-ids"));
                //ids = JSON.parse($("#selectedInstances").attr("data-ids"));

                $.ajax({

                    type: "GET",
                    url: "/payroll/send-slip",
                    data: { id: maildata },
                    traditional: true,
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload();
                        }
                    },

                });
            }
        });
    }

}

function payslipBulkDelete() {
    var checkedRows = $(".payslip-checkbox").filter(":checked");
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if ((ids.length === 0) & (checkedRows.length === 0)) {
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
                if (ids.length === 0) {
                    e.preventDefault();
                    ids = [];
                    checkedRows.each(function () {
                        ids.push($(this).attr("id"));
                    });
                } else if (checkedRows.length === 0) {
                    ids = [];
                    ids.push($("#selectedInstances").attr("data-ids"));
                    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                }
                $.ajax({
                    type: "POST",
                    url: "/payroll/payslip-bulk-delete",
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
}
