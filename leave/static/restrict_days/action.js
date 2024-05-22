var rowMessages = {
  ar: " تم الاختيار",
  de: " Ausgewählt",
  es: " Seleccionado",
  en: " Selected",
  fr: " Sélectionné",
};

var deleteDaysMessages = {
  ar: "هل تريد حقًا حذف جميع العطل المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Feiertage löschen?",
  es: "¿Realmente quieres eliminar todas las vacaciones seleccionadas?",
  en: "Do you really want to delete all the selected restrict days?",
  fr: "Voulez-vous vraiment supprimer toutes les vacances sélectionnées?",
};

var noRowsDeleteMessages = {
  ar: "لم تتم تحديد صفوف لحذف العطلات.",
  de: "Es wurden keine Zeilen zum Löschen von Feiertagen ausgewählt.",
  es: "No se han seleccionado filas para eliminar las vacaciones.",
  en: "No rows are selected for deleting restrict days.",
  fr: "Aucune ligne n'a été sélectionnée pour supprimer les vacances.",
};

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

function makeDaysListUnique(list) {
  return Array.from(new Set(list));
}

function tickRestrictDaysCheckboxes() {
  var ids = JSON.parse($("#selectedRestrictDays").attr("data-ids") || "[]");
  uniqueIds = makeDaysListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedRestrictDays").attr("data-clicked");
  if (click === "1") {
    $(".all-restrict-days").prop("checked", true);
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#unselectAllRestrictDays").css("display", "inline-flex");
    //   $("#exportRestrictDays").css("display", "inline-flex");
      $("#showSelectedDays").css("display", "inline-flex");
      $("#showSelectedDays").text(selectedCount + " -" + message);
    } else {
      $("#unselectAllRestrictDays").css("display", "none  ");
      $("#showSelectedDays").css("display", "none");
    //   $("#exportRestrictDays").css("display", "none");
    }
  });
}

function addingRestrictDayIds() {
  var ids = JSON.parse($("#selectedRestrictDays").attr("data-ids") || "[]");
  var selectedCount = 0;
  $(".all-restrict-days-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
        $(".all-restrict-days").prop("checked", false);
      }
    }
  });
  ids = makeDaysListUnique(ids);
  toggleHighlight(ids);
  selectedCount = ids.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedRestrictDays").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#showSelectedDays").css("display", "none");
    //   $("#exportRestrictDays").css("display", "none");
      $("#unselectAllRestrictDays").css("display", "none");
    } else {
      $("#unselectAllRestrictDays").css("display", "inline-flex");
    //   $("#exportRestrictDays").css("display", "inline-flex");
      $("#showSelectedDays").css("display", "inline-flex");
      $("#showSelectedDays").text(selectedCount + " - " + message);
    }
  });
}
function updateParentCheckbox() {
  var parentTable = $(this).closest(".oh-sticky-table");
  var body = parentTable.find(".oh-sticky-table__tbody");
  var parentCheckbox = parentTable.find(".all-restrict-days");
  parentCheckbox.prop(
    "checked",
    body.find(".all-restrict-days-row:checked").length ===
      body.find(".all-restrict-days-row").length
  );
  addingRestrictDayIds();
}
function toggleAllCheckboxes(e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-restrict-days-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(".all-restrict-days-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
  addingRestrictDayIds();
}

function selectAllRestrictDays() {
  $("#selectedRestrictDays").attr("data-clicked", 1);
  $("#showSelectedDays").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
  var ajaxData =
    savedFilters && savedFilters["filterData"]
      ? { page: "all", filter: JSON.stringify(savedFilters["filterData"]) }
      : { page: "all" };
  var ajaxUrl =
    savedFilters && savedFilters["filterData"]
      ? "/leave/restrict-day-select-filter"
      : "/leave/restrict-day-select";

  $.ajax({
    url: ajaxUrl,
    data: ajaxData,
    type: "GET",
    dataType: "json",
    success: function (response) {
      var restrictDayIds = response.restrict_day_ids;

      if (!Array.isArray(restrictDayIds)) {
        console.error("restrictDayIds is not an array:", restrictDayIds);
        return;
      }

      restrictDayIds.forEach(function (dayId) {
        $("#" + dayId).prop("checked", true);
      });

      var previousIds = $("#selectedRestrictDays").attr("data-ids") || "[]";
      var allIds = Array.from(
        new Set([...restrictDayIds, ...JSON.parse(previousIds)])
      );

      $("#selectedRestrictDays").attr("data-ids", JSON.stringify(allIds));

      var count = makeDaysListUnique(restrictDayIds);
      tickRestrictDaysCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

function unselectAllRestrictDays() {
  $("#selectedRestrictDays").attr("data-clicked", 0);

  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
  var ajaxData =
    savedFilters && savedFilters["filterData"]
      ? { page: "all", filter: JSON.stringify(savedFilters["filterData"]) }
      : { page: "all" };
  var ajaxUrl =
    savedFilters && savedFilters["filterData"]
      ? "/leave/restrict-day-select-filter"
      : "/leave/restrict-day-select";

  $.ajax({
    url: ajaxUrl,
    data: ajaxData,
    type: "GET",
    dataType: "json",
    success: function (response) {
      var restrictDayIds = response.restrict_day_ids;
      if (!Array.isArray(restrictDayIds)) {
        console.error("restrict_day_ids is not an array:", restrictDayIds);
        return;
      }

      restrictDayIds.forEach(function (dayId) {
        $("#" + dayId)
          .prop("checked", false)
          .closest(".oh-sticky-table__tr")
          .removeClass("highlight-selected");
      });
      $(".all-restrict-days").prop("checked", false);

      var previousIds = $("#selectedRestrictDays").attr("data-ids") || "[]";
      var remainingIds = JSON.parse(previousIds).filter(
        (id) => !restrictDayIds.includes(id)
      );

      $("#selectedRestrictDays").attr("data-ids", JSON.stringify(remainingIds));

      var count = makeDaysListUnique(remainingIds);
      tickRestrictDaysCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

$("#bulkRestrictedDaysDelete").click(function (e) {
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteDaysMessages[languageCode];
    var textMessage = noRowsDeleteMessages[languageCode];
    ids = JSON.parse($("#selectedRestrictDays").attr("data-ids"));
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
          $("#bulkDeleteSpan").attr("hx-vals", `{"ids":${hxVals}}`);
          $("#bulkDeleteSpan").click();
        }
      });
    }
  });
});
