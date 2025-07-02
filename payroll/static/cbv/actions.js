var excelMessages = {
    ar: "هل ترغب في تنزيل ملف Excel؟",
    de: "Möchten Sie die Excel-Datei herunterladen?",
    es: "¿Desea descargar el archivo de Excel?",
    en: "Do you want to download the excel file?",
    fr: "Voulez-vous télécharger le fichier Excel?",
};

var deletePayslipMessages = {
    ar: "هل تريد حقًا حذف جميع كشوف الدفع المحددة؟",
    de: "Sind Sie sicher, dass Sie alle ausgewählten Gehaltsabrechnungen löschen möchten?",
    es: "¿Realmente quieres eliminar todas las nóminas seleccionadas?",
    en: "Do you really want to delete all the selected payslips?",
    fr: "Voulez-vous vraiment supprimer tous les bulletins de paie sélectionnés?",
};

var deleteContractMessage = {
    ar: "هل ترغب حقًا في حذف جميع العقود المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Verträge löschen?",
    es: "¿Realmente quieres borrar todos los contratos seleccionados?",
    en: "Do you really want to delete all the selected contracts?",
    fr: "Voulez-vous vraiment supprimer tous les contrats sélectionnés?",
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


function getCurrentLanguageCode(callback) {
    var languageCode = $("#main-section-data").attr("data-lang");
    var allowedLanguageCodes = ["ar", "de", "es", "en", "fr"];
    if (allowedLanguageCodes.includes(languageCode)) {
        callback(languageCode);
    } else {
        callback("en");
    }
}


function DeleteContractBulk() {


    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteContractMessage[languageCode];
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
};
