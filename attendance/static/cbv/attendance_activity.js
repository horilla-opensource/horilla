if (typeof tickCheckboxes === "function") {
    tickCheckboxes();
}
function makeListUnique(list) {
    return Array.from(new Set(list));
}

if (typeof tickactivityCheckboxes === "function") {
    tickactivityCheckboxes();
}
function makeactivityListUnique(list) {
    return Array.from(new Set(list));
}

if (typeof ticklatecomeCheckboxes === "function") {
    ticklatecomeCheckboxes();
}
function makelatecomeListUnique(list) {
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

function deleteAttendanceNav() {
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
                ids = [];
                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/attendance/attendance-activity-bulk-delete/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    complete: function () {
                        refreshAttendanceListContainer();
                    },
                });
            }
        });
    }
}


function importAttendanceNav() {
    Swal.fire({
        text: i18nMessages.downloadTemplate,
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
                url: "/attendance/attendance-excel",
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
                    link.download = "attendance_excel.xlsx";
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



function importAttendanceActivity() {
    Swal.fire({
        text: i18nMessages.downloadTemplate,
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
                url: "/attendance/attendance-activity-import-excel",
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
                    link.download = "activity_excel.xlsx";
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


function bulkDeleteAttendanceNav() {
    let ids = [];

    // Collect data-ids from all three elements
    const selectors = [
        "#validateselectedInstances",
        "#overtimeselectedInstances",
        "#validatedselectedInstances"
    ];

    selectors.forEach(function (selector) {
        const element = $(selector);
        if (element.length && element.attr("data-ids")) {
            try {
                const parsedIds = JSON.parse(element.attr("data-ids"));
                if (Array.isArray(parsedIds)) {
                    ids = ids.concat(parsedIds);
                }
            } catch (e) {
                console.error("Invalid JSON in", selector);
            }
        }
    });

    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
        return;
    }

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
            $.ajax({
                type: "POST",
                url: "/attendance/attendance-bulk-delete/",
                traditional: true,
                data: {
                    csrfmiddlewaretoken: getCookie("csrftoken"),
                    ids: ids,
                },
                complete: function () {
                    refreshAttendanceListContainer();
                },
            });
        }
    });
}


function showApproveAlert(dataReqValue) {
    Swal.fire({
        title: gettext('Pending Attendance Update Request!'),
        text: gettext('An attendance request exists for updating this attendance prior to validation.'),
        icon: 'warning',
        confirmButtonText: gettext('View Request'),
        showCancelButton: true,
        cancelButtonText: i18nMessages.close,
        preConfirm: () => {
            // Redirect to the page based on dataReqValue
            localStorage.setItem("attendanceRequestActiveTab", "#tab_1")
            window.location.href = dataReqValue;

        },
    });
}


function bulkValidateTabAttendance(dataReqValue) {
    ids = [];
    ids.push($("#validateselectedInstances").attr("data-ids"));
    ids = JSON.parse($("#validateselectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: gettext("Do you really want to validate all the selected attendances?"),
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#validateselectedInstances").attr("data-ids"));
                ids = JSON.parse($("#validateselectedInstances").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/attendance/validate-bulk-attendance/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    complete: function () {
                        refreshAttendanceListContainer();
                    },
                });
            }
        });
    }
}

function otBulkValidateTabAttendance(dataReqValue) {
    ids = [];
    ids.push($("#overtimeselectedInstances").attr("data-ids"));
    ids = JSON.parse($("#overtimeselectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: gettext("No rows are selected from OT Attendances."),
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: gettext("Do you really want to approve OT for all the selected attendances?"),
            icon: "success",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#overtimeselectedInstances").attr("data-ids"));
                ids = JSON.parse($("#overtimeselectedInstances").attr("data-ids"));

                $.ajax({
                    type: "POST",
                    url: "/attendance/approve-bulk-overtime/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    complete: function () {
                        refreshAttendanceListContainer();
                    },
                });
            }
        });
    }
}

function attendanceTabReloadUrl() {
    var url = "/attendance/attendances-tab-view/";
    var form = document.getElementById("filterForm");
    if (form && typeof jQuery !== "undefined") {
        var params = jQuery(form).serialize();
        if (params) {
            url = "/attendance/attendances-tab-view/?" + params;
        }
    }
    return url;
}

function openAttendanceTabAfterInject(container) {
    var scope = container.querySelector("#attendances-tab") || container;
    setTimeout(function () {
        var btn =
            scope.querySelector(".oh-tabs__tab--active") ||
            scope.querySelector(".oh-tabs__tab") ||
            scope.querySelector("button[data-target]");
        if (btn) {
            btn.click();
        }
    }, 120);
}

var _refreshAttendanceContainerTimer = null;

function refreshAttendanceListContainerImmediately() {
    var doneMessages = function () {
        if (typeof jQuery !== "undefined" && $("#reloadMessagesButton").length) {
            $("#reloadMessagesButton").click();
        }
    };
    var listUrl = attendanceTabReloadUrl();
    if (typeof htmx !== "undefined" && typeof htmx.ajax === "function") {
        htmx
            .ajax("GET", listUrl, {
                target: "#listContainer",
                swap: "innerHTML",
                headers: {
                    "HX-Current-URL": window.location.href,
                },
            })
            .then(doneMessages)
            .catch(doneMessages);
        return;
    }
    $.ajax({
        type: "GET",
        url: listUrl,
        headers: {
            "HX-Request": "true",
            "HX-Current-URL": window.location.href,
        },
        success: function (html) {
            var c = document.getElementById("listContainer");
            if (c) {
                c.innerHTML = html;
                if (typeof htmx !== "undefined") {
                    htmx.process(c);
                }
                openAttendanceTabAfterInject(c);
            }
            doneMessages();
        },
    });
}

function refreshAttendanceListContainer() {
    if (_refreshAttendanceContainerTimer) {
        clearTimeout(_refreshAttendanceContainerTimer);
    }
    _refreshAttendanceContainerTimer = setTimeout(function () {
        _refreshAttendanceContainerTimer = null;
        refreshAttendanceListContainerImmediately();
    }, 50);
}

document.addEventListener("reloadAttendanceView", function () {
    refreshAttendanceListContainer();
});

document.body.addEventListener("htmx:afterRequest", function (evt) {
    var d = evt.detail;
    if (!d || !d.successful || !d.xhr || !d.xhr.responseURL) {
        return;
    }
    if (d.xhr.responseURL.indexOf("/attendance/approve-overtime/") === -1) {
        return;
    }
    refreshAttendanceListContainer();
});
