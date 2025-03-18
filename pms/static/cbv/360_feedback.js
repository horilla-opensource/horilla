var archiveMessagedata = {
    ar: "هل ترغب حقاً في أرشفة كل التعليقات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Rückmeldungen archivieren?",
    es: "¿Realmente quieres archivar todas las retroalimentaciones seleccionadas?",
    en: "Do you really want to archive all the selected feedbacks?",
    fr: "Voulez-vous vraiment archiver tous les retours sélectionnés?",
  };
  
  var unarchiveMessagedata = {
    ar: "هل ترغب حقاً في إلغاء الأرشفة عن كل التعليقات المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Rückmeldungen aus der Archivierung nehmen?",
    es: "¿Realmente quieres desarchivar todas las retroalimentaciones seleccionadas?",
    en: "Do you really want to unarchive all the selected feedbacks?",
    fr: "Voulez-vous vraiment désarchiver tous les retours sélectionnés?",
  };
  
  var deleteMessagedata = {
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

  

$(document).on('click', '#archiveFeedback', function(e) {
              e.preventDefault();
            
              var languageCode = null;
              getCurrentLanguageCode(function(code) {
                languageCode = code;
            
                var confirmMessage = archiveMessagedata[languageCode];
                var textMessage = norowMessages[languageCode];
            
                var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
                var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];
      
                if (announy_ids.length > 0) {
                  ids = []; 
                }
            
                if (ids.length === 0 && announy_ids.length === 0) {
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
                  }).then(function(result) {
                    if (result.isConfirmed) {
                      $.ajax({
                        type: "POST",
                        url: "/pms/feedback-bulk-archive?is_active=False",
                        data: {
                          csrfmiddlewaretoken: getCookie("csrftoken"),
                          ids: JSON.stringify(ids),
                          announy_ids: JSON.stringify(announy_ids),
                        },
                        success: function(response, textStatus, jqXHR) {
                          if (jqXHR.status === 200) {
                            window.location.reload();
                          } else {
                          }
                        },
                      });
                    }
                  });
                }
              });
            });


$(document).on('click', '#UnarchiveFeedback', function(e) {
              e.preventDefault();
            
              var languageCode = null;
              getCurrentLanguageCode(function(code) {
                languageCode = code;
            
                var confirmMessage = unarchiveMessagedata[languageCode];
                var textMessage = norowMessages[languageCode];
            
                var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
                var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];
      
                if (announy_ids.length > 0) {
                  ids = []; 
                }
            
                if (ids.length === 0 && announy_ids.length === 0) {
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
                  }).then(function(result) {
                    if (result.isConfirmed) {
                      $.ajax({
                        type: "POST",
                        url: "/pms/feedback-bulk-archive?is_active=True",
                        data: {
                          csrfmiddlewaretoken: getCookie("csrftoken"),
                          ids: JSON.stringify(ids),
                          announy_ids: JSON.stringify(announy_ids),
                        },
                        success: function(response, textStatus, jqXHR) {
                          if (jqXHR.status === 200) {
                            window.location.reload();
                          } else {
                          }
                        },
                      });
                    }
                  });
              }
        });
  });

$(document).on('click', '#deleteFeedback', function(e) {
      e.preventDefault();
    
      var languageCode = null;
      getCurrentLanguageCode(function(code) {
        languageCode = code;
    
        var confirmMessage = deleteMessagedata[languageCode];
        var textMessage = norowMessages[languageCode];
    
        var ids = JSON.parse($("#selectedInstances").attr("data-ids")) || [];
        console.log(ids)
        var announy_ids = JSON.parse($("#anounyselectedInstances").attr("data-ids")) || [];
    
        if (ids.length === 0 && announy_ids.length === 0) {
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
          }).then(function(result) {
            if (result.isConfirmed) {
              $.ajax({
                type: "POST",
                url: "/pms/feedback-bulk-delete",
                data: {
                  csrfmiddlewaretoken: getCookie("csrftoken"),
                  ids: JSON.stringify(ids),
                  announy_ids: JSON.stringify(announy_ids),
                },
                success: function(response, textStatus, jqXHR) {
                  if (jqXHR.status === 200) {
                    window.location.reload();
                  } else {
                  }
                },
              });
            }
          });
        }
      });
    });




      
