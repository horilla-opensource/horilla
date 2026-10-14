/*
 * Bulk approve / reject / delete for the "Leave Allocation Requests" tab.
 *
 * The progress animation and the Total / result / Failed dialog are drawn by the
 * shared bulk-action wrapper in static/index/index.js (it recognises these URLs),
 * so these handlers only confirm, post the ids and refresh the list in place.
 */
function leaveAllocationSelectedIds() {
    try {
        return JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    } catch (e) {
        return [];
    }
}

function leaveAllocationNoRowsSelected() {
    Swal.fire({
        text: i18nMessages.noRowsSelected,
        icon: "warning",
        confirmButtonText: i18nMessages.close,
    });
}

function leaveAllocationBulkPost(url, extra) {
    var ids = leaveAllocationSelectedIds();
    $.ajax({
        type: "POST",
        url: url,
        data: $.extend({ csrfmiddlewaretoken: getCookie("csrftoken"), ids: JSON.stringify(ids) }, extra || {}),
        success: function () {
            clearSelection("selectedInstances");
            hlvReloadListInPlace();
        },
    });
}

function leaveAllocationBulkApprove() {
    if (!leaveAllocationSelectedIds().length) return leaveAllocationNoRowsSelected();
    Swal.fire({
        text: i18nMessages.confirmBulkApprove,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#6c757d",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) leaveAllocationBulkPost("/leave/leave-allocation-request-bulk-approve/");
    });
}

function leaveAllocationBulkReject() {
    if (!leaveAllocationSelectedIds().length) return leaveAllocationNoRowsSelected();
    Swal.fire({
        text: i18nMessages.confirmBulkReject,
        icon: "warning",
        input: "textarea",
        inputPlaceholder: gettext("Rejection reason"),
        inputAttributes: { "aria-label": gettext("Rejection reason") },
        inputValidator: function (value) {
            if (!value || !value.trim()) return gettext("A rejection reason is required.");
        },
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#6c757d",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            leaveAllocationBulkPost("/leave/leave-allocation-request-bulk-reject/", { reason: result.value });
        }
    });
}

function leaveAllocationBulkDelete() {
    if (!leaveAllocationSelectedIds().length) return leaveAllocationNoRowsSelected();
    Swal.fire({
        text: i18nMessages.confirmBulkDelete,
        icon: "error",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#6c757d",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) leaveAllocationBulkPost("/leave/leave-allocation-request-bulk-delete/");
    });
}
