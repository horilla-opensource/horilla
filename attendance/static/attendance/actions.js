var downloadMessages = {
  ar: "هل ترغب في تنزيل القالب؟",
  de: "Möchten Sie die Vorlage herunterladen?",
  es: "¿Quieres descargar la plantilla?",
  en: "Do you want to download the template?",
  fr: "Voulez-vous télécharger le modèle ?",
};
var validateMessages = {
  ar: "هل ترغب حقًا في التحقق من كل الحضور المحدد؟",
  de: "Möchten Sie wirklich alle ausgewählten Anwesenheiten überprüfen?",
  es: "¿Realmente quieres validar todas las asistencias seleccionadas?",
  en: "Do you really want to validate all the selected attendances?",
  fr: "Voulez-vous vraiment valider toutes les présences sélectionnées?",
};
var overtimeMessages = {
  ar: "هل ترغب حقًا في الموافقة على الساعات الإضافية لجميع الحضور المحدد؟",
  de: "Möchten Sie wirklich die Überstunden für alle ausgewählten Anwesenheiten genehmigen?",
  es: "¿Realmente quieres aprobar las horas extras para todas las asistencias seleccionadas?",
  en: "Do you really want to approve OT for all the selected attendances?",
  fr: "Voulez-vous vraiment approuver les heures supplémentaires pour toutes les présences sélectionnées?",
};
var deleteMessages = {
  ar: "هل ترغب حقًا في حذف جميع الحضور المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Anwesenheiten löschen?",
  es: "¿Realmente quieres eliminar todas las asistencias seleccionadas?",
  en: "Do you really want to delete all the selected attendances?",
  fr: "Voulez-vous vraiment supprimer toutes les présences sélectionnées?",
};
var noRowValidateMessages = {
  ar: "لم يتم تحديد أي صفوف من فحص الحضور.",
  de: "Im Feld „Anwesenheit validieren“ sind keine Zeilen ausgewählt.",
  es: "No se selecciona ninguna fila de Validar asistencia.",
  en: "No rows are selected from Validate Attendances.",
  fr: "Aucune ligne n'est sélectionnée dans Valider la présence.",
};
var norowotMessages = {
  ar: "لم يتم تحديد أي صفوف من حضور العمل الإضافي.",
  de: "In der OT-Anwesenheit sind keine Zeilen ausgewählt.",
  es: "No se seleccionan filas de Asistencias de OT.",
  en: "No rows are selected from OT Attendances.",
  fr: "Aucune ligne n'est sélectionnée dans les présences OT.",
};
var norowdeleteMessages = {
  ar: "لم يتم تحديد أي صفوف لحذف الحضور.",
  de: "Es sind keine Zeilen zum Löschen von Anwesenheiten ausgewählt.",
  es: "No se seleccionan filas para eliminar asistencias.",
  en: "No rows are selected for deleting attendances.",
  fr: "Aucune ligne n'est sélectionnée pour la suppression des présences.",
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
var reqAttendanceApproveMessages = {
  ar: "هل ترغب حقًا في الموافقة على جميع طلبات الحضور المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Anwesenheitsanfragen genehmigen?",
  es: "¿Realmente quieres aprobar todas las solicitudes de asistencia seleccionadas?",
  en: "Do you really want to approve all the selected attendance requests?",
  fr: "Voulez-vous vraiment approuver toutes les demandes de présence sélectionnées?",
};

var reqAttendanceRejectMessages = {
  ar: "هل ترغب حقًا في رفض جميع طلبات الحضور المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Anwesenheitsanfragen ablehnen?",
  es: "¿Realmente quieres rechazar todas las solicitudes de asistencia seleccionadas?",
  en: "Do you really want to reject all the selected attendance requests?",
  fr: "Voulez-vous vraiment rejeter toutes les demandes de présence sélectionnées?",
};

tickCheckboxes();
function makeListUnique(list) {
  return Array.from(new Set(list));
}

tickactivityCheckboxes();
function makeactivityListUnique(list) {
  return Array.from(new Set(list));
}

ticklatecomeCheckboxes();
function makelatecomeListUnique(list) {
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

$(".validate").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".validate-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".validate-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

$(".validate-row").change(function () {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".validate");
  parentCheckbox.prop(
    "checked",
    body.find(".validate-row:checked").length ===
      body.find(".validate-row").length
  );
});

$(".all-hour-account").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".all-hour-account-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".all-hour-account-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

function tickCheckboxes() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  uniqueIds = makeListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedInstances").attr("data-clicked");
  if (click === "1") {
    $(".all-hour-account").prop("checked", true);
  }

  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#exportAccounts").css("display", "inline-flex");
      $("#selectedShow").css("display", "inline-flex");
      $("#selectedShow").text(selectedCount + " -" + message);
    } else {
      $("#unselectAllInstances").css("display", "none");
      $("#exportAccounts").css("display", "none");
      $("#selectedShow").css("display", "none");
    }
  });
}

