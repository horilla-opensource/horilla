$(document).ready(function () {
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
  var norowvalidateMessages = {
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
  function getCurrentLanguageCode(callback) {
    $.ajax({
      type: "GET",
      url: "/employee/get-language-code/",
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
            url: "attendance-excel",
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
      .catch((error) => {
      });
  });

  $("#validateAttendances").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = validateMessages[languageCode];
      var textMessage = norowvalidateMessages[languageCode];
      var checkedRows = $(".validate-row").filter(":checked");
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
});
