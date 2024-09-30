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

function tickLeaveCheckboxes() {
  var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
  uniqueIds = makeLeaveListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedLeaves").attr("data-clicked");
  if (click === "1") {
    $(".all-assigned-leaves").prop("checked", true);
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllLeaves").css("display", "inline-flex");
      $("#exportAssignedLeaves").css("display", "inline-flex");
      $("#selectedShowLeaves").css("display", "inline-flex");
      $("#selectedShowLeaves").text(selectedCount + " -" + message);
    } else {
      $("#selectedShowLeaves").css("display", "none");
      $("#exportAssignedLeaves").css("display", "none");
      $("#unselectAllLeaves").css("display", "none");
    }
  });
}

function addingAssignedLeaveIds() {
  var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-assigned-leaves-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeLeaveListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];

    $("#selectedLeaves").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
      $("#selectedShowLeaves").css("display", "none");
      $("#exportAssignedLeaves").css("display", "none");
      $("#unselectAllLeaves").css("display", "none");
    } else {
      $("#unselectAllLeaves").css("display", "inline-flex");
      $("#exportAssignedLeaves").css("display", "inline-flex");
      $("#selectedShowLeaves").css("display", "inline-flex");
      $("#selectedShowLeaves").text(selectedCount + " - " + message);
    }
  });
}

$("#selectAllLeaves").click(function () {
  $("#selectedLeaves").attr("data-clicked", 1);
  $("#selectedShowLeaves").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/leave/assigned-leave-select-filter",
      data: { page: "all", filter: JSON.stringify(filter) },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedLeaves").attr("data-ids", JSON.stringify(employeeIds));
        count = makeLeaveListUnique(employeeIds);
        tickLeaveCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/leave/assigned-leave-select",
      data: { page: "all" },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedLeaves").attr("data-ids");
        $("#selectedLeaves").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeLeaveListUnique(employeeIds);
        tickLeaveCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
});

$("#unselectAllLeaves").click(function (e) {
  $("#unselectAllLeaves").click(function () {
    $("#selectedLeaves").attr("data-clicked", 0);
    $.ajax({
      url: "/leave/assigned-leave-select",
      data: { page: "all", filter: "{}" },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", false);
          $(".all-assigned-leaves").prop("checked", false);
        }
        var ids = JSON.parse($("#selectedLeaves").attr("data-ids") || "[]");
        uniqueIds = makeLeaveListUnique(ids);
        toggleHighlight(uniqueIds);
        $("#selectedLeaves").attr("data-ids", JSON.stringify([]));
        count = [];
        tickLeaveCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  });
});

$("#exportAssignedLeaves").click(function (e) {
  var currentDate = new Date().toISOString().slice(0, 10);
  var language_code = null;
  getCurrentLanguageCode(function (code) {
    language_code = code;
    var confirmMessage = excelMessages[language_code];
    ids = [];
    ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
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
          url: "/leave/assigned-leaves-info-export",
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
            link.download = "Assigned_leaves" + currentDate + ".xlsx";
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

$("#bulkAssignedLeavesDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteAssignedMessages[languageCode];
    var textMessage = no_rows_deleteMessages[languageCode];
    ids = [];
    ids.push($("#selectedLeaves").attr("data-ids"));
    ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
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
          e.preventDefault();
          ids = [];
          ids.push($("#selectedLeaves").attr("data-ids"));
          ids = JSON.parse($("#selectedLeaves").attr("data-ids"));
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
});

$(".assign-leave-type-info-import").click(function (e) {
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
});

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});
