tickLeaverequestsCheckboxes();
function makeLeaverequestsListUnique(list) {
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
}
