var closeButtonText = {
    ar: "إغلاق",
    de: "Schließen",
    es: "Cerrar",
    en: "Close",
    fr: "Fermer",
};

var confirmButtonText = {
    ar: "تأكيد",
    de: "Bestätigen",
    es: "Confirmar",
    en: "Confirm",
    fr: "Confirmer",
};

var deleteLeaveRequestMessages = {
    ar: "هل تريد حقًا حذف جميع طلبات الإجازة المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Urlaubsanfragen löschen?",
    es: "¿Realmente desea eliminar todas las solicitudes de permiso seleccionadas?",
    en: "Do you really want to delete all the selected leave requests?",
    fr: "Voulez-vous vraiment supprimer toutes les demandes de congé sélectionnées?",
};

var approveLeaveRequests = {
    ar: "هل ترغب في الموافقة على طلبات الإجازة المحددة؟",
    de: "Möchten Sie die ausgewählten Urlaubsanfragen genehmigen?",
    es: "¿Quieres aprobar las solicitudes de licencia seleccionadas?",
    en: "Do you want to approve the selected leave requests?",
    fr: "Voulez-vous approuver les demandes de congé sélectionnées?",
};

var noRowMessage = {
    ar: "لم يتم تحديد أي صفوف.",
    de: "Es wurden keine Zeilen ausgewählt.",
    es: "No se han seleccionado filas.",
    en: "No rows have been selected.",
    fr: "Aucune ligne n'a été sélectionnée.",
};

var rowMessages = {
    ar: " تم الاختيار",
    de: " Ausgewählt",
    es: " Seleccionado",
    en: " Selected",
    fr: " Sélectionné",
};

var excelMessages = {
    ar: "هل ترغب في تنزيل ملف Excel؟",
    de: "Möchten Sie die Excel-Datei herunterladen?",
    es: "¿Desea descargar el archivo de Excel?",
    en: "Do you want to download the excel file?",
    fr: "Voulez-vous télécharger le fichier Excel?",
};

tickLeaverequestsCheckboxes();
function makeLeaverequestsListUnique(list) {
    return Array.from(new Set(list));
}


function getCurrentLanguageCode(callback) {
    var languageCode = $("#main-section-data").attr("data-lang");
    var allowedLanguageCodes = ["ar", "de", "es", "en", "fr"];
    if (allowedLanguageCodes.includes(languageCode)) {
        callback(languageCode);
    } else {
        callback("en");
    }
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
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var message = rowMessages[languageCode];
        if (selectedCount > 0) {
            $("#unselectAllLeaverequests").css("display", "inline-flex");
            $("#exportLeaverequests").css("display", "inline-flex");
            $("#selectedShowLeaverequests").css("display", "inline-flex");
            $("#selectedShowLeaverequests").text(selectedCount + " -" + message);
        } else {
            $("#selectedShowLeaverequests").css("display", "none");
            $("#exportLeaverequests").css("display", "none");
            $("#unselectAllLeaverequests").css("display", "none");
        }
    });
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
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = approveLeaveRequests[languageCode];
        var textMessage = noRowMessage[languageCode];
        ids = JSON.parse($("#selectedInstances").attr("data-ids"));

        if (ids.length === 0) {
            Swal.fire({
                text: textMessage,
                icon: "warning",
                confirmButtonText: "Close",
            });
        } else {
            Swal.fire({
                text: confirmMessage,
                icon: "question",
                showCancelButton: true,
                confirmButtonColor: "#008000",
                cancelButtonColor: "#d33",
                confirmButtonText: "Confirm",
            }).then(function (result) {
                if (result.isConfirmed) {
                    console.log("worked")
                    var hxVals = JSON.stringify(ids);
                    console.log(hxVals)
                    $("#bulkApproveSpan").attr("hx-vals", `{"ids":${hxVals}}`);
                    $("#bulkApproveSpan").click();
                }
            });
        }
    });
}

function bulkDeleteLeaveRequests() {

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteLeaveRequestMessages[languageCode];
        var textMessage = noRowMessage[languageCode];
        ids = [];
        ids.push($("#selectedInstances").attr("data-ids"));
        ids = JSON.parse($("#selectedInstances").attr("data-ids"));
        if (ids.length === 0) {
            Swal.fire({
                text: textMessage,
                icon: "warning",
                confirmButtonText: "Close",
            });
        } else {
            Swal.fire({
                text: confirmMessage,
                icon: "error",
                showCancelButton: true,
                confirmButtonColor: "#008000",
                cancelButtonColor: "#d33",
                confirmButtonText: "Confirm",
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
    });
}
