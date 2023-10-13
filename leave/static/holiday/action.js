$(document).ready(function () {
  var deleteMessages = {
    ar: "هل تريد حقًا حذف جميع العطل المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Feiertage löschen?",
    es: "¿Realmente quieres eliminar todas las vacaciones seleccionadas?",
    en: "Do you really want to delete all the selected holidays?",
    fr: "Voulez-vous vraiment supprimer toutes les vacances sélectionnées?",
  };

  var no_rows_deleteMessages = {
    ar: "لم تتم تحديد صفوف لحذف العطلات.",
    de: "Es wurden keine Zeilen zum Löschen von Feiertagen ausgewählt.",
    es: "No se han seleccionado filas para eliminar las vacaciones.",
    en: "No rows are selected for deleting holidays.",
    fr: "Aucune ligne n'a été sélectionnée pour supprimer les vacances.",
  };
  var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
  };

  $("#bulkHolidaysDelete").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessages[languageCode];
      var textMessage = no_rows_deleteMessages[languageCode];
      var checkedRows = $(".holiday-checkbox").filter(":checked");
      console.log(checkedRows);
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
              url: "/leave/holidays-bulk-delete",
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

  $(".all-holidays").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-holidays-row").prop("checked", true);
    } else {
      $(".all-holidays-row").prop("checked", false);
    }
  });

  $("#holidays-info-import").click(function (e) {
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
            url: "holidays-excel-template",
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
              link.download = "holiday_excel.xlsx";
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
});

$("#holidaysImportForm").submit(function (e) {
  e.preventDefault();

  // Create a FormData object to send the file
  $("#uploadContainer").css("display", "none");
  $("#uploading").css("display", "block");
  var formData = new FormData(this);

  fetch("/leave/holidays-info-import", {
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
        link.download = "HolidayImportError.xlsx";
        document.body.appendChild(link);
        link.click();
        window.location.href = "/leave/holiday-view";
      }
    })
    .catch((error) => {});
});