function tickactivityCheckboxes() {
  var ids = JSON.parse($("#selectedActivity").attr("data-ids") || "[]");
  uniqueIds = makeactivityListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedActivity").attr("data-clicked");
  if (click === "1") {
    $(".all-attendance-activity").prop("checked", true);
  }

  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllActivity").css("display", "inline-flex");
      $("#exportActivity").css("display", "inline-flex");
      $("#selectedShowActivity").css("display", "inline-flex");
      $("#selectedShowActivity").text(selectedCount + " -" + message);
    } else {
      $("#unselectAllActivity").css("display", "none");
      $("#exportActivity").css("display", "none");
      $("#selectedShowActivity").css("display", "none");
    }
  });
}

function ticklatecomeCheckboxes() {
  var ids = JSON.parse($("#selectedLatecome").attr("data-ids") || "[]");
  uniqueIds = makelatecomeListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedLatecome").attr("data-clicked");
  if (click === "1") {
    $(".all-latecome").prop("checked", true);
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllLatecome").css("display", "inline-flex");
      $("#exportLatecome").css("display", "inline-flex");
      $("#selectedShowLatecome").css("display", "inline-flex");
      $("#selectedShowLatecome").text(selectedCount + " -" + message);
    } else {
      $("#selectedShowLatecome").css("display", "none");
      $("#exportLatecome").css("display", "none");
      $("#unselectAllLatecome").css("display", "none");
    }
  });
}

function selectAllHourAcconts() {
  $("#unselectAllInstances").show();
  $("#exportAccounts").show();
  $("#selectedShow").show();

  $("#selectedInstances").attr("data-clicked", 1);
  $("#selectedShow").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];

    $.ajax({
      url: "/attendance/hour-attendance-select-filter",
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));

        count = makeListUnique(employeeIds);
        tickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/attendance/hour-attendance-select",
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));
        var previousIds = $("#selectedInstances").attr("data-ids");
        $("#selectedInstances").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );

        count = makeListUnique(employeeIds);
        tickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function addingHourAccountsIds() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-hour-account-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeListUnique(ids);
  selectedCount = ids.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
      $("#unselectAllInstances").css("display", "none");
      $("#exportAccounts").css("display", "none");
      $("#selectedShow").css("display", "none");
    } else {
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#exportAccounts").css("display", "inline-flex");
      $("#selectedShow").css("display", "inline-flex");
      $("#selectedShow").text(selectedCount + " - " + message);
    }
  });
}

function unselectAllHourAcconts() {
  $("#selectedInstances").attr("data-clicked", 0);

  $.ajax({
    url: "/attendance/hour-attendance-select",
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
        $("#allHourAccount").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);

      $("#selectedInstances").attr("data-ids", JSON.stringify([]));

      count = [];
      $("#unselectAllInstances").hide();
      $("#exportAccounts").hide();
      tickCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

$(".all-attendances").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".all-attendance-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".all-attendance-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

$(".all-attendance-row").change(function () {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".all-attendances");
  parentCheckbox.prop(
    "checked",
    body.find(".all-attendance-row:checked").length ===
      body.find(".all-attendance-row").length
  );
});

$(".ot-attendances").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".ot-attendance-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".ot-attendance-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

$(".ot-attendance-row").change(function () {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".ot-attendances");
  parentCheckbox.prop(
    "checked",
    body.find(".ot-attendance-row:checked").length ===
      body.find(".ot-attendance-row").length
  );
});

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

