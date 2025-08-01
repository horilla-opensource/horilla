var archiveMessages = {
  ar: "هل ترغب حقاً في أرشفة كل التعليقات المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Rückmeldungen archivieren?",
  es: "¿Realmente quieres archivar todas las retroalimentaciones seleccionadas?",
  en: "Do you really want to archive all the selected feedbacks?",
  fr: "Voulez-vous vraiment archiver tous les retours sélectionnés?",
};

var unarchiveMessages = {
  ar: "هل ترغب حقاً في إلغاء الأرشفة عن كل التعليقات المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Rückmeldungen aus der Archivierung nehmen?",
  es: "¿Realmente quieres desarchivar todas las retroalimentaciones seleccionadas?",
  en: "Do you really want to unarchive all the selected feedbacks?",
  fr: "Voulez-vous vraiment désarchiver tous les retours sélectionnés?",
};

var deleteFeedbackMessages = {
  ar: "هل ترغب حقاً في حذف كل التعليقات المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Rückmeldungen löschen?",
  es: "¿Realmente quieres eliminar todas las retroalimentaciones seleccionadas?",
  en: "Do you really want to delete all the selected feedbacks?",
  fr: "Voulez-vous vraiment supprimer tous les retours sélectionnés?",
};

var norowMessages = {
  ar: "لم يتم تحديد أي صفوف.",
  de: "Es wurden keine Zeilen ausgewählt.",
  es: "No se han seleccionado filas.",
  en: "No rows have been selected.",
  fr: "Aucune ligne n'a été sélectionnée.",
};

$(".all-feedbacks").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-feedback-row").prop("checked", true);
  } else {
    $(".all-feedback-row").prop("checked", false);
  }
});

$(".self-feedbacks").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".self-feedback-row").prop("checked", true);
  } else {
    $(".self-feedback-row").prop("checked", false);
  }
});

$(".requested-feedbacks").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".requested-feedback-row").prop("checked", true);
  } else {
    $(".requested-feedback-row").prop("checked", false);
  }
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

$("#archiveFeedback").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = archiveMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".feedback-checkbox").filter(":checked");
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
          e.preventDefault();
          ids = [];
          announy_ids = []
          checkedRows.each(function () {
            if($(this).data("anounymous")) {
              announy_ids.push($(this).attr("id"))
            } else {
              ids.push($(this).attr("id"));
            }
          });
          $.ajax({
            type: "POST",
            url: "/pms/feedback-bulk-archive?is_active=False",
            data: {
              csrfmiddlewaretoken: getCookie("csrftoken"),
              ids: JSON.stringify(ids),
              announy_ids : JSON.stringify(announy_ids),
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

$("#unArchiveFeedback").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = unarchiveMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".feedback-checkbox").filter(":checked");
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
          e.preventDefault();
          ids = [];
          announy_ids = []
          checkedRows.each(function () {
            if($(this).data("anounymous")) {
              announy_ids.push($(this).attr("id"))
            } else {
              ids.push($(this).attr("id"));
            }
          });

          $.ajax({
            type: "POST",
            url: "/pms/feedback-bulk-archive?is_active=True",
            data: {
              csrfmiddlewaretoken: getCookie("csrftoken"),
              ids: JSON.stringify(ids),
              announy_ids : JSON.stringify(announy_ids),
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

$("#deleteFeedback").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteFeedbackMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".feedback-checkbox").filter(":checked");
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
          checkedRows.each(function () {
            ids.push($(this).attr("id"));
          });

          $.ajax({
            type: "POST",
            url: "/pms/feedback-bulk-delete",
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
