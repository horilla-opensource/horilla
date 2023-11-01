var archiveMessages = {
  ar: "هل ترغب حقًا في أرشفة جميع الموظفين المحددين؟",
  de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter archivieren?",
  es: "¿Realmente quieres archivar a todos los empleados seleccionados?",
  en: "Do you really want to archive all the selected employees?",
  fr: "Voulez-vous vraiment archiver tous les employés sélectionnés ?",
};

var unarchiveMessages = {
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

var norowMessages = {
  ar: "لم يتم تحديد أي صفوف.",
  de: "Es wurden keine Zeilen ausgewählt.",
  es: "No se han seleccionado filas.",
  en: "No rows have been selected.",
  fr: "Aucune ligne n'a été sélectionnée.",
};

var selectedemployees = {
  ar: " موظفون محددون",
  de: " Ausgewählte Mitarbeiter",
  es: " Empleados seleccionados",
  en: " Selected Employees",
  fr: " Employés sélectionnés",
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

$(".all-employee").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-employee-row").prop("checked", true);
  } else {
    $(".all-employee-row").prop("checked", false);
  }
  addingIds()
});


$(".all-employee-row").change(function(){
  addingIds()
})


function addingIds(){
  var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
  var selectedCount = 0;

  $(".all-employee-row").each(function() {
    if ($(this).is(":checked")) {
      ids.push(this.id);
    } else {
      var index = ids.indexOf(this.id);
      if (index > -1) {
        ids.splice(index, 1);
      }
    }
  });
  var ids = makeListUnique(ids);
  var selectedCount = ids.length;
  
  getCurrentLanguageCode(function(code){
    languageCode = code;
    var message = selectedemployees[languageCode];

    $("#selectedInstances").attr("data-ids", JSON.stringify(ids)); 
    $('#selectedshow').text(selectedCount + ' -' + message);
  })

}


function tickCheckboxes(uniqueIds) {
  
  click = $("#selectedInstances").attr("data-clicked")
  if ( click === '1'){
    $(".all-employee").prop('checked',true)
  }

  uniqueIds.forEach(function(id) {
    $('#' + id).prop('checked', true);
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function(code){
    languageCode = code;
    var message = selectedemployees[languageCode];
    $('#selectedshow').text(selectedCount + ' -' + message);
  })

}


function makeListUnique(list) {
  return Array.from(new Set(list));
}

var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
tickCheckboxes(ids);

$("#archiveEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = archiveMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".all-employee-row").filter(":checked");
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
});

$("#unArchiveEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = unarchiveMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".all-employee-row").filter(":checked");
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
});

$("#deleteEmployees").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".all-employee-row").filter(":checked");
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
});

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});