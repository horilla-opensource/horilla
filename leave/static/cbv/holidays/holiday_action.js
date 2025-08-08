function createHolidayHxValue() {
    var pd = $(".oh-pagination").attr("data-pd");
    var hxValue = JSON.stringify(pd);
    $("#holidayCreateButton").attr("hx-vals", `{"pd":${hxValue}}`);
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
        $("#unselectAllHolidays").css("display", "none  ");
        $("#selectedShowHolidays").css("display", "none");
        $("#exportHolidays").css("display", "none");
    }
}


//$(".holidaysInfoImport").click(function (e) {

function importHolidays() {
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
                url: "/configuration/holidays-excel-template",
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
}



function bulkDeleteHoliday() {
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
                    url: "/holidays-bulk-delete",
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
}
