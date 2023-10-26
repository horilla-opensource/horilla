var archiveMessages = {
  ar: "هل ترغب حقاً في أرشفة جميع الأهداف المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Ziele archivieren?",
  es: "¿Realmente quieres archivar todos los objetivos seleccionados?",
  en: "Do you really want to archive all the selected objectives?",
  fr: "Voulez-vous vraiment archiver tous les objectifs sélectionnés?",
};

var unarchiveMessages = {
  ar: "هل ترغب حقاً في إلغاء الأرشفة عن جميع الأهداف المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Ziele aus der Archivierung nehmen?",
  es: "¿Realmente quieres desarchivar todos los objetivos seleccionados?",
  en: "Do you really want to unarchive all the selected objectives?",
  fr: "Voulez-vous vraiment désarchiver tous les objectifs sélectionnés?",
};

var deleteMessages = {
  ar: "هل ترغب حقاً في حذف جميع الأهداف المحددة؟",
  de: "Möchten Sie wirklich alle ausgewählten Ziele löschen?",
  es: "¿Realmente quieres eliminar todos los objetivos seleccionados?",
  en: "Do you really want to delete all the selected objectives?",
  fr: "Voulez-vous vraiment supprimer tous les objectifs sélectionnés?",
};

var norowMessages = {
  ar: "لم يتم تحديد أي صفوف.",
  de: "Es wurden keine Zeilen ausgewählt.",
  es: "No se han seleccionado filas.",
  en: "No rows have been selected.",
  fr: "Aucune ligne n'a été sélectionnée.",
};


$(".all-objects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-objects-row").prop("checked", true);
    } else {
        $(".all-objects-row").prop("checked", false);
    }
});

$(".own-objects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".own-objects-row").prop("checked", true);
    } else {
        $(".own-objects-row").prop("checked", false);
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
    $.ajax({
      type: "GET",
      url: "/employee/get-language-code/",
      success: function (response) {
        var languageCode = response.language_code;
        callback(languageCode); // Pass the language code to the callback
      },
    });
  }

$("#archiveObjectives").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = archiveMessages[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".objective-checkbox").filter(":checked");
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
                checkedRows.each(function () {
                ids.push($(this).attr("id"));
            });
            
            $.ajax({
                type: "POST",
                url: "/pms/objective-bulk-archive?is_active=False",
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

$("#unArchiveObjectives").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = unarchiveMessages[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".objective-checkbox").filter(":checked");
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
                checkedRows.each(function () {
                ids.push($(this).attr("id"));
                });
                
                $.ajax({
                    type: "POST",
                    url: "/pms/objective-bulk-archive?is_active=True",
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

$("#deleteObjectives").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessages[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".objective-checkbox").filter(":checked");
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
                    url: "/pms/objective-bulk-delete",
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
