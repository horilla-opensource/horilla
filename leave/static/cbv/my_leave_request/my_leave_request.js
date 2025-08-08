// tickLeaverequestsCheckboxes();
// function makeLeaverequestsListUnique(list) {
//   return Array.from(new Set(list));
// }

// tickUserrequestsCheckboxes();
// function makeUserrequestsListUnique(list) {
//   return Array.from(new Set(list));
// }

// ---------------------------------------
//            LEAVE REQUEST
// ---------------------------------------

// function tickLeaverequestsCheckboxes() {
//   var ids = JSON.parse($("#selectedLeaverequests").attr("data-ids") || "[]");
//   uniqueIds = makeLeaverequestsListUnique(ids);
//   toggleHighlight(uniqueIds);
//   click = $("#selectedLeaverequests").attr("data-clicked");
//   if (click === "1") {
//     $(".all-leave-requests").prop("checked", true);
//   }
//   uniqueIds.forEach(function (id) {
//     $("#" + id).prop("checked", true);
//   });
//   var selectedCount = uniqueIds.length;
//   getCurrentLanguageCode(function (code) {
//     languageCode = code;
//     var message = rowMessages[languageCode];
//     if (selectedCount > 0) {
//       $("#unselectAllLeaverequests").css("display", "inline-flex");
//       $("#exportLeaverequests").css("display", "inline-flex");
//       $("#selectedShowLeaverequests").css("display", "inline-flex");
//       $("#selectedShowLeaverequests").text(selectedCount + " -" + message);
//     } else {
//       $("#selectedShowLeaverequests").css("display", "none");
//       $("#exportLeaverequests").css("display", "none");
//       $("#unselectAllLeaverequests").css("display", "none");
//     }
//   });
// }


function myLeaveRequestBulkDelete() {



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
                    url: "/leave/user-request-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload();
                        }
                    },
                });
            }
        });
    }

}
