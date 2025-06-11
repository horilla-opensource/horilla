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
  var attendancedeleteMessages = {
    ar: "هل ترغب حقًا في حذف جميع الحضور المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anwesenheiten löschen?",
    es: "¿Realmente quieres eliminar todas las asistencias seleccionadas?",
    en: "Do you really want to delete all the selected attendances?",
    fr: "Voulez-vous vraiment supprimer toutes les présences sélectionnées?",
  };
  var noRowValidateMessages = {
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
  var rowMessages = {
    ar: " تم الاختيار",
    de: " Ausgewählt",
    es: " Seleccionado",
    en: " Selected",
    fr: " Sélectionné",
  };
  var excelMessages = {
    ar: "هل ترغب في تنزيل ملف Excel؟",
    de: "Möchten Sie die Excel-Datei herunterladen?",
    es: "¿Desea descargar el archivo de Excel?",
    en: "Do you want to download the excel file?",
    fr: "Voulez-vous télécharger le fichier Excel?",
  };
  var reqAttendanceApproveMessages = {
    ar: "هل ترغب حقًا في الموافقة على جميع طلبات الحضور المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anwesenheitsanfragen genehmigen?",
    es: "¿Realmente quieres aprobar todas las solicitudes de asistencia seleccionadas?",
    en: "Do you really want to approve all the selected attendance requests?",
    fr: "Voulez-vous vraiment approuver toutes les demandes de présence sélectionnées?",
  };
  
  var reqAttendanceApproveMessages = {
    ar: "هل ترغب حقًا في رفض جميع طلبات الحضور المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Anwesenheitsanfragen ablehnen?",
    es: "¿Realmente quieres rechazar todas las solicitudes de asistencia seleccionadas?",
    en: "Do you really want to reject all the selected attendance requests?",
    fr: "Voulez-vous vraiment rejeter toutes les demandes de présence sélectionnées?",
  };
  
  tickCheckboxes();
  function makeListUnique(list) {
    return Array.from(new Set(list));
  }
  
  tickactivityCheckboxes();
  function makeactivityListUnique(list) {
    return Array.from(new Set(list));
  }
  
  ticklatecomeCheckboxes();
  function makelatecomeListUnique(list) {
    return Array.from(new Set(list));
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

  

  
function deleteAttendanceNav() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = attendancedeleteMessages[languageCode];
      var textMessage = norowdeleteMessages[languageCode];
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
              url: "/attendance/attendance-activity-bulk-delete",
              data: {
                csrfmiddlewaretoken: getCookie("csrftoken"),
                ids: JSON.stringify(ids),
              },
              success: function (response, textStatus, jqXHR) {
                if (jqXHR.status === 200) {
                  location.reload();
                }
              },
            });
          }
        });
      }
    });
  }


  function importAttendanceNav() {      
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
            url: "/attendance/attendance-excel",
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
  }



  function importAttendanceActivity() {      
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
            url: "/attendance/attendance-activity-import-excel",
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
              link.download = "activity_excel.xlsx";
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
  }


  function bulkDeleteAttendanceNav() {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = attendancedeleteMessages[languageCode];
      var textMessage = norowdeleteMessages[languageCode];
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
              url: "/attendance/attendance-bulk-delete",
              data: {
                csrfmiddlewaretoken: getCookie("csrftoken"),
                ids: JSON.stringify(ids),
              },
              success: function (response, textStatus, jqXHR) {
                if (jqXHR.status === 200) {
                  location.reload();
                }
              },
            });
          }
        });
      }
    });
  }

  


  function showApproveAlert(dataReqValue) {
    Swal.fire({
        title: 'Pending Attendance Update Request!',
        text: 'An attendance request exists for updating this attendance prior to validation.',
        icon: 'warning',
        confirmButtonText: 'View Request',
        showCancelButton: true,
        cancelButtonText: 'Close',
        preConfirm: () => {
          // Redirect to the page based on dataReqValue
          localStorage.setItem("attendanceRequestActiveTab","#tab_1")
          window.location.href = dataReqValue;

      },
    });
  }


  function bulkValidateTabAttendance(dataReqValue) {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = validateMessages[languageCode];
      var textMessage = noRowValidateMessages[languageCode];
      ids = [];
      ids.push($("#validateselectedInstances").attr("data-ids"));
      ids = JSON.parse($("#validateselectedInstances").attr("data-ids"));
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
            ids.push($("#validateselectedInstances").attr("data-ids"));
            ids = JSON.parse($("#validateselectedInstances").attr("data-ids"));
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
  }
  
  function otBulkValidateTabAttendance(dataReqValue) {
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = overtimeMessages[languageCode];
      var textMessage = norowotMessages[languageCode];
      ids = [];
      ids.push($("#overtimeselectedInstances").attr("data-ids"));
      ids = JSON.parse($("#overtimeselectedInstances").attr("data-ids"));
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
            ids.push($("#overtimeselectedInstances").attr("data-ids"));
            ids = JSON.parse($("#overtimeselectedInstances").attr("data-ids"));
            
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
  }

  