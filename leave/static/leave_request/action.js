tickLeaverequestsCheckboxes();
function makeLeaverequestsListUnique(list) {
    return Array.from(new Set(list));
}

tickUserrequestsCheckboxes();
function makeUserrequestsListUnique(list) {
    return Array.from(new Set(list));
}



// ---------------------------------------
//            LEAVE REQUEST
// ---------------------------------------

function tickLeaverequestsCheckboxes() {
    var ids = JSON.parse($("#selectedLeaverequests").attr("data-ids") || "[]");
    uniqueIds = makeLeaverequestsListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedLeaverequests").attr("data-clicked");
    if (click === "1") {
        $(".all-leave-requests").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllLeaverequests").css("display", "inline-flex");
        $("#exportLeaverequests").css("display", "inline-flex");
        $("#selectedShowLeaverequests").css("display", "inline-flex");
        $("#selectedShowLeaverequests").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowLeaverequests").css("display", "none");
        $("#exportLeaverequests").css("display", "none");
        $("#unselectAllLeaverequests").css("display", "none");
    }
}

function addingLeaverequestsIds() {
    var ids = JSON.parse($("#selectedLeaverequests").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-leave-requests-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makeLeaverequestsListUnique(ids);
    selectedCount = ids.length;

    $("#selectedLeaverequests").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
        $("#selectedShowLeaverequests").css("display", "none");
        $("#exportLeaverequests").css("display", "none");
        $("#unselectAllLeaverequests").css("display", "none");
    } else {
        $("#unselectAllLeaverequests").css("display", "inline-flex");
        $("#exportLeaverequests").css("display", "inline-flex");
        $("#selectedShowLeaverequests").css("display", "inline-flex");
        $("#selectedShowLeaverequests").text(selectedCount + " - " + i18nMessages.selected);
    }

}

function selectAllLeaverequests() {
    $("#selectedLeaverequests").attr("data-clicked", 1);
    $("#selectedShowLeaverequests").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];
        $.ajax({
            url: "/leave/leave-request-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;
                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedLeaverequests").attr(
                    "data-ids",
                    JSON.stringify(employeeIds)
                );

                count = makeLeaverequestsListUnique(employeeIds);
                tickLeaverequestsCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/leave/leave-request-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;
                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedLeaverequests").attr("data-ids");
                $("#selectedLeaverequests").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
                    )
                );
                count = makeLeaverequestsListUnique(employeeIds);
                tickLeaverequestsCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllLeaverequests() {
    $("#selectedLeaverequests").attr("data-clicked", 0);
    $.ajax({
        url: "/leave/leave-request-select",
        data: { page: "all", filter: "{}" },
        type: "GET",
        dataType: "json",
        success: function (response) {
            var employeeIds = response.employee_ids;
            for (var i = 0; i < employeeIds.length; i++) {
                var empId = employeeIds[i];
                $("#" + empId).prop("checked", false);
                $(".all-leave-requests").prop("checked", false);
            }
            var ids = JSON.parse(
                $("#selectedLeaverequests").attr("data-ids") || "[]"
            );
            uniqueIds = makeLeaverequestsListUnique(ids);
            toggleHighlight(uniqueIds);
            $("#selectedLeaverequests").attr("data-ids", JSON.stringify([]));

            count = [];
            tickLeaverequestsCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}

function exportLeaverequests() {
    var currentDate = new Date().toISOString().slice(0, 10);

    ids = [];
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
    Swal.fire({
        text: i18nMessages.downloadExcel,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/leave/leave-requests-info-export",
                data: {
                    ids: JSON.stringify(ids),
                },
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "Leave_requests" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
}

function createLeaveReport() {
    var currentDate = new Date().toISOString().slice(0, 10);
    Swal.fire({
        text: gettext("Do you wish to create a Leave Report?"),
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/leave/create-leave-report",
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/pdf",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "LeaveRequestReport" + currentDate + ".pdf";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
}

$("#leaveRequestsBulkApprove").click(function (e) {
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkApprove,
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                var hxVals = JSON.stringify(ids);
                $("#bulkApproveSpan").attr("hx-vals", `{"ids":${hxVals}}`);
                $("#bulkApproveSpan").click();
            }
        });
    }
});


$("#idBulkRejectReason").click(function (e) {
    e.preventDefault();
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
    var rejectReason = $("#id_reject_reason").val();
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: gettext("Do you want to reject the selected leave requests?"),
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                var data = JSON.stringify({ "request_ids": ids, "reason": rejectReason })
                $("#bulkRejectSpan").attr("hx-vals", data);
                $("#bulkRejectSpan").click();
            }
        });
    }
});

