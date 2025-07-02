var rowMessages = {
    ar: " تم الاختيار",
    de: " Ausgewählt",
    es: " Seleccionado",
    en: " Selected",
    fr: " Sélectionné",
};

var deleteHolidayMessages = {
    ar: "هل تريد حقًا حذف جميع العطل المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Feiertage löschen?",
    es: "¿Realmente quieres eliminar todas las vacaciones seleccionadas?",
    en: "Do you really want to delete all the selected holidays?",
    fr: "Voulez-vous vraiment supprimer toutes les vacances sélectionnées?",
};

var no_rows_deleteMessages = {
    ar: "لم تتم تحديد صفوف لحذف العطلات.",
    de: "Es wurden keine Zeilen zum Löschen von Feiertagen ausgewählt.",
    es: "No se han seleccionado filas para eliminar las vacaciones.",
    en: "No rows are selected for deleting holidays.",
    fr: "Aucune ligne n'a été sélectionnée pour supprimer les vacances.",
};
var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
};

function createHolidayHxValue() {
    var pd = $(".oh-pagination").attr("data-pd");
    var hxValue = JSON.stringify(pd);
    $("#holidayCreateButton").attr("hx-vals", `{"pd":${hxValue}}`);
}

tickHolidayCheckboxes();
function makeHolidayListUnique(list) {
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
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var message = rowMessages[languageCode];
        if (selectedCount > 0) {
            $("#unselectAllHolidays").css("display", "inline-flex");
            $("#exportHolidays").css("display", "inline-flex");
            $("#selectedShowHolidays").css("display", "inline-flex");
            $("#selectedShowHolidays").text(selectedCount + " -" + message);
        } else {
            $("#unselectAllHolidays").css("display", "none  ");
            $("#selectedShowHolidays").css("display", "none");
            $("#exportHolidays").css("display", "none");
        }
    });
}


//$(".holidaysInfoImport").click(function (e) {

function importHolidays() {
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
    });
}



function bulkDeleteHoliday() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteHolidayMessages[languageCode];
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
    });
}
