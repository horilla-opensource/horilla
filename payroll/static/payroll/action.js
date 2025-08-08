tickContractCheckboxes();

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


// -------------------------------
//        PAYSLIP SECTION
// -------------------------------

$("#select-all-fields").change(function () {
    const isChecked = $(this).prop("checked");
    $('[name="selected_fields"]').prop("checked", isChecked);
});

function addingPayslipIds() {
    var ids = JSON.parse($("#selectedPayslip").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-payslip-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makePayslipListUnique(ids);
    selectedCount = ids.length;
    $("#selectedPayslip").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
        $("#unselectAllPayslip").css("display", "none");
        $("#exportPayslips").css("display", "none");
        $("#selectedSlipShow").css("display", "none");
    } else {
        $("#unselectAllPayslip").css("display", "inline-flex");
        $("#exportPayslips").css("display", "inline-flex");
        $("#selectedSlipShow").css("display", "inline-flex");
        $("#selectedSlipShow").text(selectedCount + " - " + i18nMessages.selected);
    }

}

$(".all-payslip-row").change(function () {
    if ($(".all-payslip").is(":checked")) {
        $(".all-payslip").prop("checked", false);
    }
    addingPayslipIds();
});

function tickPayslipCheckboxes() {
    var ids = JSON.parse($("#selectedPayslip").attr("data-ids") || "[]");
    uniqueIds = makePayslipListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedPayslip").attr("data-clicked");
    if (click === "1") {
        $(".all-payslip").prop("checked", true);
    }

    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });

    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllPayslip").css("display", "inline-flex");
        $("#exportPayslips").css("display", "inline-flex");
        $("#selectedSlipShow").css("display", "inline-flex");
        $("#selectedSlipShow").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#unselectAllPayslip").css("display", "none");
        $("#exportPayslips").css("display", "none");
        $("#selectedSlipShow").css("display", "none");
    }
}

function selectAllPayslip() {
    var allPayslipCount = 0;
    $("#selectedPayslip").attr("data-clicked", 1);
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];

        $.ajax({
            url: "/payroll/payslip-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var payslipIds = response.payslip_ids;

                if (Array.isArray(payslipIds)) {
                    // Continue
                } else {
                    console.error("employee_ids is not an array:", payslipIds);
                }

                allPayslipCount = payslipIds.length;

                for (var i = 0; i < payslipIds.length; i++) {
                    var empId = payslipIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedPayslip").attr("data-ids");
                $("#selectedPayslip").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...payslipIds, ...JSON.parse(previousIds)]))
                    )
                );

                count = makePayslipListUnique(payslipIds);
                tickPayslipCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/payroll/payslip-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var payslipIds = response.payslip_ids;

                if (Array.isArray(payslipIds)) {
                    // Continue
                } else {
                    console.error("employee_ids is not an array:", payslipIds);
                }

                allPayslipCount = payslipIds.length;

                for (var i = 0; i < payslipIds.length; i++) {
                    var empId = payslipIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedPayslip").attr("data-ids", JSON.stringify(payslipIds));

                count = makePayslipListUnique(payslipIds);
                tickPayslipCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllPayslip() {
    $("#selectedPayslip").attr("data-clicked", 0);

    $.ajax({
        url: "/payroll/payslip-select",
        data: { page: "all", filter: "{}" },
        type: "GET",
        dataType: "json",
        success: function (response) {
            var payslipIds = response.payslip_ids;

            if (Array.isArray(payslipIds)) {
                // Continue
            } else {
                console.error("employee_ids is not an array:", payslipIds);
            }

            for (var i = 0; i < payslipIds.length; i++) {
                var empId = payslipIds[i];
                $("#" + empId).prop("checked", false);
                $(".all-payslip").prop("checked", false);
            }
            var ids = JSON.parse($("#selectedPayslip").attr("data-ids") || "[]");
            uniqueIds = makePayslipListUnique(ids);
            toggleHighlight(uniqueIds);
            $("#selectedPayslip").attr("data-ids", JSON.stringify([]));

            count = [];
            tickPayslipCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}
function exportPayslips() {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids.push($("#selectedPayslip").attr("data-ids"));
    ids = JSON.parse($("#selectedPayslip").attr("data-ids"));

    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
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
                    url: "/payroll/payslip-info-export",
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
                        link.download = "Payslip_excel_" + currentDate + ".xlsx";
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
}

$("#deletePayslipBulk").click(function (e) {
    e.preventDefault();

    var checkedRows = $(".payslip-checkbox").filter(":checked");
    ids = [];
    ids.push($("#selectedPayslip").attr("data-ids"));
    ids = JSON.parse($("#selectedPayslip").attr("data-ids"));
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
                    e.preventDefault();
                    ids = [];
                    ids.push($("#selectedPayslip").attr("data-ids"));
                    ids = JSON.parse($("#selectedPayslip").attr("data-ids"));
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
});

// -------------------------------
//        CONTRACT SECTION
// -------------------------------

function addingContractIds() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-contract-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });

    ids = makeEmpListUnique(ids);
    selectedCount = ids.length;

    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
        $("#unselectAllContracts").css("display", "none");
        $("#exportContracts").css("display", "none");
        $("#selectedShow").css("display", "none");
    } else {
        $("#unselectAllContracts").css("display", "inline-flex");
        $("#exportContracts").css("display", "inline-flex");
        $("#selectedShow").css("display", "inline-flex");
        $("#selectedShow").text(selectedCount + " - " + i18nMessages.noRowsSelected);
    }
}

