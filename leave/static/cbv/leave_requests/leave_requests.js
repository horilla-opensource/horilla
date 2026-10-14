tickLeaverequestsCheckboxes();
function makeLeaverequestsListUnique(list) {
    return Array.from(new Set(list));
}

// ---------------------------------------
//            LEAVE REQUEST
// ---------------------------------------

function refreshLeaveRequestListContainer() {
    if (typeof htmx === "undefined") return;
    var query = window.location.search || "";
    var url = "/leave/request-filter/" + query;
    htmx.ajax("GET", url, { target: "#listContainer", swap: "innerHTML" });
    var rejectModal = document.getElementById("rejectModal");
    if (rejectModal) rejectModal.classList.remove("oh-modal--show");
}

document.addEventListener("reloadLeaveRequestList", function () {
    refreshLeaveRequestListContainer();
});

document.addEventListener("horillaMessage", function (evt) {
    var detail = (evt && evt.detail) ? evt.detail : {};
    var text = detail.text || "";
    if (!text) return;

    var level = detail.level === "error" ? "danger" : "success";
    var $alert = $("<div>")
        .addClass("oh-alert oh-alert--animated oh-alert--" + level)
        .text(text);
    var $container = $("<div>").addClass("oh-alert-container").append($alert);
    $alert.on("animationend", function () {
        $container.remove();
    });
    $("body").append($container);
});

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

// function bulkApproveLeaveRequests() {
//   var languageCode = null;
//   getCurrentLanguageCode(function (code) {
//     languageCode = code;
//     var confirmMessage = approveLeaveRequests[languageCode];
//     var textMessage = noRowMessage[languageCode];
//     ids = [];
//     ids.push($("#selectedInstances").attr("data-ids"));
//     ids = JSON.parse($("#selectedInstances").attr("data-ids"));
//     console.log(ids) // Parse IDs

//     if (ids.length === 0) {
//       Swal.fire({
//         text: textMessage,
//         icon: "warning",
//         confirmButtonText: closeButtonText[languageCode], // Use language-specific text for close button
//       });
//     } else {
//       Swal.fire({
//         text: confirmMessage,
//         icon: "question",
//         showCancelButton: true,
//         confirmButtonColor: "#008000",
//         cancelButtonColor: "#d33",
//         confirmButtonText: confirmButtonText[languageCode], // Use language-specific text for confirm button
//       }).then(function (result) {
//         if (result.isConfirmed) {
//           ids = [];
//           ids.push($("#selectedInstances").attr("data-ids"));
//           ids = JSON.parse($("#selectedInstances").attr("data-ids"));
//           console.log(ids)
//           $.ajax({
//             type: "POST",
//             url: "/leave/leave-requests-bulk-approve",
//             data: {
//               csrfmiddlewaretoken: getCookie("csrftoken"),
//               ids: JSON.stringify(ids),
//             },
//             success: function (response, textStatus, jqXHR) {
//               if (jqXHR.status === 200) {
//                 location.reload(); // Reload the current page on success
//               } else {
//                 console.error("Unexpected HTTP status:", jqXHR.status);
//               }
//             },
//             error: function (jqXHR, textStatus, errorThrown) {
//               console.error("AJAX Error:", errorThrown);
//             },
//           });
//         }
//       });
//     }
//   });
// }



function bulkApproveLeaveRequests() {
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));

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
            cancelButtonColor: "#6c757d",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                // Progress + result dialog come from the shared bulk-action
                // wrapper in index.js; the list refreshes in place afterwards.
                $.ajax({
                    type: "POST",
                    url: "/leave/leave-requests-bulk-approve/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function () {
                        clearSelection("selectedInstances");
                        hlvReloadListInPlace();
                    },
                });
            }
        });
    }
}

function bulkRejectLeaveRequests() {
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));

    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkReject,
            icon: "warning",
            input: "textarea",
            inputPlaceholder: gettext("Rejection reason"),
            inputAttributes: { "aria-label": gettext("Rejection reason") },
            inputValidator: function (value) {
                if (!value || !value.trim()) {
                    return gettext("A rejection reason is required.");
                }
            },
            showCancelButton: true,
            confirmButtonColor: "#d33",
            cancelButtonColor: "#6c757d",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                $.ajax({
                    type: "POST",
                    url: "/leave/leave-requests-bulk-reject/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                        reason: result.value,
                    },
                    success: function () {
                        clearSelection("selectedInstances");
                        hlvReloadListInPlace();
                    },
                });
            }
        });
    }
}

function bulkDeleteLeaveRequests() {
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
            confirmButtonColor: "#d33",
            cancelButtonColor: "#6c757d",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/leave/leave-request-bulk-delete/",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            clearSelection("selectedInstances");
                            hlvReloadListInPlace();
                        }
                    },
                });
            }
        });
    }
}


function importLeaveRequest() {
    Swal.fire({
        text: i18nMessages.downloadTemplate,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#6c757d",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/leave/leave-request-excel/",
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
                    link.download = "leave_request_excel.xlsx";
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