function addingActivityIds() {
  var ids = JSON.parse($("#selectedActivity").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-attendance-activity-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeactivityListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];

    $("#selectedActivity").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
      $("#unselectAllActivity").css("display", "none");
      $("#exportActivity").css("display", "none");
      $("#selectedShowActivity").css("display", "none");
    } else {
      $("#unselectAllActivity").css("display", "inline-flex");
      $("#exportActivity").css("display", "inline-flex");
      $("#selectedShowActivity").css("display", "inline-flex");
      $("#selectedShowActivity").text(selectedCount + " - " + message);
    }
  });
}

function addinglatecomeIds() {
  var ids = JSON.parse($("#selectedLatecome").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-latecome-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makelatecomeListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];

    $("#selectedLatecome").attr("data-ids", JSON.stringify(ids));

    if (selectedCount === 0) {
      $("#selectedShowLatecome").css("display", "none");
      $("#exportLatecome").css("display", "none");
      $("#unselectAllLatecome").css("display", "none");
    } else {
      $("#exportLatecome").css("display", "inline-flex");
      $("#unselectAllLatecome").css("display", "inline-flex");
      $("#selectedShowLatecome").css("display", "inline-flex");
      $("#selectedShowLatecome").text(selectedCount + " - " + message);
    }
  });
}
function selectAllActivity() {
  $("#selectedActivity").attr("data-clicked", 0);
  $("#selectedShowActivity").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];

    $.ajax({
      url: "/attendance/activity-attendance-select-filter",
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedActivity").attr("data-ids", JSON.stringify(employeeIds));

        count = makeactivityListUnique(employeeIds);
        tickactivityCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {

    $("#selectedActivity").attr("data-clicked", 1);

    $.ajax({
      url: "/attendance/activity-attendance-select",
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedActivity").attr("data-ids");
        $("#selectedActivity").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );

        count = makeactivityListUnique(employeeIds);
        tickactivityCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllActivity() {
  $("#selectedActivity").attr("data-clicked", 0);
  $.ajax({
    url: "/attendance/activity-attendance-select",
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
        $(".all-attendance-activity").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedActivity").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);
      $("#selectedActivity").attr("data-ids", JSON.stringify([]));

      count = [];
      tickactivityCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

$("#attendance-info-import").click(function (e) {
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
          url: "/attendance/attendance-excel",
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
            link.download = "attendance_excel.xlsx";
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


function selectAllLatecome() {
  // $("#selectAllLatecome").click(function () {

    $("#selectedLatecome").attr("data-clicked", 0);
    $("#selectedShowLatecome").removeAttr("style");
    var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

    if (savedFilters && savedFilters["filterData"] !== null) {
      var filter = savedFilters["filterData"];

      $.ajax({
        url: "/attendance/latecome-attendance-select-filter",
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

          var selectedCount = employeeIds.length;

          for (var i = 0; i < employeeIds.length; i++) {
            var empId = employeeIds[i];
            $("#" + empId).prop("checked", true);
          }
          $("#selectedLatecome").attr("data-ids", JSON.stringify(employeeIds));

          count = makelatecomeListUnique(employeeIds);
          ticklatecomeCheckboxes(count);
        },
        error: function (xhr, status, error) {
          console.error("Error:", error);
        },
      });
    } else {

      $("#selectedLatecome").attr("data-clicked", 1);

      $.ajax({
        url: "/attendance/latecome-attendance-select",
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

          var selectedCount = employeeIds.length;

          for (var i = 0; i < employeeIds.length; i++) {
            var empId = employeeIds[i];
            $("#" + empId).prop("checked", true);
          }
          var previousIds = $("#selectedLatecome").attr("data-ids");
          $("#selectedLatecome").attr(
            "data-ids",
            JSON.stringify(
              Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
            )
          );

          count = makelatecomeListUnique(employeeIds);
          ticklatecomeCheckboxes(count);
        },
        error: function (xhr, status, error) {
          console.error("Error:", error);
        },
      });
    }
  // });
}

function unselectAllLatecome() {
  // $("#unselectAllLatecome").click(function () {
    $("#selectedLatecome").attr("data-clicked", 0);

    $.ajax({
      url: "/attendance/latecome-attendance-select",
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
          $(".all-latecome").prop("checked", false);
        }
        var ids = JSON.parse($("#selectedLatecome").attr("data-ids") || "[]");
        var uniqueIds = makeListUnique(ids);
        toggleHighlight(uniqueIds);
        $("#selectedLatecome").attr("data-ids", JSON.stringify([]));

        count = [];
        ticklatecomeCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  // });
}

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});

$(".all-latecome").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".all-latecome-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $("#selectedLatecome").attr("data-clicked", 0);
    $(closest)
      .children()
      .find(".all-latecome-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

$(".all-attendance-activity").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".all-attendance-activity-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $("#selectedActivity").attr("data-clicked", 0);
    $(closest)
      .children()
      .find(".all-attendance-activity-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

$("#attendanceImportForm").submit(function (e) {
  e.preventDefault();

  // Create a FormData object to send the file
  $("#uploadContainer").css("display", "none");
  $("#uploading").css("display", "block");
  var formData = new FormData(this);

  fetch("/attendance/attendance-info-import", {
    method: "POST",
    dataType: "binary",
    body: formData,
    processData: false,
    contentType: false,
    headers: {
      // Include the CSRF token in the headers
      "X-CSRFToken": "{{ csrf_token }}",
    },
    xhrFields: {
      responseType: "blob",
    },
  })
    .then((response) => {
      if (response.ok) {
        return response.blob(); // Use response.blob() to get the binary data
      } else {
        // Handle errors, e.g., show an error message
      }
    })
    .then((blob) => {
      if (blob) {
        // Create a Blob from the binary data
        const file = new Blob([blob], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        const url = URL.createObjectURL(file);
        const link = document.createElement("a");
        link.href = url;
        link.download = "ImportError.xlsx";
        document.body.appendChild(link);
        link.click();
        window.location.href = "/attendance/attendance-view";
      }
    })
    .catch((error) => {});
});

$("#validateAttendances").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = validateMessages[languageCode];
    var textMessage = noRowValidateMessages[languageCode];
    var checkedRows = $(".validate-row").filter(":checked");
    if (checkedRows.length === 0) {
      Swal.fire({
        text: textMessage,
        icon: "warning",
        confirmButtonText: "Close",
      });
    } else {
      Swal.fire({
        text: "confirmMessage",
        icon: "info",
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
          $.ajax({
            type: "POST",
            url: "/attendance/validate-bulk-attendance",
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

$("#approveOt").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = overtimeMessages[languageCode];
    var textMessage = norowotMessages[languageCode];
    var checkedRows = $(".ot-attendance-row").filter(":checked");
    if (checkedRows.length === 0) {
      Swal.fire({
        text: textMessage,
        icon: "warning",
        confirmButtonText: "Close",
      });
    } else {
      Swal.fire({
        text: confirmMessage,
        icon: "success",
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
          $.ajax({
            type: "POST",
            url: "/attendance/approve-bulk-overtime",
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

// -------------------------------------------Data Export Handlers---------------------------------------------------------------

$("#exportAccounts").click(function (e) {
  var currentDate = new Date().toISOString().slice(0, 10);
  var languageCode = null;
  ids = [];
  ids.push($("#selectedInstances").attr("data-ids"));
  ids = JSON.parse($("#selectedInstances").attr("data-ids"));
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = excelMessages[languageCode];
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
          url: "/attendance/attendance-account-info-export",
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
            link.download = "Hour_account" + currentDate + ".xlsx";
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

$("#exportActivity").click(function (e) {
  var currentDate = new Date().toISOString().slice(0, 10);
  var languageCode = null;
  ids = [];
  ids.push($("#selectedActivity").attr("data-ids"));
  ids = JSON.parse($("#selectedActivity").attr("data-ids"));
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = excelMessages[languageCode];
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
          url: "/attendance/attendance-activity-info-export",
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
            link.download = "Attendance_activity" + currentDate + ".xlsx";
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

$("#exportLatecome").click(function (e) {
  var currentDate = new Date().toISOString().slice(0, 10);
  var languageCode = null;
  ids = [];
  ids.push($("#selectedLatecome").attr("data-ids"));
  ids = JSON.parse($("#selectedLatecome").attr("data-ids"));
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = excelMessages[languageCode];
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
          url: "/attendance/late-come-early-out-info-export",
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
            link.download = "Late_come" + currentDate + ".xlsx";
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

// ------------------------------------------------------------------------------------------------------------------------------

// -------------------------------------------------Data Delete Handlers---------------------------------------------------------

$("#bulkDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowdeleteMessages[languageCode];
    var checkedRows = $(".attendance-checkbox").filter(":checked");
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
          $.ajax({
            type: "POST",
            url: "/attendance/attendance-bulk-delete",
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

$("#hourAccountbulkDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowdeleteMessages[languageCode];
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
            url: "/attendance/attendance-account-bulk-delete",
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
  });
});

$("#attendanceActivityDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowdeleteMessages[languageCode];
    ids = [];
    ids.push($("#selectedActivity").attr("data-ids"));
    ids = JSON.parse($("#selectedActivity").attr("data-ids"));
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
          ids.push($("#selectedActivity").attr("data-ids"));
          ids = JSON.parse($("#selectedActivity").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/attendance/attendance-activity-bulk-delete",
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
  });
});

$("#lateComeBulkDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowdeleteMessages[languageCode];
    ids = [];
    ids.push($("#selectedLatecome").attr("data-ids"));
    ids = JSON.parse($("#selectedLatecome").attr("data-ids"));
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
          ids.push($("#selectedLatecome").attr("data-ids"));
          ids = JSON.parse($("#selectedLatecome").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/attendance/late-come-early-out-bulk-delete",
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
  });
});


// attendance requests select all functions

function requestedAttendanceTickCheckboxes() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  uniqueIds = makeListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedInstances").attr("data-clicked");
  if (click === "1") {
    $(".requested-attendances-select-all").prop("checked", true);
  }
    uniqueIds.forEach(function (id) {
      $("#" + id).prop("checked", true);
    });

  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#selectedShow").css("display", "inline-flex");
      $("#selectedShow").text(selectedCount + " -" + message);
    } else {
      $("#selectedShow").css("display", "none");
    }
  });
}

function dictToQueryString(dict) {
  const queryString = Object.keys(dict).map(key => {
      const value = dict[key];
      if (Array.isArray(value)) {
          return value.map(val => `${encodeURIComponent(key)}=${encodeURIComponent(val)}`).join('&');
      } else {
          return `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
      }
  }).join('&');
  return queryString;
}


function selectAllReqAttendance() {
  $("#unselectAllInstances").show();
  $("#selectedShow").show();

  $("#selectedInstances").attr("data-clicked", 1);
  $("#selectedShow").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    // Convert the dictionary to a query string
    var queryString = dictToQueryString(filter);
    $.ajax({
      url: `/attendance/select-all-filter-attendance-request?${queryString}`,
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));

        count = makeListUnique(employeeIds);

        requestedAttendanceTickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/attendance/select-all-filter-attendance-request",
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

        var selectedCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));
        var previousIds = $("#selectedInstances").attr("data-ids");
        $("#selectedInstances").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );

        count = makeListUnique(employeeIds);
        requestedAttendanceTickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllReqAttendance() {
  $("#selectedInstances").attr("data-clicked", 0);

  $.ajax({
    url: "/attendance/select-all-filter-attendance-request",
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
        $(".requested-attendances-select-all").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);

      $("#selectedInstances").attr("data-ids", JSON.stringify([]));

      count = [];
      $("#unselectAllInstances").hide();
      requestedAttendanceTickCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}


$("#reqAttendanceBulkApprove").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = reqAttendanceApproveMessages[languageCode];
    var textMessage = noRowValidateMessages[languageCode];
    var checkedRows = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    if (checkedRows.length === 0) {
      Swal.fire({
        text: textMessage,
        icon: "warning",
        confirmButtonText: "Close",
      });
    } else {
      Swal.fire({
        text: confirmMessage,
        icon: "info",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: "Confirm",
      }).then(function (result) {
        if (result.isConfirmed) {
          ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
          $.ajax({
            type: "POST",
            url: "/attendance/bulk-approve-attendance-request",
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
  });
});

$("#reqAttendanceBulkReject").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = reqAttendanceRejectMessages[languageCode];
    var textMessage = noRowValidateMessages[languageCode];
    var checkedRows = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    if (checkedRows.length === 0) {
      Swal.fire({
        text: textMessage,
        icon: "warning",
        confirmButtonText: "Close",
      });
    } else {
      Swal.fire({
        text: confirmMessage,
        icon: "info",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: "Confirm",
      }).then(function (result) {
        if (result.isConfirmed) {
          ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
          $.ajax({
            type: "POST",
            url: "/attendance/bulk-reject-attendance-request",
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
  });
});


function addingRequestAttendanceIds() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;
    $(".requested-attendance-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeListUnique(ids);

  selectedCount = ids.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#unselectAllInstances").css("display", "none");
      $("#selectedShow").css("display", "none");
    } else {
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#selectedShow").css("display", "inline-flex");
      $("#selectedShow").text(selectedCount + " - " + message);
    }
  });
}

$(".requested-attendances-select-all").click(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".requested-attendance-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".requested-attendance-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
  addingRequestAttendanceIds()
});
function checkReqAttentanceSelectAll(){
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".requested-attendances-select-all");
  parentCheckbox.prop(
    "checked",
    body.find(".requested-attendance-row:checked").length ===
      body.find(".requested-attendance-row").length
  );
}
$(".requested-attendance-row").change(function () {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".requested-attendances-select-all");
  parentCheckbox.prop(
    "checked",
    body.find(".requested-attendance-row:checked").length ===
      body.find(".requested-attendance-row").length
  );
  $("#selectedInstances").attr("data-clicked", 0);
  addingRequestAttendanceIds();

});


// ------------------------------------------------------------------------------------------------------------------------------

// ******************************************************************
// *     THIS IS FOR SWITCHING THE DATE FORMAT IN THE ALL VIEWS     *
// ******************************************************************

// Iterate through all elements with the 'dateformat_changer' class and format their content

$(".dateformat_changer").each(function (index, element) {
  var currentDate = $(element).text().trim();
  // Checking currentDate value is a date or None value.
  if (/[\.,\-\/]/.test(currentDate)) {
    var formattedDate = dateFormatter.getFormattedDate(currentDate);
  } else if (currentDate) {
    var formattedDate = currentDate;
  } else {
    var formattedDate = "None";
  }
  $(element).text(formattedDate);
});

// Display the formatted date wherever needed
var currentDate = $(".dateformat_changer").first().text();
var formattedDate = dateFormatter.getFormattedDate(currentDate);

// ******************************************************************
// *     THIS IS FOR SWITCHING THE TIME FORMAT IN THE ALL VIEWS     *
// ******************************************************************

// Iterate through all elements with the 'timeformat_changer' class and format their content
$(".timeformat_changer").each(function (index, element) {
  var currentTime = $(element).text().trim();

  if (currentTime === 'midnight'){
    if (timeFormatter.timeFormat === 'hh:mm A') {
      formattedTime = '12:00 AM'
    }else{
      formattedTime = '00:00'
    }
  }
  else if (currentTime === 'noon'){
    if (timeFormatter.timeFormat === 'hh:mm A') {
      formattedTime = '12:00 PM'
    }else{
      formattedTime = '12:00'
    }
  }
  // Checking currentTime value is a valid time.
  else if (/[\.:]/.test(currentTime)) {
    var formattedTime = timeFormatter.getFormattedTime(currentTime);
  } else if (currentTime) {
    var formattedTime = currentTime;
  } else {
    var formattedTime = "None";
  }
  $(element).text(formattedTime);
});

// Display the formatted time wherever needed
var currentTime = $(".timeformat_changer").first().text();
var formattedTime = timeFormatter.getFormattedTime(currentTime);
