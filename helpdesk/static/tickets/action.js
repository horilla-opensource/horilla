var TicketArchiveMessages = {
  ar: "",
  de: "",
  es: "",
  en: "Do you really want to archive all the selected tickets?",
  fr: "",
};

var ticketUnarchiveMessages = {
  ar: "",
  de: "",
  es: "",
  en: "Do you really want to unarchive all the selected tickets?",
  fr: "",
};

var ticketDeleteMessages = {
  ar: "",
  de: "",
  es: "",
  en: "Do you really want to delete all the selected tickets?",
  fr: "",
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

tickTicketsCheckboxes();
function makeTicketsListUnique(list) {
  return Array.from(new Set(list));
}

// TO recognize recently used tab
var activeTab = localStorage.getItem("activeTabTicket");
if (activeTab != null) {
  var tab = $(`[data-target="${activeTab}"]`);
  var tabContent = $(activeTab);
  $(tab).attr("class", "oh-tabs__tab oh-tabs__tab--active");
  $(tabContent).attr("class", "oh-tabs__content oh-tabs__content--active");
} else {
  $('[data-target="#tab_1"]').attr(
    "class",
    "oh-tabs__tab oh-tabs__tab--active"
  );
  $("#tab_1").attr("class", "oh-tabs__content oh-tabs__content--active");
}
$(".oh-tabs__tab").click(function (e) {
  var activeTab = $(this).attr("data-target");
  localStorage.setItem("activeTabTicket", activeTab);
});

// TO toggle class for select all button in All tickets tab
$(".allTicketsAll").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-tickets-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(".all-tickets-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

// TO toggle class for select all button in Allocated tickets tab
$(".allocatedTicketsAll").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".allocated-tickets-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(".allocated-tickets-row")
      .prop("checked", false)
      .closest(".oh-sticky-table__tr")
      .removeClass("highlight-selected");
  }
});

// TO toggle class for select all button in My tickets tab
$(".myTicketsAll").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".my-tickets-row")
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  } else {
    $(".my-tickets-row")
      .prop("checked", false)
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

// To get the current language code
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

// To mark tick on the selected checkboxes
function tickTicketsCheckboxes() {
  var ids = JSON.parse($("#selectedTickets").attr("data-ids") || "[]");
  uniqueIds = makeTicketsListUnique(ids);
  toggleHighlight(uniqueIds);
  click = $("#selectedTickets").attr("data-clicked");
  if (click === "1") {
    var tableName = localStorage.getItem("activeTabTicket");
    if (tableName === "#tab_1") {
      tableName = "my";
      $(".myTicketsAll").prop("checked", true);
    } else if (tableName === "#tab_2") {
      tableName = "allocated";
      $(".allocatedTicketsAll").prop("checked", true);
    } else {
      tableName = "all";
      $(".allTicketsAll").prop("checked", true);
      $(".myTicketsAll").prop("checked", true);
    }
  }
  uniqueIds.forEach(function (id) {
    $("#" + id)
      .prop("checked", true)
      .closest(".oh-sticky-table__tr")
      .addClass("highlight-selected");
  });
  var selectedCount = uniqueIds.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    if (selectedCount > 0) {
      $("#exportTickets").css("display", "inline-flex");
      $("#selectedShowTickets").css("display", "inline-flex");
      $("#selectedShowTickets").text(selectedCount + " -" + message);
      $('#unselectAllTickets').removeClass('d-none')
    } else {
      $("#selectedShowTickets").css("display", "none");
      $("#exportTickets").css("display", "none");
      $('#unselectAllTickets').addClass('d-none')
    }
  });
}

