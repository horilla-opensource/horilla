
var downloadMessages = {
    ar: "هل ترغب في تنزيل القالب؟",
    de: "Möchten Sie die Vorlage herunterladen?",
    es: "¿Quieres descargar la plantilla?",
    en: "Do you want to download the template?",
    fr: "Voulez-vous télécharger le modèle ?",
  };
  
  var importSuccess = {
    ar: "نجح الاستيراد", // Arabic
    de: "Import erfolgreich", // German
    es: "Importado con éxito", // Spanish
    en: "Imported Successfully!", // English
    fr: "Importation réussie", // French
  };
  
  var uploadSuccess = {
    ar: "تحميل كامل", // Arabic
    de: "Upload abgeschlossen", // German
    es: "Carga completa", // Spanish
    en: "Upload Complete!", // English
    fr: "Téléchargement terminé", // French
  };
  
  var uploadingMessage = {
    ar: "جارٍ الرفع",
    de: "Hochladen...",
    es: "Subiendo...",
    en: "Uploading...",
    fr: "Téléchargement en cours...",
  };
  
  var validationMessage = {
    ar: "يرجى تحميل ملف بامتداد .xlsx فقط.",
    de: "Bitte laden Sie nur eine Datei mit der Erweiterung .xlsx hoch.",
    es: "Por favor, suba un archivo con la extensión .xlsx solamente.",
    en: "Please upload a file with the .xlsx extension only.",
    fr: "Veuillez télécharger uniquement un fichier avec l'extension .xlsx.",
  };

  var excelMessages = {
    ar: "هل ترغب في تنزيل ملف Excel؟",
    de: "Möchten Sie die Excel-Datei herunterladen?",
    es: "¿Desea descargar el archivo de Excel?",
    en: "Do you want to download the excel file?",
    fr: "Voulez-vous télécharger le fichier Excel?",
  };
  var archiveMessagesEmployee = {
    ar: "هل ترغب حقًا في أرشفة جميع الموظفين المحددين؟",
    de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter archivieren?",
    es: "¿Realmente quieres archivar a todos los empleados seleccionados?",
    en: "Do you really want to archive all the selected employees?",
    fr: "Voulez-vous vraiment archiver tous les employés sélectionnés ?",
  };
  
  var unarchiveMessagesEmployees = {
    ar: "هل ترغب حقًا في إلغاء أرشفة جميع الموظفين المحددين؟",
    de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter aus der Archivierung zurückholen?",
    es: "¿Realmente quieres desarchivar a todos los empleados seleccionados?",
    en: "Do you really want to unarchive all the selected employees?",
    fr: "Voulez-vous vraiment désarchiver tous les employés sélectionnés?",
  };
  
  var deleteMessages = {
    ar: "هل ترغب حقًا في حذف جميع الموظفين المحددين؟",
    de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter löschen?",
    es: "¿Realmente quieres eliminar a todos los empleados seleccionados?",
    en: "Do you really want to delete all the selected employees?",
    fr: "Voulez-vous vraiment supprimer tous les employés sélectionnés?",
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

  var form = document.getElementById("workInfoImportForm");

  // Add an event listener to the form submission
  form.addEventListener("submit", function (event) {
    // Prevent the default form submission
    event.preventDefault();
  
    // Create a new form data object
    $(".oh-dropdown__import-form").css("display", "none");
    $("#uploading").css("display", "block");
    var formData = new FormData();
  
    // Append the file to the form data object
    var fileInput = document.querySelector("#workInfoImportFile");
    formData.append("file", fileInput.files[0]);
    $.ajax({
      type: "POST",
      url: "/employee/work-info-import",
      dataType: "binary",
      data: formData,
      processData: false,
      contentType: false,
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
      xhrFields: {
        responseType: "blob",
      },
      success: function (response, textStatus, xhr) {
        var errorCount = xhr.getResponseHeader('X-Error-Count');
        if (typeof response === 'object' && response.type == 'application/json') {
          var reader = new FileReader();
  
          reader.onload = function() {
            var json = JSON.parse(reader.result);
  
            if(json.success_count > 0) {
              Swal.fire({
                text: `${json.success_count} Employees Imported Successfully`,
                icon: "success",
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true,
              }).then(function() {
                window.location.reload();
              });
            }
          }
          reader.readAsText(response);
          return;
        }
        if (!$(".file-xlsx-validation").length) {
          swal.fire({
            text: `You have ${errorCount} errors. Do you want to download the error list?`,
            icon: "error",
            showCancelButton: true,
            showDenyButton: true,
            confirmButtonText: "Download error list & Skip Import",
            denyButtonText: "Downlod error list & Continue Import",
            cancelButtonText: "Cancel",
            confirmButtonColor: "#d33",
            denyButtonColor: "#008000",
            customClass: {
              container: 'custom-swal-container'
            }
          })
          .then((result) => {
            if (result.isConfirmed) {
              const file = new Blob([response], {
                type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              });
              const url = URL.createObjectURL(file);
              const link = document.createElement("a");
              link.href = url;
              link.download = "ImportError.xlsx";
              document.body.appendChild(link);
              link.click();
              window.location.reload();
            }
            else if (result.isDenied) {
              formData.append("create_work_info", true);
              $.ajax({
                type: "POST",
                url: "/employee/work-info-import",
                dataType: "binary",
                data: formData,
                processData: false,
                contentType: false,
                headers: {
                  "X-CSRFToken": getCookie("csrftoken"),
                },
                xhrFields: {
                  responseType: "blob",
                },
                success: function (response, textStatus, xhr) {
                  Swal.fire({
                    text: `Employees Imported Successfully`,
                    icon: "success",
                    showConfirmButton: false,
                    timer: 3000,
                    timerProgressBar: true,
                  }).then(function() {
                    const file = new Blob([response], {
                      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "ImportError.xlsx";
                    document.body.appendChild(link);
                    link.click();
                    window.location.reload();
                  });
  
                  return;
                }
              })
            }
            else {
              $(".oh-dropdown__import-form").css("display", "block");
              $("#uploading").css("display", "none");
            }
          });
        }
  
      },
      error: function (xhr, textStatus, errorThrown) {
        console.error("Error downloading file:", errorThrown);
      },
    });
  });
  
  

$(document).on("click", "#work-info-import", function (e) {
    e.preventDefault();
    getCurrentLanguageCode(function (code) {
      var languageCode = code;
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
          $("#loading").show();
  
          var xhr = new XMLHttpRequest();
          xhr.open("GET", "/employee/work-info-import", true);
          xhr.responseType = "arraybuffer";

          xhr.upload.onprogress = function (e) {
            if (e.lengthComputable) {
              var percent = (e.loaded / e.total) * 100;
              $(".progress-bar")
                .width(percent + "%")
                .attr("aria-valuenow", percent);
              $("#progress-text").text(
                "Uploading... " + percent.toFixed(2) + "%"
              );
            }
          };
  
          xhr.onload = function (e) {
            if (this.status == 200) {
              const file = new Blob([this.response], {
                type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              });
              const url = URL.createObjectURL(file);
              const link = document.createElement("a");
              link.href = url;
              link.download = "work_info_template.xlsx";
              document.body.appendChild(link);
              link.click();
            }
          };
  
  
          xhr.onerror = function () {
            console.error("Error downloading file:", xhr.statusText);
          };
  
          xhr.onerror = function (e) {
            console.error("Error downloading file:", e);
          };
          xhr.send();
        }
      });
    });
  });
  $(document).ajaxStart(function () {
    $("#loading").show();
  });
  
  $(document).ajaxStop(function () {
    $("#loading").hide();
  });
  
  function simulateProgress() {
    getCurrentLanguageCode(function (code) {
      let progressBar = document.querySelector(".progress-bar");
      let progressText = document.getElementById("progress-text");
  
      let width = 0;
      let interval = setInterval(function () {
        if (width >= 100) {
          clearInterval(interval);
          progressText.innerText = uploadMessage;
          setTimeout(function () {
            document.getElementById("loading").style.display = "none";
          }, 3000);
          Swal.fire({
            text: importMessage,
            icon: "success",
            showConfirmButton: false,
            timer: 2000,
            timerProgressBar: true,
          });
          setTimeout(function () {
            $("#workInfoImport").removeClass("oh-modal--show");
            location.reload(true);
          }, 2000);
        } else {
          width++;
          progressBar.style.width = width + "%";
          progressBar.setAttribute("aria-valuenow", width);
          progressText.innerText = uploadingMessage[languageCode] + width + "%";
        }
      }, 20);
    });
  }
  
  

  $(document).on("click", "#archiveEmployees", function (e) {
    e.preventDefault();
    var languageCode = null;
    languageCode = $("#main-section-data").attr("data-lang");
    var confirmMessage =
    archiveMessagesEmployee[languageCode] ||
      ((languageCode = "en"), archiveMessages[languageCode]);
    var textMessage =
      noRowMessages[languageCode] ||
      ((languageCode = "en"), noRowMessages[languageCode]);
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
          ids = [];
          ids.push($("#selectedInstances").attr("data-ids"));
          ids = JSON.parse($("#selectedInstances").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/employee/employee-bulk-archive?is_active=False",
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


  $(document).on("click", "#unArchiveEmployees", function (e) {
    e.preventDefault();
    var languageCode = null;
    languageCode = $("#main-section-data").attr("data-lang");
    var confirmMessage =
    unarchiveMessagesEmployees[languageCode] ||
      ((languageCode = "en"), unarchiveMessages[languageCode]);
    var textMessage =
      noRowMessages[languageCode] ||
      ((languageCode = "en"), noRowMessages[languageCode]);
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
  
          ids = [];
  
          ids.push($("#selectedInstances").attr("data-ids"));
          ids = JSON.parse($("#selectedInstances").attr("data-ids"));
  
          $.ajax({
            type: "POST",
            url: "/employee/employee-bulk-archive?is_active=True",
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

  $(document).on("click", "#employeeBulkUpdateId", function (e) {
    var languageCode = null;
    languageCode = $("#main-section-data").attr("data-lang");
    var textMessage =
      noRowMessages[languageCode] ||
      ((languageCode = "en"), noRowMessages[languageCode]);
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (ids.length === 0) {
      $("#bulkUpdateModal").removeClass("oh-modal--show");
      Swal.fire({
        text: textMessage,
        icon: "warning",
        confirmButtonText: "Close",
      });
    } else {
      $("#id_bulk_employee_ids").val(JSON.stringify(ids));
      $("#bulkUpdateModal").addClass("oh-modal--show");
    }
  });


  $(document).on("click", "#deleteEmployees", function (e) {
    e.preventDefault();
    var languageCode = null;
    languageCode = $("#main-section-data").attr("data-lang");
    var confirmMessage =
      deleteMessages[languageCode] ||
      ((languageCode = "en"), deleteMessages[languageCode]);
    var textMessage =
      noRowMessages[languageCode] ||
      ((languageCode = "en"), noRowMessages[languageCode]);
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
          e.preventDefault();
  
          ids = [];
          ids.push($("#selectedInstances").attr("data-ids"));
          ids = JSON.parse($("#selectedInstances").attr("data-ids"));
  
          $.ajax({
            type: "POST",
            url: "/employee/employee-bulk-delete",
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
  
 
  
  