$("#leaveRequestBulkDelete").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedLeaverequests").attr("data-ids"));
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
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
                e.preventDefault();
                ids = [];
                ids.push($("#selectedLeaverequests").attr("data-ids"));
                ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/leave/leave-request-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload();
                        } else {
                        }
                    },
                });
            }
        });
    }
});

// ---------------------------------------
//              USER LEAVE
// ---------------------------------------

function tickUserrequestsCheckboxes() {
    var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
    uniqueIds = makeUserrequestsListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedUserrequests").attr("data-clicked");
    if (click === "1") {
        $(".all-user-requests").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllUserrequests").css("display", "inline-flex");
        $("#exportUserrequests").css("display", "inline-flex");
        $("#selectedShowUserrequests").css("display", "inline-flex");
        $("#selectedShowUserrequests").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#unselectAllUserrequests").css("display", "none");
        $("#exportUserrequests").css("display", "none");
        $("#selectedShowUserrequests").css("display", "none");
    }
}

function addingUserrequestsIds() {
    var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-user-requests-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makeUserrequestsListUnique(ids);
    selectedCount = ids.length;

    $("#selectedUserrequests").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
        $("#unselectAllUserrequests").css("display", "none");
        $("#selectedShowUserrequests").css("display", "none");
        $("#exportUserrequests").css("display", "none");
    } else {
        $("#exportUserrequests").css("display", "inline-flex");
        $("#unselectAllUserrequests").css("display", "inline-flex");
        $("#selectedShowUserrequests").css("display", "inline-flex");
        $("#selectedShowUserrequests").text(selectedCount + " - " + i18nMessages.selected);
    }
}

function selectAllUserrequests() {
    $("#selectedUserrequests").attr("data-clicked", 1);
    $("#selectedShowUserrequests").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];
        $.ajax({
            url: "/leave/user-request-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;
                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedUserrequests").attr(
                    "data-ids",
                    JSON.stringify(employeeIds)
                );

                count = makeUserrequestsListUnique(employeeIds);
                tickUserrequestsCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/leave/user-request-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;
                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedUserrequests").attr("data-ids");
                $("#selectedUserrequests").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
                    )
                );
                count = makeUserrequestsListUnique(employeeIds);
                tickUserrequestsCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllUserrequests() {
    $("#selectedUserrequests").attr("data-clicked", 0);
    $.ajax({
        url: "/leave/user-request-select",
        data: { page: "all", filter: "{}" },
        type: "GET",
        dataType: "json",
        success: function (response) {
            var employeeIds = response.employee_ids;
            for (var i = 0; i < employeeIds.length; i++) {
                var empId = employeeIds[i];
                $("#" + empId).prop("checked", false);
                $(".all-user-requests").prop("checked", false);
            }
            var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
            var uniqueIds = makeListUnique(ids);
            toggleHighlight(uniqueIds);
            $("#selectedUserrequests").attr("data-ids", JSON.stringify([]));

            count = [];
            tickUserrequestsCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}

$("#userrequestbulkDelete").click(function (e) {
    e.preventDefault();

    ids = [];
    ids.push($("#selectedUserrequests").attr("data-ids"));
    ids = JSON.parse($("#selectedUserrequests").attr("data-ids"));
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
                e.preventDefault();
                ids = [];
                ids.push($("#selectedUserrequests").attr("data-ids"));
                ids = JSON.parse($("#selectedUserrequests").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/leave/user-request-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload();
                        } else {
                        }
                    },
                });
            }
        });
    }
});
