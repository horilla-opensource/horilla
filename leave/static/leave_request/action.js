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

var rejectLeaveRequests = {
  ar: "هل تريد رفض طلبات الإجازة المختارة؟",
  de: "Möchten Sie die ausgewählten Abwesenheitsanträge ablehnen?",
  es: "¿Quieres rechazar las solicitudes de vacaciones seleccionadas?",
  en: "Do you want to reject the selected leave requests?",
  fr: "Vous souhaitez rejeter les demandes de congés sélectionnées ?",
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

tickUserrequestsCheckboxes();
function makeUserrequestsListUnique(list) {
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

function addingLeaverequestsIds() {
  var ids = JSON.parse($("#selectedLeaverequests").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-leave-requests-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeLeaverequestsListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedLeaverequests").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#selectedShowLeaverequests").css("display", "none");
      $("#exportLeaverequests").css("display", "none");
      $("#unselectAllLeaverequests").css("display", "none");
    } else {
      $("#unselectAllLeaverequests").css("display", "inline-flex");
      $("#exportLeaverequests").css("display", "inline-flex");
      $("#selectedShowLeaverequests").css("display", "inline-flex");
      $("#selectedShowLeaverequests").text(selectedCount + " - " + message);
    }
  });
}

function selectAllLeaverequests() {
  $("#selectedLeaverequests").attr("data-clicked", 1);
  $("#selectedShowLeaverequests").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/leave/leave-request-select-filter",
      data: { page: "all", filter: JSON.stringify(filter) },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedLeaverequests").attr(
          "data-ids",
          JSON.stringify(employeeIds)
        );

        count = makeLeaverequestsListUnique(employeeIds);
        tickLeaverequestsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/leave/leave-request-select",
      data: { page: "all" },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedLeaverequests").attr("data-ids");
        $("#selectedLeaverequests").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeLeaverequestsListUnique(employeeIds);
        tickLeaverequestsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllLeaverequests() {
  $("#selectedLeaverequests").attr("data-clicked", 0);
  $.ajax({
    url: "/leave/leave-request-select",
    data: { page: "all", filter: "{}" },
    type: "GET",
    dataType: "json",
    success: function (response) {
      var employeeIds = response.employee_ids;
      for (var i = 0; i < employeeIds.length; i++) {
        var empId = employeeIds[i];
        $("#" + empId).prop("checked", false);
        $(".all-leave-requests").prop("checked", false);
      }
      var ids = JSON.parse(
        $("#selectedLeaverequests").attr("data-ids") || "[]"
      );
      uniqueIds = makeLeaverequestsListUnique(ids);
      toggleHighlight(uniqueIds);
      $("#selectedLeaverequests").attr("data-ids", JSON.stringify([]));

      count = [];
      tickLeaverequestsCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}
function exportLeaverequests() {
  var currentDate = new Date().toISOString().slice(0, 10);
  var language_code = null;
  getCurrentLanguageCode(function (code) {
    language_code = code;
    var confirmMessage = excelMessages[language_code];
    ids = [];
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
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
          url: "/leave/leave-requests-info-export",
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
            link.download = "Leave_requests" + currentDate + ".xlsx";
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

$("#leaveRequestsBulkApprove").click(function (e) {
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = approveLeaveRequests[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
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
          var hxVals = JSON.stringify(ids);
          $("#bulkApproveSpan").attr("hx-vals", `{"ids":${hxVals}}`);
          $("#bulkApproveSpan").click();
        }
      });
    }
  });
});


$("#idBulkRejectReason").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = rejectLeaveRequests[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
    var rejectReason = $("#id_reject_reason").val();
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
          var data = JSON.stringify({"request_ids":ids, "reason":rejectReason})
          $("#bulkRejectSpan").attr("hx-vals", data);
          $("#bulkRejectSpan").click();
        }
      });
    }
  });
});

$("#leaverequestbulkDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteLeaveRequestMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = [];
    ids.push($("#selectedLeaverequests").attr("data-ids"));
    ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
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
          ids.push($("#selectedLeaverequests").attr("data-ids"));
          ids = JSON.parse($("#selectedLeaverequests").attr("data-ids"));
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
});

// ---------------------------------------
//              USER LEAVE
// ---------------------------------------

function tickUserrequestsCheckboxes() {
  var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
  uniqueIds = makeUserrequestsListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedUserrequests").attr("data-clicked");
  if (click === "1") {
    $(".all-user-requests").prop("checked", true);
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllUserrequests").css("display", "inline-flex");
      $("#exportUserrequests").css("display", "inline-flex");
      $("#selectedShowUserrequests").css("display", "inline-flex");
      $("#selectedShowUserrequests").text(selectedCount + " -" + message);
    } else {
      $("#unselectAllUserrequests").css("display", "none");
      $("#exportUserrequests").css("display", "none");
      $("#selectedShowUserrequests").css("display", "none");
    }
  });
}

function addingUserrequestsIds() {
  var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-user-requests-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });

  ids = makeUserrequestsListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedUserrequests").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#unselectAllUserrequests").css("display", "none");
      $("#selectedShowUserrequests").css("display", "none");
      $("#exportUserrequests").css("display", "none");
    } else {
      $("#exportUserrequests").css("display", "inline-flex");
      $("#unselectAllUserrequests").css("display", "inline-flex");
      $("#selectedShowUserrequests").css("display", "inline-flex");
      $("#selectedShowUserrequests").text(selectedCount + " - " + message);
    }
  });
}

function selectAllUserrequests() {
  $("#selectedUserrequests").attr("data-clicked", 1);
  $("#selectedShowUserrequests").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));

  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/leave/user-request-select-filter",
      data: { page: "all", filter: JSON.stringify(filter) },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedUserrequests").attr(
          "data-ids",
          JSON.stringify(employeeIds)
        );

        count = makeUserrequestsListUnique(employeeIds);
        tickUserrequestsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/leave/user-request-select",
      data: { page: "all" },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;
        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        var previousIds = $("#selectedUserrequests").attr("data-ids");
        $("#selectedUserrequests").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeUserrequestsListUnique(employeeIds);
        tickUserrequestsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllUserrequests() {
  $("#selectedUserrequests").attr("data-clicked", 0);
  $.ajax({
    url: "/leave/user-request-select",
    data: { page: "all", filter: "{}" },
    type: "GET",
    dataType: "json",
    success: function (response) {
      var employeeIds = response.employee_ids;
      for (var i = 0; i < employeeIds.length; i++) {
        var empId = employeeIds[i];
        $("#" + empId).prop("checked", false);
        $(".all-user-requests").prop("checked", false);
      }
      var ids = JSON.parse($("#selectedUserrequests").attr("data-ids") || "[]");
      var uniqueIds = makeListUnique(ids);
      toggleHighlight(uniqueIds);
      $("#selectedUserrequests").attr("data-ids", JSON.stringify([]));

      count = [];
      tickUserrequestsCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

$("#userrequestbulkDelete").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteLeaveRequestMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = [];
    ids.push($("#selectedUserrequests").attr("data-ids"));
    ids = JSON.parse($("#selectedUserrequests").attr("data-ids"));
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
          ids.push($("#selectedUserrequests").attr("data-ids"));
          ids = JSON.parse($("#selectedUserrequests").attr("data-ids"));
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
              } else {
              }
            },
          });
        }
      });
    }
  });
});
