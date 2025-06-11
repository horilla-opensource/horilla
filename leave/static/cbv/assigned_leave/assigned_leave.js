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

var deleteAssignedMessages = {
    ar: "هل تريد حقًا حذف كافة حالات الغياب المعينة المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten zugewiesenen abwesenheit löschen?",
    es: "¿Realmente desea eliminar todas las hojas asignadas dejar?",
    en: "Do you really want to delete all the selected assigned leaves?",
    fr: "Voulez-vous vraiment supprimer tous les sélectionnés congés attribués ?",
};

var no_rows_deleteMessages = {
    ar: "لم يتم تحديد أي صفوف لحذف الإجازات المخصصة.",
    de: "Es gibt keine Zeilen zum Löschen der zugewiesenen abwesenheit.",
    es: "No se ha seleccionado ninguna fila para eliminar la  asignadas dejar",
    en: "No rows are selected for deleting assigned leaves.",
    fr: "Aucune ligne n'est sélectionnée pour supprimer les congés attribués.",
};

var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
};

tickLeaveCheckboxes();
function makeLeaveListUnique(list) {
    return Array.from(new Set(list));
}

function getCurrentLanguageCode(callback) {
    var languageCode = $("#main-section-data").attr("data-lang");
    var allowedLanguageCodes = ["ar", "de", "es", "en", "fr"];
    if (allowedLanguageCodes.includes(languageCode)) {
        callback(languageCode);
    } else {
        $.ajax({
            type: "GET",
            url: "/employee/get-language-code/",
            success: function (response) {
                var ajaxLanguageCode = response.language_code;
                $("#main-section-data").attr("data-lang", ajaxLanguageCode);
                callback(
                    allowedLanguageCodes.includes(ajaxLanguageCode)
                        ? ajaxLanguageCode
                        : "en"
                );
            },
            error: function () {
                callback("en");
            },
        });
    }
}

function importAssignedLeave() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = downloadMessages[languageCode];
        Swal.fire({
            text: confirmMessage,
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: "Confirm",
        }).then(function (result) {
            if (result.isConfirmed) {
                $.ajax({
                    type: "GET",
                    url: "/leave/assign-leave-type-excel",
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
                        link.download = "assign_leave_type_excel.xlsx";
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
}

function leaveAssigBulkDelete() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteAssignedMessages[languageCode];
        var textMessage = no_rows_deleteMessages[languageCode];
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
}