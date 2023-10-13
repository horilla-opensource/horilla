$(document).ready(function () {
  var deleteMessages = {
    ar: "هل تريد حقًا حذف كافة حالات الغياب المعينة المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten zugewiesenen abwesenheit löschen?",
    es: "¿Realmente desea eliminar todas las hojas asignadas dejar?",
    en: "Do you really want to delete all the selected assigned leaves?",
    fr: "Voulez-vous vraiment supprimer tous les sélectionnés congés attribués ?",
  };
  var no_rows_deleteMessages = {
    ar: "لم يتم تحديد أي صفوف لحذف الإجازات المخصصة.",
    de: "Es gibt keine Zeilen zum Löschen der zugewiesenen abwesenheit.",
    es: "No se ha seleccionado ninguna fila para eliminar la  asignadas dejar",
    en: "No rows are selected for deleting assigned leaves.",
    fr: "Aucune ligne n'est sélectionnée pour supprimer les congés attribués.",
  };
  var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
  };

  $("#bulkAssignedLeavesDelete").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessages[languageCode];
      var textMessage = no_rows_deleteMessages[languageCode];
      var checkedRows = $(".assigned-leaves-checkbox").filter(":checked");
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
              url: "/leave/assigned-leave-bulk-delete",
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

  $(".all-assigned-leaves").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-assigned-leaves-row").prop("checked", true);
    } else {
      $(".all-assigned-leaves-row").prop("checked", false);
    }
  });

  $("#assign-leave-type-info-import").click(function (e) {
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
            url: "assign-leave-type-excel",
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
              link.download = "assign_leave_type_excel.xlsx";
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

$("#assignLeaveTypeImportForm").submit(function (e) {
  e.preventDefault();

  // Create a FormData object to send the file
  $("#uploadContainer").css("display", "none");
  $("#uploading").css("display", "block");
  var formData = new FormData(this);

  fetch("/leave/assign-leave-type-info-import", {
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
        link.download = "AssignLeaveError.xlsx";
        document.body.appendChild(link);
        link.click();
        window.location.href = "/leave/assign-view";
      }
    })
    .catch((error) => {});
});

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});
