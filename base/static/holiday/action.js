function makeListUnique(list) {
    return Array.from(new Set(list));
}

tickHolidayCheckboxes();
function makeHolidayListUnique(list) {
    return Array.from(new Set(list));
}

function tickHolidayCheckboxes() {
    var ids = JSON.parse($("#selectedHolidays").attr("data-ids") || "[]");
    uniqueIds = makeHolidayListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedHolidays").attr("data-clicked");
    if (click === "1") {
        $(".all-holidays").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });

    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllHolidays").css("display", "inline-flex");
        $("#exportHolidays").css("display", "inline-flex");
        $("#selectedShowHolidays").css("display", "inline-flex");
        $("#selectedShowHolidays").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#unselectAllHolidays").css("display", "none");
        $("#selectedShowHolidays").css("display", "none");
        $("#exportHolidays").css("display", "none");
    }
}

function addingHolidayIds() {
    var ids = JSON.parse($("#selectedHolidays").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-holidays-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
                $(".all-holidays").prop("checked", false);
            }
        }
    });

    ids = makeHolidayListUnique(ids);
    toggleHighlight(ids);
    selectedCount = ids.length;

    $("#selectedHolidays").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
        $("#selectedShowHolidays").css("display", "none");
        $("#exportHolidays").css("display", "none");
        $('#unselectAllHolidays').css("display", "none");
    } else {
        $("#unselectAllHolidays").css("display", "inline-flex");
        $("#exportHolidays").css("display", "inline-flex");
        $("#selectedShowHolidays").css("display", "inline-flex");
        $("#selectedShowHolidays").text(selectedCount + " - " + i18nMessages.selected);
    }

}

function selectAllHolidays() {
    $("#selectedHolidays").attr("data-clicked", 1);
    $("#selectedShowHolidays").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];
        $.ajax({
            url: "/holiday-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
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
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedHolidays").attr("data-ids", JSON.stringify(employeeIds));

                count = makeHolidayListUnique(employeeIds);
                tickHolidayCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/holiday-select",
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

                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedHolidays").attr("data-ids");
                $("#selectedHolidays").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
                    )
                );
                count = makeHolidayListUnique(employeeIds);
                tickHolidayCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllHolidays() {
    $("#selectedHolidays").attr("data-clicked", 0);
    $.ajax({
        url: "/holiday-select",
        data: { page: "all", filter: "{}" },
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
                $(".all-holidays").prop("checked", false);
            }
            var ids = JSON.parse($("#selectedHolidays").attr("data-ids") || "[]");
            var uniqueIds = makeListUnique(ids);
            toggleHighlight(uniqueIds);
            $("#selectedHolidays").attr("data-ids", JSON.stringify([]));

            count = [];
            tickHolidayCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}

function exportHolidays() {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
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
                url: "/holiday-info-export",
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
                    link.download = "holiday_leaves" + currentDate + ".xlsx";
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

$("#bulkHolidaysDelete").click(function (e) {
    e.preventDefault();

    ids = [];
    ids.push($("#selectedHolidays").attr("data-ids"));
    ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
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
                ids.push($("#selectedHolidays").attr("data-ids"));
                ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
                var hxValue = JSON.stringify(ids);
                $("#bulkHolidaysDeleteSpan").attr("hx-vals", `{"ids":${hxValue}}`);
                $('#unselectAllHolidays').click();
                $("#bulkHolidaysDeleteSpan").click();
            }
        });
    }
});

$(document).on("click", "#holidaysInfoImport", function (e) {
    e.preventDefault();

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
                url: "holidays-excel-template",
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
                    link.download = "holiday_excel.xlsx";
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
