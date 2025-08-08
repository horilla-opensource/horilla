tickCheckboxes();

function makeListUnique(list) {
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

$(".all-employee").change(function (e) {
    var is_checked = $(this).is(":checked");
    var closest = $(this)
        .closest(".oh-sticky-table__thead")
        .siblings(".oh-sticky-table__tbody");
    if (is_checked) {
        $(closest)
            .children()
            .find(".all-employee-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(closest)
            .children()
            .find(".all-employee-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
    addingIds();
});

$(".all-employee-row").change(function () {
    var parentTable = $(this).closest(".oh-sticky-table");
    var body = parentTable.find(".oh-sticky-table__tbody");
    var parentCheckbox = parentTable.find(".all-employee");
    parentCheckbox.prop(
        "checked",
        body.find(".all-employee-row:checked").length ===
        body.find(".all-employee-row").length
    );
    addingIds();
});

function addingIds() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-employee-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makeListUnique(ids);
    selectedCount = ids.length;

    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
        $("#unselectAllEmployees").css("display", "none");
        $("#exportEmployees").css("display", "none");
        $("#selectedShow").css("display", "none");
    } else {
        $("#unselectAllEmployees").css("display", "inline-flex");
        $("#exportEmployees").css("display", "inline-flex");
        $("#selectedShow").css("display", "inline-flex");
        $("#selectedShow").text(selectedCount + " - " + i18nMessages.selected);
    }
}

function tickCheckboxes() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    var uniqueIds = makeListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedInstances").attr("data-clicked");
    if (click === "1") {
        $(".all-employee").prop("checked", true);
    }

    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;

    if (selectedCount > 0) {
        $("#unselectAllEmployees").css("display", "inline-flex");
        $("#exportEmployees").css("display", "inline-flex");
        $("#selectedShow").css("display", "inline-flex");
        $("#selectedShow").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#unselectAllEmployees").css("display", "none");
        $("#exportEmployees").css("display", "none");
        $("#selectedShow").css("display", "none");
    }
}

function selectAllEmployees() {
    var allEmployeeCount = 0;
    $("#selectedInstances").attr("data-clicked", 1);
    $("#selectedShow").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
    var filterQuery = $("#selectAllEmployees").data("pd");
    if (savedFilters && savedFilters["filterData"] !== null) {
        $.ajax({
            url: "/employee/employee-select-filter?" + filterQuery,
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;

                if (Array.isArray(employeeIds)) {
                    // Continue
                } else {
                    console.error("employee_ids is not an array:", employeeIds);
                }

                allEmployeeCount = employeeIds.length;

                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));

                count = makeListUnique(employeeIds);
                $("#unselectAllEmployees").css("display", "inline-flex");
                $("#exportEmployees").css("display", "inline-flex");
                tickCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/employee/employee-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;

                if (Array.isArray(employeeIds)) {
                    // Continue
                } else {
                    console.error("employee_ids is not an array:", employeeIds);
                }

                allEmployeeCount = employeeIds.length;

                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedInstances").attr("data-ids");
                $("#selectedInstances").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
                    )
                );

                count = makeListUnique(employeeIds);
                $("#unselectAllEmployees").css("display", "inline-flex");
                $("#exportEmployees").css("display", "inline-flex");
                tickCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllEmployees() {
    $("#selectedInstances").attr("data-clicked", 0);

    $.ajax({
        url: "/employee/employee-select",
        data: { page: "unselect", filter: "{}" },
        type: "GET",
        dataType: "json",
        success: function (response) {
            var employeeIds = response.employee_ids;

            if (Array.isArray(employeeIds)) {
                // Continue
            } else {
                console.error("employee_ids is not an array:", employeeIds);
            }

            for (var i = 0; i < employeeIds.length; i++) {
                var empId = employeeIds[i];
                $("#" + empId).prop("checked", false);
                $("#tick").prop("checked", false);
            }
            var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
            var uniqueIds = makeListUnique(ids);
            toggleHighlight(uniqueIds);

            $("#selectedInstances").attr("data-ids", JSON.stringify([]));

            count = [];
            $("#unselectAllEmployees").css("display", "none");
            $("#exportEmployees").css("display", "none");
            tickCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}

$("#exportEmployees").click(function (e) {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
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
                url: "/employee/work-info-export",
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
                    link.download = "employee_export_" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
});

$("#employeeBulkUpdateId").click(function (e) {
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        $("#bulkUpdateModal").removeClass("oh-modal--show");
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        $("#id_bulk_employee_ids").val(JSON.stringify(ids));
        $("#bulkUpdateModal").addClass("oh-modal--show");
    }
});

$("#archiveEmployees").click(function (e) {
    e.preventDefault();
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
            text: i18nMessages.confirmBulkArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();
                ids = [];
                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/employee/employee-bulk-archive?is_active=False",
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

$("#unArchiveEmployees").click(function (e) {
    e.preventDefault();
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
            text: i18nMessages.confirmBulkUnArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();

                ids = [];

                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));

                $.ajax({
                    type: "POST",
                    url: "/employee/employee-bulk-archive?is_active=True",
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

$("#deleteEmployees").click(function (e) {
    e.preventDefault();
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
                e.preventDefault();
                $("#view-container").html(`<div class="animated-background"></div>`);

                ids = [];
                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));

                $.ajax({
                    type: "POST",
                    url: "/employee/employee-bulk-delete",
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

$("#select-all-fields").change(function () {
    const isChecked = $(this).prop("checked");
    $('[name="selected_fields"]').prop("checked", isChecked);
});
