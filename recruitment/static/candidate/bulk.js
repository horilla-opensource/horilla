var archivecanMessages = {
    ar: "هل ترغب حقًا في أرشفة جميع المرشحين المحددين؟",
    de: "Möchten Sie wirklich alle ausgewählten Kandidaten archivieren?",
    es: "¿Realmente deseas archivar a todos los candidatos seleccionados?",
    en: "Do you really want to archive all the selected candidates?",
    fr: "Voulez-vous vraiment archiver tous les candidats sélectionnés?",
};

  
var unarchivecanMessages = {
    ar: "هل ترغب حقًا في إلغاء أرشفة جميع المرشحين المحددين؟",
    de: "Möchten Sie wirklich alle ausgewählten Kandidaten aus der Archivierung nehmen?",
    es: "¿Realmente deseas desarchivar a todos los candidatos seleccionados?",
    en: "Do you really want to unarchive all the selected candidates?",
    fr: "Voulez-vous vraiment désarchiver tous les candidats sélectionnés?",
};

  
var deletecanMessages = {
  ar: "هل ترغب حقًا في حذف جميع المرشحين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Kandidaten löschen?",
    es: "¿Realmente deseas eliminar a todos los candidatos seleccionados?",
    en: "Do you really want to delete all the selected candidates?",
    fr: "Voulez-vous vraiment supprimer tous les candidats sélectionnés?",
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

tickcandidateCheckboxes();

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
      console.log(response);
      var languageCode = response.language_code;
      callback(languageCode); // Pass the language code to the callback
    },
  });
}


$(".all-candidate").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-candidate-row").prop("checked", true);
    } else {
        $(".all-candidate-row").prop("checked", false);
    }
    addingcandidateIds()
});

$(".all-candidate-row").change(function(){
    addingcandidateIds()
})


function addingcandidateIds(){
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-candidate-row").each(function() {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });
  var ids = makeListUnique1(ids);
  var selectedCount = ids.length;
  
  getCurrentLanguageCode(function(code){
    languageCode = code;
    var message = rowMessages[languageCode];

    $("#selectedInstances").attr("data-ids", JSON.stringify(ids)); 
    $('#selectedshow').text(selectedCount + ' -' + message);
  })

}


function tickcandidateCheckboxes() {
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var uniqueIds = makeListUnique1(ids)
  var selectedCount = uniqueIds.length;
  var message1 = rowMessages[languageCode];


  $('#selectedshow').text(selectedCount + ' -' + message1);
  click = $("#selectedInstances").attr("data-clicked")
  if ( click === '1'){
    $(".all-candidate").prop('checked',true)
    $('#Allcandidate').prop('checked',true)
  }
  uniqueIds.forEach(function(id) {
    $('#' + id).prop('checked', true);
  });

  getCurrentLanguageCode(function(code){
    languageCode = code;
    var message1 = rowMessages[languageCode];
    $('#selectedshow').text(selectedCount + ' -' + message1);
  })

}


function makeListUnique1(list) {
  return Array.from(new Set(list));
}



$("#archiveCandidates").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = archivecanMessages[languageCode];
      var textMessage = rowMessages[languageCode];
      var checkedRows = $(".all-candidate-row").filter(":checked");
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

                ids.push($("#selectedInstances").attr("data-ids"))
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                
            $.ajax({
                type: "POST",
                url: "/recruitment/candidate-bulk-archive?is_active=False",
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

$("#unArchiveCandidates").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = unarchivecanMessages[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".all-candidate-row").filter(":checked");
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

                ids.push($("#selectedInstances").attr("data-ids"))
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                
                $.ajax({
                    type: "POST",
                    url: "/recruitment/candidate-bulk-archive?is_active=True",
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

$("#deleteCandidates").click(function (e) {
    e.preventDefault();

    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deletecanMessages[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".all-candidate-row").filter(":checked");
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

                ids.push($("#selectedInstances").attr("data-ids"))
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));
                
                $.ajax({
                    type: "POST",
                    url: "/recruitment/candidate-bulk-delete",
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
