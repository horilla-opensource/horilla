var deleteleaverequestMessages = {
  ar: "هل تريد حقًا حذف جميع طلبات الإجازة المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Urlaubsanfragen löschen?",
  es: "¿Realmente desea eliminar todas las solicitudes de permiso seleccionadas?",
  en: "Do you really want to delete all the selected leave requests?",
  fr: "Voulez-vous vraiment supprimer toutes les demandes de congé sélectionnées?",
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

tickLeaverequestsCheckboxes();
function makeLeaverequestsListUnique(list) {
  return Array.from(new Set(list));
}

function getCurrentLanguageCode(callback) {
  $.ajax({
    type: "GET",
    url: "/employee/get-language-code/",
    success: function (response) {
      var languageCode = response.language_code;
      callback(languageCode); // Pass the language code to the callback
    },
  });
}

function tickLeaverequestsCheckboxes() {
  var ids = JSON.parse($("#selectedLeaverequests").attr("data-ids") || "[]");
  uniqueIds = makeLeaverequestsListUnique(ids);
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
      $("#exportLeaverequests").css("display", "inline-flex");
      $("#selectedShowLeaverequests").css("display", "inline-flex");
      $("#selectedShowLeaverequests").text(selectedCount + " -" + message);
    } else {
      $("#selectedShowLeaverequests").css("display", "none");
      $("#exportLeaverequests").css("display", "none");
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
    } else {
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

        if (Array.isArray(employeeIds)) {
          // Continue
        } else {
          console.error("employee_ids is not an array:", employeeIds);
        }

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedLeaverequests").attr("data-ids", JSON.stringify(employeeIds));

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
        if (Array.isArray(employeeIds)) {
          // Continue
        } else {
          console.error("employee_ids is not an array:", employeeIds);
        }

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

      if (Array.isArray(employeeIds)) {
        // Continue
      } else {
        console.error("employee_ids is not an array:", employeeIds);
      }

      for (var i = 0; i < employeeIds.length; i++) {
        var empId = employeeIds[i];
        $("#" + empId).prop("checked", false);
        $(".all-leave-requests").prop("checked", false);
      }
      $("#selectedLeaverequests").attr("data-ids", JSON.stringify([]));

      count = [];
      tickLeaverequestsCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}


$("#leaverequestbulkDelete").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
        languageCode = code;
        var confirmMessage = deleteleaverequestMessages[languageCode];
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
  