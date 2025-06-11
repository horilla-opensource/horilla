var excelMessages = {
    ar: "هل ترغب في تنزيل ملف Excel؟",
    de: "Möchten Sie die Excel-Datei herunterladen?",
    es: "¿Desea descargar el archivo de Excel?",
    en: "Do you want to download the excel file?",
    fr: "Voulez-vous télécharger le fichier Excel?",
  };

  var archiveMessages = {
    ar: "هل ترغب حقًا في أرشفة كل الحضور المحدد؟",
    de: "Möchten Sie wirklich alle ausgewählten Anwesenheiten archivieren?",
    es: "Realmente quieres archivar todas las asistencias seleccionadas?",
    en: "Do you really want to archive all the selected allocations?",
    fr: "Voulez-vous vraiment archiver toutes les présences sélectionnées?",
  };

  var unarchiveMessages = {
    ar: "هل ترغب حقًا في إلغاء أرشفة كل الحضور المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten archivierten Zuweisungen wiederherstellen?",
    es: "Realmente quieres desarchivar todas las asignaciones seleccionadas?",
    en: "Do you really want to un-archive all the selected allocations?",
    fr: "Voulez-vous vraiment désarchiver toutes les allocations sélectionnées?",
  };

  var rotatedeleteRequestMessages = {
    ar: "هل ترغب حقًا في حذف كل الحجوزات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Zuweisungen löschen?",
    es: "Realmente quieres eliminar todas las asignaciones seleccionadas?",
    en: "Do you really want to delete all the selected Requests?",
    fr: "Voulez-vous vraiment supprimer toutes les allocations sélectionnées?",
  };

  var approveMessages = {
    ar: "هل ترغب حقًا في الموافقة على جميع الطلبات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anfragen genehmigen?",
    es: "Realmente quieres aprobar todas las solicitudes seleccionadas?",
    en: "Do you really want to approve all the selected requests?",
    fr: "Voulez-vous vraiment approuver toutes les demandes sélectionnées?",
  };
  var rejectMessages = {
    ar: "هل تريد حقًا رفض جميع الطلبات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anfragen ablehnen?",
    es: "¿Realmente deseas rechazar todas las solicitudes seleccionadas?",
    en: "Do you really want to reject all the selected requests?",
    fr: "Voulez-vous vraiment rejeter toutes les demandes sélectionnées?",
  };
  var requestDeleteMessages = {
    ar: "هل ترغب حقًا في حذف جميع الطلبات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anfragen löschen?",
    es: "Realmente quieres eliminar todas las solicitudes seleccionadas?",
    en: "Do you really want to delete all the selected requests?",
    fr: "Voulez-vous vraiment supprimer toutes les demandes sélectionnées?",
  };
  var norowMessages = {
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

  tickShiftCheckboxes();
  function makeShiftListUnique(list) {
    return Array.from(new Set(list));
  }

  tickWorktypeCheckboxes();
  function makeWorktypeListUnique(list) {
    return Array.from(new Set(list));
  }

  tickRShiftCheckboxes();
  function makeRShiftListUnique(list) {
    return Array.from(new Set(list));
  }

  tickRWorktypeCheckboxes();
  function makeRWorktypeListUnique(list) {
    return Array.from(new Set(list));
  }

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


  function handleApproveRequestsClick() {
     // e.preventDefault();
     var languageCode = null;
     getCurrentLanguageCode(function (code) {
       languageCode = code;
       var confirmMessage = approveMessages[languageCode];
       var textMessage = norowMessages[languageCode];
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
           icon: "success",
           showCancelButton: true,
           confirmButtonColor: "#008000",
           cancelButtonColor: "#d33",
           confirmButtonText: "Confirm",
         }).then(function (result) {
           if (result.isConfirmed) {
             ids = [];
             ids.push($("#selectedInstances").attr("data-ids"));
             ids = JSON.parse($("#selectedInstances").attr("data-ids"));
             $.ajax({
               type: "POST",
               url: "/work-type-request-bulk-approve",
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
    }



function handleRejectRequestsClick() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = rejectMessages[languageCode];
      var textMessage = norowMessages[languageCode];
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
          icon: "warning",
          showCancelButton: true,
          confirmButtonColor: "#008000",
          cancelButtonColor: "#d33",
          confirmButtonText: "Confirm",
        }).then(function (result) {
          if (result.isConfirmed) {
            console.log("hello")
            ids = [];
            ids.push($("#selectedInstances").attr("data-ids"));
            ids = JSON.parse($("#selectedInstances").attr("data-ids"));
            $.ajax({
              type: "POST",
              url: "/work-type-request-bulk-cancel",
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
  }

  function handleDeleteRequestsClick() {
    var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = rotatedeleteRequestMessages[languageCode];
    var textMessage = norowMessages[languageCode];
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
          ids = [];
          ids.push($("#selectedInstances").attr("data-ids"));
          ids = JSON.parse($("#selectedInstances").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/work-type-request-bulk-delete",
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
  }

  //scripts for rotating work type page
  //bulk archive in rotate work type
  $(document).on('click', '#archiveWorkRotateNav', function(e) {

    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = archiveMessages[languageCode];
      var textMessage = norowMessages[languageCode];
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
            ids = [];
            ids.push($("#selectedInstances").attr("data-ids"));
            ids = JSON.parse($("#selectedInstances").attr("data-ids"));
            $.ajax({
              type: "POST",
              url: "/rotating-work-type-assign-bulk-archive?is_active=False",
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


  function UnarchiveWorkRotateNav() {
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = unarchiveMessages[languageCode];
      var textMessage = norowMessages[languageCode];
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
            ids = [];
            ids.push($("#selectedInstances").attr("data-ids"));
            ids = JSON.parse($("#selectedInstances").attr("data-ids"));
            $.ajax({
              type: "POST",
              url: "/rotating-work-type-assign-bulk-archive?is_active=True",
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
  }

  function deleteWorkRotateNav() {

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = rotatedeleteRequestMessages[languageCode];
      var textMessage = norowMessages[languageCode];
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
            ids = [];
            ids.push($("#selectedInstances").attr("data-ids"));
            ids = JSON.parse($("#selectedInstances").attr("data-ids"));
            $.ajax({
              type: "POST",
              url: "/rotating-work-type-assign-bulk-delete",
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
  }
