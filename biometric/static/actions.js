
var deleteUsersMessages = {
    ar: "هل ترغب حقًا في حذف جميع الحضور المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anwesenheiten löschen?",
    es: "¿Realmente quieres eliminar todas las asistencias seleccionadas?",
    en: "Do you really want to delete all the selected Users?",
    fr: "Voulez-vous vraiment supprimer toutes les présences sélectionnées?",
};
var nousersdeleteMessages = {
    ar: "لم يتم تحديد أي صفوف لحذف الحضور.",
    de: "Es sind keine Zeilen zum Löschen von Anwesenheiten ausgewählt.",
    es: "No se seleccionan filas para eliminar asistencias.",
    en: "No rows are selected for deleting users from device.",
    fr: "Aucune ligne n'est sélectionnée pour la suppression des présences.",
};

function getCurrentLanguageCode(callback) {
    $.ajax({
        type: "GET",
        url: "/employee/get-language-code/",
        success: function (response) {
            var languageCode = response.language_code;
            callback(languageCode); // Pass the language code to the callback function
        },
    });
}

function selectAllDahuaUsers(element) {
    var is_checked = $("#allBioEmployee").is(":checked");
    if (is_checked) {
        $(".all-bio-employee-row").prop("checked", true);
    } else {
        $(".all-bio-employee-row").prop("checked", false);
    }
}
function selectAllETimeOfficeUsers(element) {
    var is_checked = $("#allBioEmployee").is(":checked");
    if (is_checked) {
        $(".all-bio-employee-row").prop("checked", true);
    } else {
        $(".all-bio-employee-row").prop("checked", false);
    }
}

$(".all-bio-employee-row").change(function (e) {
    var is_checked = $(".all-bio-employee").is(":checked");
    if (is_checked) {
        $(".all-bio-employee").prop("checked", false);
    }
});



// -------------------------------------------------Data Delete Handlers---------------------------------------------------------

$("#deleteBioUsers").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteUsersMessages[languageCode];
        var textMessage = nousersdeleteMessages[languageCode];
        var checkedRows = $(".all-bio-employee-row").filter(":checked");
        var deviceId = $(".all-bio-employee").attr("data-device");
        if (checkedRows.length === 0) {
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
                    checkedRows.each(function () {
                        ids.push($(this).attr("id"));
                    });
                    $("#BiometricDeviceTestModal").toggleClass("oh-modal--show")
                    $.ajax({
                        type: "POST",
                        url: "/biometric/biometric-users-bulk-delete",
                        data: {
                            csrfmiddlewaretoken: getCookie("csrftoken"),
                            ids: JSON.stringify(ids),
                            deviceId: deviceId,
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
});


$("#deleteCosecUsers").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteUsersMessages[languageCode];
        var textMessage = nousersdeleteMessages[languageCode];
        var checkedRows = $(".all-bio-employee-row").filter(":checked");
        var deviceId = $(".all-bio-employee").attr("data-device");
        if (checkedRows.length === 0) {
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
                    checkedRows.each(function () {
                        ids.push($(this).attr("id"));
                    });
                    $("#BiometricDeviceTestModal").toggleClass("oh-modal--show");
                    $.ajax({
                        type: "POST",
                        url: "/biometric/cosec-users-bulk-delete",
                        data: {
                            csrfmiddlewaretoken: getCookie("csrftoken"),
                            ids: JSON.stringify(ids),
                            deviceId: deviceId,
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
});


function deleteDahuaUsers(e) {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteUsersMessages[languageCode];
        var textMessage = nousersdeleteMessages[languageCode];
        var checkedRows = $(".all-bio-employee-row").filter(":checked");
        if (checkedRows.length === 0) {
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
                    checkedRows.each(function () {
                        ids.push($(this).attr("id"));
                    });
                    var hxValue = JSON.stringify(ids);
                    var bioDeviceID = JSON.stringify($("#allBioEmployee").data("device"))
                    $("#deleteDahuaUsers").attr("hx-vals", `{"ids":${hxValue},"device_id":${bioDeviceID}}`);
                    $("#deleteDahuaUsers").click();
                }
            });
        }
    });
}

function deleteETimeOfficeUsers(e) {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteUsersMessages[languageCode];
        var textMessage = nousersdeleteMessages[languageCode];
        var checkedRows = $(".all-bio-employee-row").filter(":checked");
        if (checkedRows.length === 0) {
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
                    checkedRows.each(function () {
                        ids.push($(this).attr("id"));
                    });
                    var hxValue = JSON.stringify(ids);
                    var bioDeviceID = JSON.stringify($("#allBioEmployee").data("device"))
                    $("#deleteETimeOfficeUsers").attr("hx-vals", `{"ids":${hxValue},"device_id":${bioDeviceID}}`);
                    $("#deleteETimeOfficeUsers").click();
                }
            });
        }
    });
}

// ------------------------------------------------------------------------------------------------------------------------------

// ******************************************************************
// *     THIS IS FOR SWITCHING THE DATE FORMAT IN THE ALL VIEWS     *
// ******************************************************************

// Iterate through all elements with the 'dateformat_changer' class and format their content

// $('.dateformat_changer').each(function(index, element) {
//   var currentDate = $(element).text();
//   // Checking currentDate value is a date or None value.
//   if (/[\.,\-\/]/.test(currentDate)) {
//     var formattedDate = dateFormatter.getFormattedDate(currentDate);
//   }
//   else {
//     var formattedDate = 'None';
//   }
//   $(element).text(formattedDate);
// });

// // Display the formatted date wherever needed
// var currentDate = $('.dateformat_changer').first().text();
// var formattedDate = dateFormatter.getFormattedDate(currentDate);
