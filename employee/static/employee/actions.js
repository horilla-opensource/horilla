var excelMessages = {
  ar: "هل ترغب في تنزيل ملف Excel؟",
  de: "Möchten Sie die Excel-Datei herunterladen?",
  es: "¿Desea descargar el archivo de Excel?",
  en: "Do you want to download the excel file?",
  fr: "Voulez-vous télécharger le fichier Excel?",
};
var archiveMessages = {
  ar: "هل ترغب حقًا في أرشفة جميع الموظفين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter archivieren?",
  es: "¿Realmente quieres archivar a todos los empleados seleccionados?",
  en: "Do you really want to archive all the selected employees?",
  fr: "Voulez-vous vraiment archiver tous les employés sélectionnés ?",
};

var unarchiveMessages = {
  ar: "هل ترغب حقًا في إلغاء أرشفة جميع الموظفين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter aus der Archivierung zurückholen?",
  es: "¿Realmente quieres desarchivar a todos los empleados seleccionados?",
  en: "Do you really want to unarchive all the selected employees?",
  fr: "Voulez-vous vraiment désarchiver tous les employés sélectionnés?",
};

var deleteMessages = {
  ar: "هل ترغب حقًا في حذف جميع الموظفين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter löschen?",
  es: "¿Realmente quieres eliminar a todos los empleados seleccionados?",
  en: "Do you really want to delete all the selected employees?",
  fr: "Voulez-vous vraiment supprimer tous les employés sélectionnés?",
};

