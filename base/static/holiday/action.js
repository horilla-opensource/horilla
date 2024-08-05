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
function makeListUnique(list) {
  return Array.from(new Set(list));
}

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

function addingHolidayIds() {
  var ids = JSON.parse($("#selectedHolidays").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-holidays-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
        $(".all-holidays").prop("checked", false);
      }
    }
  });

  ids = makeHolidayListUnique(ids);
  toggleHighlight(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedHolidays").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#selectedShowHolidays").css("display", "none");
      $("#exportHolidays").css("display", "none");
      $('#unselectAllHolidays').css("display", "none");
    } else {
      $("#unselectAllHolidays").css("display", "inline-flex");
      $("#exportHolidays").css("display", "inline-flex");
      $("#selectedShowHolidays").css("display", "inline-flex");
      $("#selectedShowHolidays").text(selectedCount + " - " + message);
    }
  });
}

function selectAllHolidays() {
  $("#selectedHolidays").attr("data-clicked", 1);
  $("#selectedShowHolidays").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/holiday-select-filter",
      data: { page: "all", filter: JSON.stringify(filter) },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;

        if (Array.isArray(employeeIds)) {
          // Continue
        } else {
          console.error("employee_ids is not an array:", employeeIds);
        }

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedHolidays").attr("data-ids", JSON.stringify(employeeIds));

        count = makeHolidayListUnique(employeeIds);
        tickHolidayCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/holiday-select",
      data: { page: "all" },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        if (Array.isArray(employeeIds)) {
          // Continue
        } else {
          console.error("employee_ids is not an array:", employeeIds);
        }

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedHolidays").attr("data-ids");
        $("#selectedHolidays").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeHolidayListUnique(employeeIds);
        tickHolidayCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllHolidays() {
  $("#selectedHolidays").attr("data-clicked", 0);
  $.ajax({
    url: "/holiday-select",
    data: { page: "all", filter: "{}" },
    type: "GET",
    dataType: "json",
    success: function (response) {
      var employeeIds = response.employee_ids;

      if (Array.isArray(employeeIds)) {
        // Continue
      } else {
        console.error("employee_ids is not an array:", employeeIds);
      }

      for (var i = 0; i < employeeIds.length; i++) {
        var empId = employeeIds[i];
        $("#" + empId).prop("checked", false);
        $(".all-holidays").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedHolidays").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);
      $("#selectedHolidays").attr("data-ids", JSON.stringify([]));

      count = [];
      tickHolidayCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

function exportHolidays() {
  var currentDate = new Date().toISOString().slice(0, 10);
  var language_code = null;
  getCurrentLanguageCode(function (code) {
    language_code = code;
    var confirmMessage = excelMessages[language_code];
    ids = [];
    ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
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
          url: "/holiday-info-export",
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
            link.download = "holiday_leaves" + currentDate + ".xlsx";
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

$("#bulkHolidaysDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteHolidayMessages[languageCode];
    var textMessage = no_rows_deleteMessages[languageCode];
    ids = [];
    ids.push($("#selectedHolidays").attr("data-ids"));
    ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
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
          ids.push($("#selectedHolidays").attr("data-ids"));
          ids = JSON.parse($("#selectedHolidays").attr("data-ids"));
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
});

$("#holidaysInfoImport").click(function (e) {
  e.preventDefault();
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
          url: "holidays-excel-template",
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
});
