var confirmModal = {
  ar: "تأكيد",
  de: "Bestätigen",
  es: "Confirmar",
  en: "Confirm",
  fr: "Confirmer",
};

var cancelModal = {
  ar: "إلغاء",
  de: "Abbrechen",
  es: "Cancelar",
  en: "Cancel",
  fr: "Annuler",
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

var originalConfirm = window.confirm;
// Override the default confirm function with SweetAlert
window.confirm = function (message) {
  var event = window.event || {};
  event.preventDefault();
  var languageCode = null;
  languageCode = $("#main-section-data").attr("data-lang");
  var confirm =
    confirmModal[languageCode] ||
    ((languageCode = "en"), confirmModal[languageCode]);
  var cancel =
    cancelModal[languageCode] ||
    ((languageCode = "en"), cancelModal[languageCode]);
  // Add event listener to "Confirm" button
  $("#confirmModalBody").html(message);
  var submit = false;
  Swal.fire({
    text: message,
    icon: "question",
    showCancelButton: true,
    confirmButtonColor: "#008000",
    cancelButtonColor: "#d33",
    confirmButtonText: confirm,
    cancelButtonText: cancel,
  }).then((result) => {
    if (result.isConfirmed) {
      if (event.target.tagName.toLowerCase() === "form") {
        if (event.target["htmx-internal-data"]) {
          var path = event.target["htmx-internal-data"].path;
          var verb = event.target["htmx-internal-data"].verb;
          var hxTarget = $(event.target).attr("hx-target");
          if (verb === "post") {
            htmx.ajax("POST", path, hxTarget);
          } else {
            htmx.ajax("GET", path, hxTarget);
          }
        } else {
          event.target.submit();
        }
      } else if (event.target.tagName.toLowerCase() === "a") {
        if (event.target.href) {
          window.location.href = event.target.href;
        } else {
          var path = event.target["htmx-internal-data"].path;
          var verb = event.target["htmx-internal-data"].verb;
          var hxTarget = $(event.target).attr("hx-target");
          if (verb === "post") {
            // hx.post(path)
            htmx.ajax("POST", path, hxTarget);
          } else {
            htmx.ajax("GET", path, hxTarget);
          }
        }
      } else {
        var path = event.target["htmx-internal-data"].path;
        var verb = event.target["htmx-internal-data"].verb;
        var hxTarget = $(event.target).attr("hx-target");
        if (verb === "post") {
          htmx.ajax("POST", path, hxTarget);
        } else {
          htmx.ajax("GET", path, hxTarget);
        }
      }
    } else {
    }
  });
};
var nav = $("section.oh-wrapper.oh-main__topbar");
nav.after(
  $(
    `
  <div id="filterTagContainerSectionNav" class="oh-titlebar-container__filters mb-2 mt-0 oh-wrapper"></div>
  `
  )
);

function attendanceDateChange(selectElement) {
  var selectedDate =selectElement.val()
  let parentForm = selectElement.parents().closest("form")
  var shiftId = parentForm.find("[name=shift_id]").val()

  $.ajax({
    type: "post",
    url: "/attendance/update-date-details",
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      "attendance_date":selectedDate,
      "shift_id":shiftId
    },
    success: function (response) {
      parentForm.find("[name=minimum_hour]").val(response.minimum_hour)

    }
  });
}
