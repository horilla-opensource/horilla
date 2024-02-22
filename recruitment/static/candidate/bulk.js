var archive_CanMessages = {
  ar: "هل ترغب حقًا في أرشفة جميع المرشحين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Kandidaten archivieren?",
  es: "¿Realmente deseas archivar a todos los candidatos seleccionados?",
  en: "Do you really want to archive all the selected candidates?",
  fr: "Voulez-vous vraiment archiver tous les candidats sélectionnés?",
};

var unarchive_CanMessages = {
  ar: "هل ترغب حقًا في إلغاء أرشفة جميع المرشحين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Kandidaten aus der Archivierung nehmen?",
  es: "¿Realmente deseas desarchivar a todos los candidatos seleccionados?",
  en: "Do you really want to unarchive all the selected candidates?",
  fr: "Voulez-vous vraiment désarchiver tous les candidats sélectionnés?",
};

var delete_CanMessages = {
  ar: "هل ترغب حقًا في حذف جميع المرشحين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Kandidaten löschen?",
  es: "¿Realmente deseas eliminar a todos los candidatos seleccionados?",
  en: "Do you really want to delete all the selected candidates?",
  fr: "Voulez-vous vraiment supprimer tous les candidats sélectionnés?",
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

tickCandidateCheckboxes();

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

$(".all-candidate").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-candidate-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(".all-candidate-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
  addingCandidateIds();
});

$(".all-candidate-row").change(function () {
  addingCandidateIds();
});

function addingCandidateIds() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-candidate-row").each(function () {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });
  var ids = makeListUnique1(ids);
  var selectedCount = ids.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
    if (selectedCount > 0) {
      $("#exportCandidates").css("display", "inline-flex");
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#selectedCandidate").text(selectedCount + " -" + message);
      $("#selectedCandidate").css("display", "inline-flex");
    } else {
      $("#exportCandidates").css("display", "none");
      $("#unselectAllInstances").css("display", "none");
      $("#selectedCandidate").css("display", "none");
    }
  });
}

function tickCandidateCheckboxes() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var uniqueIds = makeListUnique1(ids);
  toggleHighlight(uniqueIds);
  var selectedCount = uniqueIds.length;
  var message = rowMessages[languageCode];
  click = $("#selectedInstances").attr("data-clicked");
  if (click === "1") {
    $(".all-candidate").prop("checked", true);
    $("#allCandidate").prop("checked", true);
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true);
  });

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    if (selectedCount > 0) {
      $("#exportCandidates").css("display", "inline-flex");
      $("#unselectAllInstances").css("display", "inline-flex");
      $("#selectedCandidate").text(selectedCount + " -" + message);
      $("#selectedCandidate").css("display", "inline-flex");
    } else {
      $("#exportCandidates").css("display", "none");
      $("#unselectAllInstances").css("display", "none");
      $("#selectedCandidate").css("display", "none");
    }
  });
}

function makeListUnique1(list) {
  return Array.from(new Set(list));
}

$("#archiveCandidates").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = archive_CanMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
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
          $.ajax({
            type: "POST",
            url: "/recruitment/candidate-bulk-archive?is_active=False",
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
});

$("#unArchiveCandidates").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = unarchive_CanMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
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
          $.ajax({
            type: "POST",
            url: "/recruitment/candidate-bulk-archive?is_active=True",
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
});

$("#deleteCandidates").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = delete_CanMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    var checkedRows = $(".all-candidate-row").filter(":checked");
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
          e.preventDefault();
          ids = [];

          ids.push($("#selectedInstances").attr("data-ids"));
          ids = JSON.parse($("#selectedInstances").attr("data-ids"));

          $.ajax({
            type: "POST",
            url: "/recruitment/candidate-bulk-delete",
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
});