function addingTicketsIds() {
  var ids = JSON.parse($("#selectedTickets").attr("data-ids") || "[]");
  var selectedCount = 0;
  var tableName = localStorage.getItem("activeTabTicket");
  if (tableName === "#tab_1") {
    tableName = "my";
    $(".my-tickets-row").each(function () {
      if ($(this).is(":checked")) {
        ids.push(this.id);
      } else {
        var index = ids.indexOf(this.id);
        if (index > -1) {
          ids.splice(index, 1);
        }
      }
    });
  } else if (tableName === "#tab_2") {
    tableName = "allocated";
    $(".allocated-tickets-row").each(function () {
      if ($(this).is(":checked")) {
        ids.push(this.id);
      } else {
        var index = ids.indexOf(this.id);
        if (index > -1) {
          ids.splice(index, 1);
        }
      }
    });
  } else {
    tableName = "all";
    $(".all-tickets-row").each(function () {
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

  ids = makeTicketsListUnique(ids);
  selectedCount = ids.length;

  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var message = rowMessages[languageCode];
    $("#selectedTickets").attr("data-ids", JSON.stringify(ids));
    if (selectedCount === 0) {
      $("#selectedShowTickets").css("display", "none");
      $("#exportTickets").css("display", "none");
      $('#unselectAllTickets').addClass('d-none')
    } else {
      $("#exportTickets").css("display", "inline-flex");
      $("#selectedShowTickets").css("display", "inline-flex");
      $("#selectedShowTickets").text(selectedCount + " - " + message);
      $('#unselectAllTickets').removeClass('d-none')
    }
  });
}

function selectAllTickets() {
  $("#selectedTickets").attr("data-clicked", 1);
  $("#selectedShowTickets").removeAttr("style");
  var savedFilters = JSON.parse(localStorage.getItem("savedFilters"));
  var tableName = localStorage.getItem("activeTabTicket");
  if (tableName === "#tab_1") {
    tableName = "my";
    $(".myTicketsAll").prop("checked", true);
  }
  if (tableName === "#tab_2") {
    tableName = "allocated";
    $(".allocatedTicketsAll").prop("checked", true);
  } else {
    tableName = "all";
    $(".allocatedTicketsAll").prop("checked", true);
    $(".myTicketsAll").prop("checked", true);
    $(".allocatedTicketsAll").prop("checked", true);
  }
  if (savedFilters && savedFilters["filterData"] !== null) {
    var filter = savedFilters["filterData"];
    $.ajax({
      url: "/helpdesk/tickets-select-filter",
      data: {
        page: "all",
        filter: JSON.stringify(filter),
        tableName: tableName,
      },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var ticketIds = response.ticket_ids;

        for (var i = 0; i < ticketIds.length; i++) {
          var tickId = ticketIds[i];
          $("#" + tickId).prop("checked", true);
        }
        $("#selectedTickets").attr("data-ids", JSON.stringify(ticketIds));

        count = makeTicketsListUnique(ticketIds);
        tickTicketsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  } else {
    $.ajax({
      url: "/helpdesk/tickets-select-filter",
      data: { page: "all", tableName: tableName },
      type: "GET",
      dataType: "json",
      success: function (response) {
        var ticketIds = response.ticket_ids;

        for (var i = 0; i < ticketIds.length; i++) {
          var tickId = ticketIds[i];
          $("#" + tickId)
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
        }
        var previousIds = $("#selectedTickets").attr("data-ids");
        $("#selectedTickets").attr(
          "data-ids",
          JSON.stringify(
            Array.from(new Set([...ticketIds, ...JSON.parse(previousIds)]))
          )
        );
        count = makeTicketsListUnique(ticketIds);
        tickTicketsCheckboxes(count);
      },
      error: function (xhr, status, error) {
        console.error("Error:", error);
      },
    });
  }
}

function unselectAllTickets() {
  $("#selectedTickets").attr("data-clicked", 0);
  var tableName = localStorage.getItem("activeTabTicket");
  if (tableName === "#tab_1") {
    tableName = "my";
    $(".myTicketsAll").prop("checked", false);
  } else if (tableName === "#tab_2") {
    tableName = "allocated";
    $(".allocatedTicketsAll").prop("checked", false);
  } else {
    tableName = "all";
    $(".allTicketsAll").prop("checked", false);
    $(".myTicketsAll").prop("checked", false);
    $(".allocatedTicketsAll").prop("checked", false);
  }
  $.ajax({
    url: "/helpdesk/tickets-select-filter",
    data: { page: "all", filter: "{}", tableName: tableName },
    type: "GET",
    dataType: "json",
    success: function (response) {
      var ticketIds = response.ticket_ids;

      for (var i = 0; i < ticketIds.length; i++) {
        var tickId = ticketIds[i];
        $("#" + tickId)
          .prop("checked", false)
          .closest(".oh-sticky-table__tr")
          .removeClass("highlight-selected");
      }
      var ids = JSON.parse($("#selectedTickets").attr("data-ids") || "[]");
      var uniqueIds = makeTicketsListUnique(ids);
      toggleHighlight(uniqueIds);

      $("#selectedTickets").attr("data-ids", JSON.stringify([]));

      count = [];
      tickTicketsCheckboxes(count);
    },
    error: function (xhr, status, error) {
      console.error("Error:", error);
    },
  });
}

function ticketBulkArchive(e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = TicketArchiveMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = [];
    ids.push($("#selectedTickets").attr("data-ids"));
    ids = JSON.parse($("#selectedTickets").attr("data-ids"));
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
          ids.push($("#selectedTickets").attr("data-ids"));
          ids = JSON.parse($("#selectedTickets").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/helpdesk/tickets-bulk-archive?is_active=False",
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

function ticketBulkUnArchive(e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = ticketUnarchiveMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = [];
    ids.push($("#selectedTickets").attr("data-ids"));
    ids = JSON.parse($("#selectedTickets").attr("data-ids"));
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
          ids.push($("#selectedTickets").attr("data-ids"));
          ids = JSON.parse($("#selectedTickets").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/helpdesk/tickets-bulk-archive?is_active=True",
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

function ticketsBulkDelete(e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = ticketDeleteMessages[languageCode];
    var textMessage = noRowMessages[languageCode];
    ids = [];
    ids.push($("#selectedTickets").attr("data-ids"));
    ids = JSON.parse($("#selectedTickets").attr("data-ids"));
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
          ids.push($("#selectedTickets").attr("data-ids"));
          ids = JSON.parse($("#selectedTickets").attr("data-ids"));
          $.ajax({
            type: "POST",
            url: "/helpdesk/tickets-bulk-delete",
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
