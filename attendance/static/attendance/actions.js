$(document).ready(function () {
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
  function getCurrentLanguageCode(callback) {
    $.ajax({
      type: "GET",
      url: "/attendance/get-language-code/",
      success: function (response) {
        var languageCode = response.language_code;
        callback(languageCode); // Pass the language code to the callback function
      },
    });
  }
  $(".validate").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".validate-row").prop("checked", true);
    } else {
      $(".validate-row").prop("checked", false);
    }
  });

  $(".all-attendances").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-attendance-row").prop("checked", true);
    } else {
      $(".all-attendance-row").prop("checked", false);
    }
  });

  $(".ot-attendances").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".ot-attendance-row").prop("checked", true);
    } else {
      $(".ot-attendance-row").prop("checked", false);
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
  $("#validateAttendances").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      console.log(languageCode);
      var confirmMessage = validateMessages[languageCode];
      choice = originalConfirm(confirmMessage);
      if (choice) {
        var checkedRows = $(".validate-row").filter(":checked");
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
  });

  $("#approveOt").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = overtimeMessages[languageCode];
      choice = originalConfirm(confirmMessage);
      if (choice) {
        var checkedRows = $(".ot-attendance-row").filter(":checked");
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
  });

  $("#bulkDelete").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessages[languageCode];
      choice = originalConfirm(confirmMessage);
      if (choice) {
        var checkedRows = $(".attendance-checkbox").filter(":checked");
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
  });
});
