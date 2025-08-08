tickLeaveCheckboxes();
function makeLeaveListUnique(list) {
    return Array.from(new Set(list));
}


function tickLeaveCheckboxes() {
    var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
    uniqueIds = makeLeaveListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedLeaves").attr("data-clicked");
    if (click === "1") {
        $(".all-assigned-leaves").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllLeaves").css("display", "inline-flex");
        $("#exportAssignedLeaves").css("display", "inline-flex");
        $("#selectedShowLeaves").css("display", "inline-flex");
        $("#selectedShowLeaves").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowLeaves").css("display", "none");
        $("#exportAssignedLeaves").css("display", "none");
        $("#unselectAllLeaves").css("display", "none");
    }

}

function addingAssignedLeaveIds() {
    var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-assigned-leaves-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makeLeaveListUnique(ids);
    selectedCount = ids.length;

    $("#selectedLeaves").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
        $("#selectedShowLeaves").css("display", "none");
        $("#exportAssignedLeaves").css("display", "none");
        $("#unselectAllLeaves").css("display", "none");
    } else {
        $("#unselectAllLeaves").css("display", "inline-flex");
        $("#exportAssignedLeaves").css("display", "inline-flex");
        $("#selectedShowLeaves").css("display", "inline-flex");
        $("#selectedShowLeaves").text(selectedCount + " - " + i18nMessages.selected);
    }

}

$("#selectAllLeaves").click(function () {
    $("#selectedLeaves").attr("data-clicked", 1);
    $("#selectedShowLeaves").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];
        $.ajax({
            url: "/leave/assigned-leave-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;

                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedLeaves").attr("data-ids", JSON.stringify(employeeIds));
                count = makeLeaveListUnique(employeeIds);
                tickLeaveCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/leave/assigned-leave-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;

                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedLeaves").attr("data-ids");
                $("#selectedLeaves").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
                    )
                );
                count = makeLeaveListUnique(employeeIds);
                tickLeaveCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
});

$("#unselectAllLeaves").click(function (e) {
    $("#unselectAllLeaves").click(function () {
        $("#selectedLeaves").attr("data-clicked", 0);
        $.ajax({
            url: "/leave/assigned-leave-select",
            data: { page: "all", filter: "{}" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var employeeIds = response.employee_ids;
                for (var i = 0; i < employeeIds.length; i++) {
                    var empId = employeeIds[i];
                    $("#" + empId).prop("checked", false);
                    $(".all-assigned-leaves").prop("checked", false);
                }
                var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
                uniqueIds = makeLeaveListUnique(ids);
                toggleHighlight(uniqueIds);
                $("#selectedLeaves").attr("data-ids", JSON.stringify([]));
                count = [];
                tickLeaveCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    });
});

$("#exportAssignedLeaves").click(function (e) {
    var currentDate = new Date().toISOString().slice(0, 10);

    ids = [];
    ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
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
                url: "/leave/assigned-leaves-info-export",
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
                    link.download = "Assigned_leaves" + currentDate + ".xlsx";
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

$("#bulkAssignedLeavesDelete").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedLeaves").attr("data-ids"));
    ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
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
                ids.push($("#selectedLeaves").attr("data-ids"));
                ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/leave/assigned-leave-bulk-delete",
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
