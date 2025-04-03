var archiveMessagesSelected = {
    // ar: "هل ترغب حقًا في أرشفة جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter archivieren?",
    // es: "¿Realmente quieres archivar a todos los empleados seleccionados?",
    en: "Do you really want to archive all the selected projects?",
    // fr: "Voulez-vous vraiment archiver tous les employés sélectionnés ?",
  };

  var unarchiveMessagesSelected = {
    // ar: "هل ترغب حقًا في إلغاء أرشفة جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter aus der Archivierung zurückholen?",
    // es: "¿Realmente quieres desarchivar a todos los empleados seleccionados?",
    en: "Do you really want to unarchive all the selected projects?",
    // fr: "Voulez-vous vraiment désarchiver tous les employés sélectionnés?",
  };

  var deleteMessage = {
    // ar: "هل ترغب حقًا في حذف جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter löschen?",
    // es: "¿Realmente quieres eliminar a todos los empleados seleccionados?",
    en: "Do you really want to delete all the selected projects?",
    // fr: "Voulez-vous vraiment supprimer tous les employés sélectionnés?",
  };

  var exportMessages = {
    // ar: "هل ترغب حقًا في حذف جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter löschen?",
    // es: "¿Realmente quieres eliminar a todos los empleados seleccionados?",
    en: "Do you really want to export all the selected projects?",
    // fr: "Voulez-vous vraiment supprimer tous les employés sélectionnés?",
  };

  var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
  };

  var norowMessagesSelected = {
    // ar: "لم يتم تحديد أي صفوف.",
    // de: "Es wurden keine Zeilen ausgewählt.",
    // es: "No se han seleccionado filas.",
    en: "No rows have been selected.",
    // fr: "Aucune ligne n'a été sélectionnée.",
  };

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


  // // Get the form element
  // var form = document.getElementById("projectImportForm");

  // // Add an event listener to the form submission
  // form.addEventListener("submit", function (event) {
  //   // Prevent the default form submission
  //   event.preventDefault();

  //   // Create a new form data object
  //   var formData = new FormData();

  //   // Append the file to the form data object
  //   var fileInput = document.querySelector("#projectImportFile");
  //   formData.append("file", fileInput.files[0]);
  //   $.ajax({
  //     type: "POST",
  //     url: "/project/project-import",
  //     dataType: "binary",
  //     data: formData,
  //     processData: false,
  //     contentType: false,
  //     headers: {
  //       "X-CSRFToken": getCookie('csrftoken'), // Replace with your csrf token value
  //     },
  //     xhrFields: {
  //       responseType: "blob",
  //     },
  //     success: function (response) {
  //       const file = new Blob([response], {
  //         type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  //       });
  //       const url = URL.createObjectURL(file);
  //       const link = document.createElement("a");
  //       link.href = url;
  //       link.download = "ImportError.xlsx";
  //       document.body.appendChild(link);
  //       link.click();
  //     },
  //     error: function (xhr, textStatus, errorThrown) {
  //       console.error("Error downloading file:", errorThrown);
  //     },
  //   });
  // });

  // $("#importProject").click(function (e) {
  //   e.preventDefault();
  //   var languageCode = null;
  //   getCurrentLanguageCode(function (code) {
  //     languageCode = code;
  //     var confirmMessage = downloadMessages[languageCode];
  //     // Use SweetAlert for the confirmation dialog
  //     Swal.fire({
  //       text: confirmMessage,
  //       icon: 'question',
  //       showCancelButton: true,
  //       confirmButtonColor: '#008000',
  //       cancelButtonColor: '#d33',
  //       confirmButtonText: 'Confirm'
  //     }).then(function(result) {
  //       if (result.isConfirmed) {
  //         $.ajax({
  //           type: "GET",
  //           url: "/project/project-import",
  //           dataType: "binary",
  //           xhrFields: {
  //             responseType: "blob",
  //           },
  //           success: function (response) {
  //             const file = new Blob([response], {
  //               type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  //             });
  //             const url = URL.createObjectURL(file);
  //             const link = document.createElement("a");
  //             link.href = url;
  //             link.download = "project_template.xlsx";
  //             document.body.appendChild(link);
  //             link.click();
  //           },
  //           error: function (xhr, textStatus, errorThrown) {
  //             console.error("Error downloading file:", errorThrown);
  //           },
  //         });
  //       }
  //     });
  //   });
  // });

  // $('#importProject').click(function (e) {
  //   $.ajax({
  //     type: 'POST',
  //     url: '/project/project-import',
  //     dataType: 'binary',
  //     xhrFields: {
  //       responseType: 'blob'
  //     },
  //     success: function(response) {
  //       const file = new Blob([response], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
  //       const url = URL.createObjectURL(file);
  //       const link = document.createElement('a');
  //       link.href = url;
  //       link.download = 'project.xlsx';
  //       document.body.appendChild(link);
  //       link.click();
  //     },
  //     error: function(xhr, textStatus, errorThrown) {
  //       console.error('Error downloading file:', errorThrown);
  //     }
  //   });
  // });


  $(".all-projects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-project-row").prop("checked", true);
    } else {
      $(".all-project-row").prop("checked", false);
    }
  });

  $("#exportProject").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = exportMessages[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
      var checkedRows = $(".all-project-row").filter(":checked");
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
            var checkedRows = $(".all-project-row").filter(":checked");
            ids = [];
            checkedRows.each(function () {
              ids.push($(this).attr("id"));
            });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-export",
              dataType: "binary",
              xhrFields: {
              responseType: "blob",
              },
              data: {
                csrfmiddlewaretoken: getCookie("csrftoken"),
                ids: JSON.stringify(ids),
              },
              success: function (response, textStatus, jqXHR) {
                const file = new Blob([response], {
                  type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                });
                const url = URL.createObjectURL(file);
                const link = document.createElement("a");
                link.href = url;
                link.download = "project details.xlsx";
                document.body.appendChild(link);
                link.click();
              },
            });
          }
        });
      }
    });
  });

  $(document).on('click', '#exportProject', function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = exportMessages[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
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
            // var checkedRows = $(".all-project-row").filter(":checked");
            // ids = [];
            // checkedRows.each(function () {
            //   ids.push($(this).attr("id"));
            // });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-export",
              dataType: "binary",
              xhrFields: {
              responseType: "blob",
              },
              data: {
                csrfmiddlewaretoken: getCookie("csrftoken"),
                ids: JSON.stringify(ids),
              },
              success: function (response, textStatus, jqXHR) {
                const file = new Blob([response], {
                  type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                });
                const url = URL.createObjectURL(file);
                const link = document.createElement("a");
                link.href = url;
                link.download = "project details.xlsx";
                document.body.appendChild(link);
                link.click();
              },
            });
          }
        });
      }
    });
  });


  $("#archiveProject").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = archiveMessagesSelected[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
      var checkedRows = $(".all-project-row").filter(":checked");
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
              url: "/project/project-bulk-archive?is_active=False",
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


  $(document).on('click', '#archiveProject', function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = archiveMessagesSelected[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
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
            // e.preventDefault();
            // ids = [];
            // checkedRows.each(function () {
            //   ids.push($(this).attr("id"));
            // });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-archive?is_active=False",
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


$("#unArchiveProject").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = unarchiveMessagesSelected[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
      var checkedRows = $(".all-project-row").filter(":checked");
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
            var checkedRows = $(".all-project-row").filter(":checked");
            ids = [];
            checkedRows.each(function () {
              ids.push($(this).attr("id"));
            });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-archive?is_active=True",
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

  $(document).on('click', '#unArchiveProject', function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = unarchiveMessagesSelected[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
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
            // var checkedRows = $(".all-project-row").filter(":checked");
            // ids = [];
            // checkedRows.each(function () {
            //   ids.push($(this).attr("id"));
            // });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-archive?is_active=True",
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

$("#deleteProject").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessage[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
      var checkedRows = $(".all-project-row").filter(":checked");
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
            var checkedRows = $(".all-project-row").filter(":checked");
            ids = [];
            checkedRows.each(function () {
              ids.push($(this).attr("id"));
            });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-delete",
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


  $(document).on('click', '#deleteProject', function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessage[languageCode];
      var textMessage = norowMessagesSelected[languageCode];
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
          icon: "error",
          showCancelButton: true,
          confirmButtonColor: "#008000",
          cancelButtonColor: "#d33",
          confirmButtonText: "Confirm",
        }).then(function (result) {
          if (result.isConfirmed) {
            // var checkedRows = $(".all-project-row").filter(":checked");
            // ids = [];
            // checkedRows.each(function () {
            //   ids.push($(this).attr("id"));
            // });

            $.ajax({
              type: "POST",
              url: "/project/project-bulk-delete",
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