var noRowMessages = {
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

tickCheckboxes();

function makeListUnique(list) {
  return Array.from(new Set(list));
}

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

$(".all-employee").change(function (e) {
  var is_checked = $(this).is(":checked");
  var closest = $(this)
    .closest(".oh-sticky-table__thead")
    .siblings(".oh-sticky-table__tbody");
  if (is_checked) {
    $(closest)
      .children()
      .find(".all-employee-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(closest)
      .children()
      .find(".all-employee-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
  addingIds();
});

$(".all-employee-row").change(function () {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".all-employee");
  parentCheckbox.prop(
    "checked",
    body.find(".all-employee-row:checked").length ===
      body.find(".all-employee-row").length
  );
  addingIds();
});

function addingIds() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-employee-row").each(function () {
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
  languageCode = $("#main-section-data").attr("data-lang");
  var message =
    rowMessages[languageCode] ||
    ((languageCode = "en"), rowMessages[languageCode]);
  $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
  if (selectedCount === 0) {
    $("#unselectAllEmployees").css("display", "none");
    $("#exportEmployees").css("display", "none");
    $("#selectedShow").css("display", "none");
  } else {
    $("#unselectAllEmployees").css("display", "inline-flex");
    $("#exportEmployees").css("display", "inline-flex");
    $("#selectedShow").css("display", "inline-flex");
    $("#selectedShow").text(selectedCount + " - " + message);
  }
}

function tickCheckboxes() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var uniqueIds = makeListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedInstances").attr("data-clicked");
  if (click === "1") {
    $(".all-employee").prop("checked", true);
  }

  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  languageCode = $("#main-section-data").attr("data-lang");
  var message =
    rowMessages[languageCode] ||
    ((languageCode = "en"), rowMessages[languageCode]);
  if (selectedCount > 0) {
    $("#unselectAllEmployees").css("display", "inline-flex");
    $("#exportEmployees").css("display", "inline-flex");
    $("#selectedShow").css("display", "inline-flex");
    $("#selectedShow").text(selectedCount + " -" + message);
  } else {
    $("#unselectAllEmployees").css("display", "none");
    $("#exportEmployees").css("display", "none");
    $("#selectedShow").css("display", "none");
  }
}

function selectAllEmployees() {
  var allEmployeeCount = 0;
  $("#selectedInstances").attr("data-clicked", 1);
  $("#selectedShow").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
  var filterQuery = $("#selectAllEmployees").data("pd");
  if (savedFilters && savedFilters["filterData"] !== null) {
    $.ajax({
      url: "/employee/employee-select-filter?" + filterQuery,
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

        allEmployeeCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(employeeIds));

        count = makeListUnique(employeeIds);
        $("#unselectAllEmployees").css("display", "inline-flex");
        $("#exportEmployees").css("display", "inline-flex");
        tickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/employee/employee-select",
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

        allEmployeeCount = employeeIds.length;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedInstances").attr("data-ids");
        $("#selectedInstances").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );

        count = makeListUnique(employeeIds);
        $("#unselectAllEmployees").css("display", "inline-flex");
        $("#exportEmployees").css("display", "inline-flex");
        tickCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllEmployees() {
  $("#selectedInstances").attr("data-clicked", 0);

  $.ajax({
    url: "/employee/employee-select",
    data: { page: "unselect", filter: "{}" },
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
        $("#tick").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);

      $("#selectedInstances").attr("data-ids", JSON.stringify([]));

      count = [];
      $("#unselectAllEmployees").css("display", "none");
      $("#exportEmployees").css("display", "none");
      tickCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

$("#exportEmployees").click(function (e) {
  var currentDate = new Date().toISOString().slice(0, 10);
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var confirmMessage =
    excelMessages[languageCode] ||
    ((languageCode = "en"), excelMessages[languageCode]);
  ids = [];
  ids.push($("#selectedInstances").attr("data-ids"));
  ids = JSON.parse($("#selectedInstances").attr("data-ids"));
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
        url: "/employee/work-info-export",
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
          link.download = "employee_export_" + currentDate + ".xlsx";
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

$("#employeeBulkUpdateId").click(function (e) {
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var textMessage =
    noRowMessages[languageCode] ||
    ((languageCode = "en"), noRowMessages[languageCode]);
  ids = [];
  ids.push($("#selectedInstances").attr("data-ids"));
  ids = JSON.parse($("#selectedInstances").attr("data-ids"));
  if (ids.length === 0) {
    $("#bulkUpdateModal").removeClass("oh-modal--show");
    Swal.fire({
      text: textMessage,
      icon: "warning",
      confirmButtonText: "Close",
    });
  } else {
    $("#id_bulk_employee_ids").val(JSON.stringify(ids));
    $("#bulkUpdateModal").addClass("oh-modal--show");
  }
});

$("#archiveEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var confirmMessage =
    archiveMessages[languageCode] ||
    ((languageCode = "en"), archiveMessages[languageCode]);
  var textMessage =
    noRowMessages[languageCode] ||
    ((languageCode = "en"), noRowMessages[languageCode]);
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
      icon: "info",
      showCancelButton: true,
      confirmButtonColor: "#008000",
      cancelButtonColor: "#d33",
      confirmButtonText: "Confirm",
    }).then(function (result) {
      if (result.isConfirmed) {
        e.preventDefault();
        ids = [];
        ids.push($("#selectedInstances").attr("data-ids"));
        ids = JSON.parse($("#selectedInstances").attr("data-ids"));
        $.ajax({
          type: "POST",
          url: "/employee/employee-bulk-archive?is_active=False",
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

$("#unArchiveEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var confirmMessage =
    unarchiveMessages[languageCode] ||
    ((languageCode = "en"), unarchiveMessages[languageCode]);
  var textMessage =
    noRowMessages[languageCode] ||
    ((languageCode = "en"), noRowMessages[languageCode]);
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
      icon: "info",
      showCancelButton: true,
      confirmButtonColor: "#008000",
      cancelButtonColor: "#d33",
      confirmButtonText: "Confirm",
    }).then(function (result) {
      if (result.isConfirmed) {
        e.preventDefault();

        ids = [];

        ids.push($("#selectedInstances").attr("data-ids"));
        ids = JSON.parse($("#selectedInstances").attr("data-ids"));

        $.ajax({
          type: "POST",
          url: "/employee/employee-bulk-archive?is_active=True",
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

$("#deleteEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var confirmMessage =
    deleteMessages[languageCode] ||
    ((languageCode = "en"), deleteMessages[languageCode]);
  var textMessage =
    noRowMessages[languageCode] ||
    ((languageCode = "en"), noRowMessages[languageCode]);
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
        e.preventDefault();

        ids = [];
        ids.push($("#selectedInstances").attr("data-ids"));
        ids = JSON.parse($("#selectedInstances").attr("data-ids"));

        $.ajax({
          type: "POST",
          url: "/employee/employee-bulk-delete",
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

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});
