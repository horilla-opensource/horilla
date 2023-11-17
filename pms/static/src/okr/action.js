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

var rowMessages = {
  ar: " تم الاختيار",
  de: " Ausgewählt",
  es: " Seleccionado",
  en: " Selected",
  fr: " Sélectionné",
};

tickObjectivesCheckboxes();
function makeObjectivesListUnique(list) {
  return Array.from(new Set(list));
}

$(".all-objects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-objects-row").prop("checked", true)
        .closest(".oh-sticky-table__tr")
        .addClass("highlight-selected");
    } else {
        $(".all-objects-row").prop("checked", false)
        .closest(".oh-sticky-table__tr")
        .removeClass("highlight-selected");
    }
});

$(".own-objects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".own-objects-row").prop("checked", true)
        .closest(".oh-sticky-table__tr")
        .addClass("highlight-selected");
    } else {
        $(".own-objects-row").prop("checked", false)
        .closest(".oh-sticky-table__tr")
        .removeClass("highlight-selected");
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


function tickObjectivesCheckboxes() {
  var ids = JSON.parse($("#selectedObjectives").attr("data-ids") || "[]");
  uniqueIds = makeObjectivesListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedObjectives").attr("data-clicked");
  if (click === "1") {
    var tableName = localStorage.getItem('activeTabPms');
    if (tableName === '#tab_1'){
      tableName = 'self'
      $('.own-objects').prop('checked',true)
    }
    else{
      tableName = 'all'    
      $('.all-objects').prop('checked',true)
      $('.own-objects').prop('checked',true)
    }
  }
  uniqueIds.forEach(function (id) {
    $("#" + id).prop("checked", true).closest(".oh-sticky-table__tr")
    .addClass("highlight-selected");
  });
  var selectedCount = uniqueIds.length;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#exportObjectives").css("display", "inline-flex");
      $("#selectedShowObjectives").css("display", "inline-flex");
      $("#selectedShowObjectives").text(selectedCount + " -" + message);
    } else {
      $("#selectedShowObjectives").css("display", "none");
      $("#exportObjectives").css("display", "none");
    }
  });
}

function addingObjectivesIds() {
  var ids = JSON.parse($("#selectedObjectives").attr("data-ids") || "[]");
  var selectedCount = 0;
  var tableName = localStorage.getItem('activeTabPms');
  if (tableName === '#tab_1'){
    tableName = 'self'
    $(".own-objects-row").each(function () {
      if ($(this).is(":checked")) {
        ids.push(this.id);
      } else {
        var index = ids.indexOf(this.id);
        if (index > -1) {
          ids.splice(index, 1);
        }
      }
    });
  }
  else{
    tableName = 'all'  
    $(".all-objects-row").each(function () {
      if ($(this).is(":checked")) {
        ids.push(this.id);
      } else {
        var index = ids.indexOf(this.id);
        if (index > -1) {
          ids.splice(index, 1);
        }
      }
    });  
  }

  ids = makeObjectivesListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedObjectives").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#selectedShowObjectives").css("display", "none");
      $("#exportObjectives").css("display", "none");
    } else {
      $("#exportObjectives").css("display", "inline-flex");
      $("#selectedShowObjectives").css("display", "inline-flex");
      $("#selectedShowObjectives").text(selectedCount + " - " + message);
    }
  });
}

function selectAllObjectives() {
  $("#selectedObjectives").attr("data-clicked", 1);
  $("#selectedShowObjectives").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
  var tableName = localStorage.getItem('activeTabPms');
  if (tableName === '#tab_1'){
    tableName = 'self'
    $('.own-objects').prop('checked',true)
  }
  else{
    tableName = 'all'    
    $('.all-objects').prop('checked',true)
    $('.own-objects').prop('checked',true)
  }
  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/pms/objective-select-filter",
      data: { page: "all", filter: JSON.stringify(filter), "tableName":tableName },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true);
        }
        $("#selectedObjectives").attr("data-ids", JSON.stringify(employeeIds));

        count = makeObjectivesListUnique(employeeIds);
        tickObjectivesCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/pms/objective-select",
      data: { page: "all", "tableName": tableName },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var employeeIds = response.employee_ids;

        for (var i = 0; i < employeeIds.length; i++) {
          var empId = employeeIds[i];
          $("#" + empId).prop("checked", true).closest(".oh-sticky-table__tr")
          .addClass("highlight-selected");
        }
        var previousIds = $("#selectedObjectives").attr("data-ids");
        $("#selectedObjectives").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...employeeIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeObjectivesListUnique(employeeIds);
        tickObjectivesCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllObjectives() {
  $("#selectedObjectives").attr("data-clicked", 0);
  var tableName = localStorage.getItem('activeTabPms');
  if (tableName === '#tab_1'){
    tableName = 'self'
    $('.own-objects').prop('checked',false)
  }
  else{
    tableName = 'all'
    $('.all-objects').prop('checked',false)
    $('.own-objects').prop('checked',false)
  }
  $.ajax({
    url: "/pms/objective-select",
    data: { page: "all", filter: "{}", "tableName": tableName },
    type: "GET",
    dataType: "json",
    success: function (response) {
      var employeeIds = response.employee_ids;

      for (var i = 0; i < employeeIds.length; i++) {
        var empId = employeeIds[i];
        $("#" + empId).prop("checked", false)
        .closest(".oh-sticky-table__tr")
        .removeClass("highlight-selected");
      }
      var ids = JSON.parse($("#selectedObjectives").attr("data-ids") || "[]");
      var uniqueIds = makeObjectivesListUnique(ids);
      toggleHighlight(uniqueIds);

      $("#selectedObjectives").attr("data-ids", JSON.stringify([]));

      count = [];
      tickObjectivesCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
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
      ids = [];
      ids.push($("#selectedObjectives").attr("data-ids"));
      ids = JSON.parse($("#selectedObjectives").attr("data-ids"));
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
            ids.push($("#selectedObjectives").attr("data-ids"));
            ids = JSON.parse($("#selectedObjectives").attr("data-ids"));
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
      ids = [];
      ids.push($("#selectedObjectives").attr("data-ids"));
      ids = JSON.parse($("#selectedObjectives").attr("data-ids"));
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
                ids.push($("#selectedObjectives").attr("data-ids"));
                ids = JSON.parse($("#selectedObjectives").attr("data-ids"));
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
      ids = [];
      ids.push($("#selectedObjectives").attr("data-ids"));
      ids = JSON.parse($("#selectedObjectives").attr("data-ids"));
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
                ids.push($("#selectedObjectives").attr("data-ids"));
                ids = JSON.parse($("#selectedObjectives").attr("data-ids"));                
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
