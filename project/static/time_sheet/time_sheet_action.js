
var archiveMessages = {
    // ar: "هل ترغب حقًا في أرشفة جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter archivieren?",
    // es: "¿Realmente quieres archivar a todos los empleados seleccionados?",
    en: "Do you really want to archive all the selected timesheet?",
    // fr: "Voulez-vous vraiment archiver tous les employés sélectionnés ?",
  };

  var unarchiveMessages = {
    // ar: "هل ترغب حقًا في إلغاء أرشفة جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter aus der Archivierung zurückholen?",
    // es: "¿Realmente quieres desarchivar a todos los empleados seleccionados?",
    en: "Do you really want to unarchive all the selected timesheet?",
    // fr: "Voulez-vous vraiment désarchiver tous les employés sélectionnés?",
  };

  var deleteMessagesBulk = {
    // ar: "هل ترغب حقًا في حذف جميع الموظفين المحددين؟",
    // de: "Möchten Sie wirklich alle ausgewählten Mitarbeiter löschen?",
    // es: "¿Realmente quieres eliminar a todos los empleados seleccionados?",
    en: "Do you really want to delete all the selected timesheet?",
    // fr: "Voulez-vous vraiment supprimer tous les employés sélectionnés?",
  };

  var norowMessages = {
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
  $(".all-time-sheet").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-time-sheet-row").prop("checked", true);
    } else {
      $(".all-time-sheet-row").prop("checked", false);
    }
  });


$("#deleteTimeSheet").click(function (e) {
    e.preventDefault();
    var languageCode = null;
    getCurrentLanguageCode(function (code) {
      languageCode = code;
      var confirmMessage = deleteMessagesBulk[languageCode];
      var textMessage = norowMessages[languageCode];
      var checkedRows = $(".all-time-sheet-row").filter(":checked");
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
            var checkedRows = $(".all-time-sheet-row").filter(":checked");
            ids = [];
            checkedRows.each(function () {
              ids.push($(this).attr("id"));
            });

            $.ajax({
              type: "POST",
              url: "/project/time-sheet-bulk-delete",
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


  function deleteTimeSheet(){
     var languageCode = null;
     getCurrentLanguageCode(function (code) {
       languageCode = code;
       var confirmMessage = deleteMessagesBulk[languageCode];
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
             // var checkedRows = $(".all-time-sheet-row").filter(":checked");
             // ids = [];
             // checkedRows.each(function () {
             //   ids.push($(this).attr("id"));
             // });

             $.ajax({
               type: "POST",
               url: "/project/time-sheet-bulk-delete",
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
   };