function tickContractCheckboxes() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    uniqueIds = makeEmpListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedInstances").attr("data-clicked");
    if (click === "1") {
        $(".all-contract").prop("checked", true);
    }

    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#unselectAllContracts").css("display", "inline-flex");
        $("#exportContracts").css("display", "inline-flex");
        $("#selectedShow").css("display", "inline-flex");
        $("#selectedShow").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#unselectAllContracts").css("display", "none");
        $("#exportContracts").css("display", "none");
        $("#selectedShow").css("display", "none");
    }
}

function selectAllContracts() {
    $("#selectedInstances").attr("data-clicked", 1);
    var allContractCount = 0;
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
    if (savedFilters && savedFilters["filterData"] !== null) {
        var filter = savedFilters["filterData"];
        $.ajax({
            url: "/payroll/contract-select-filter",
            data: { page: "all", filter: JSON.stringify(filter) },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var contractIds = response.contract_ids;

                if (Array.isArray(contractIds)) {
                    // Continue
                } else {
                    console.error("contractIds is not an array:", contractIds);
                }

                allContractCount = contractIds.length;

                for (var i = 0; i < contractIds.length; i++) {
                    var empId = contractIds[i];
                    $("#" + empId).prop("checked", true);
                }
                var previousIds = $("#selectedInstances").attr("data-ids");
                $("#selectedInstances").attr(
                    "data-ids",
                    JSON.stringify(
                        Array.from(new Set([...contractIds, ...JSON.parse(previousIds)]))
                    )
                );
                console.log(
                    Array.from(new Set([...contractIds, ...JSON.parse(previousIds)]))
                );

                count = makeEmpListUnique(contractIds);
                tickContractCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    } else {
        $.ajax({
            url: "/payroll/contract-select",
            data: { page: "all" },
            type: "GET",
            dataType: "json",
            success: function (response) {
                var contractIds = response.contract_ids;
                if (Array.isArray(contractIds)) {
                    // Continue
                } else {
                    console.error("contractIds is not an array:", contractIds);
                }

                allContractCount = contractIds.length;

                for (var i = 0; i < contractIds.length; i++) {
                    var empId = contractIds[i];
                    $("#" + empId).prop("checked", true);
                }
                $("#selectedInstances").attr("data-ids", JSON.stringify(contractIds));

                count = makeEmpListUnique(contractIds);
                tickContractCheckboxes(count);
            },
            error: function (xhr, status, error) {
                console.error("Error:", error);
            },
        });
    }
}

function unselectAllContracts() {
    $("#selectedInstances").attr("data-clicked", 0);
    $.ajax({
        url: "/payroll/contract-select",
        data: { page: "all", filter: "{}" },
        type: "GET",
        dataType: "json",
        success: function (response) {
            var contractIds = response.contract_ids;

            if (Array.isArray(contractIds)) {
                // Continue
            } else {
                console.error("contractIds is not an array:", contractIds);
            }

            for (var i = 0; i < contractIds.length; i++) {
                var contractId = contractIds[i];
                $("#" + contractId).prop("checked", false);
                $(".all-contract").prop("checked", false);
            }
            var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
            uniqueIds = makeEmpListUnique(ids);
            toggleHighlight(uniqueIds);
            $("#selectedInstances").attr("data-ids", JSON.stringify([]));

            count = [];
            tickContractCheckboxes(count);
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
        },
    });
}

function exportContractRequest() {
    var currentDate = new Date().toISOString().slice(0, 10);

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
                    url: "/payroll/contract-export",
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
                        link.download = "Contract_excel_" + currentDate + ".xlsx";
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
}

$("#DeleteContractBulk").click(function (e) {
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
                ids = [];
                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));

                $.ajax({
                    type: "POST",
                    url: "/payroll/contract-bulk-delete",
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
