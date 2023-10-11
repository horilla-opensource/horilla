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

var originalConfirm = window.confirm;
// Override the default confirm function with SweetAlert
window.confirm = function(message) {
  var event = window.event || {};
  event.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirm = confirmModal[languageCode];
    var cancel = cancelModal[languageCode];
  // Add event listener to "Confirm" button
    $("#confirmModalBody").html(message)
    var submit = false;
    Swal.fire({
      text: message,
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#008000',
      cancelButtonColor: '#d33',
      confirmButtonText: confirm,
      cancelButtonText: cancel,
    }).then((result) => {
      if (result.isConfirmed) {
        if (event.target.tagName.toLowerCase() === 'form') {
          event.target.submit();
        }
        else if (event.target.tagName.toLowerCase() === 'a') {
          window.location.href = event.target.href;
        }
      } 
      else {
      }
    })
  });
};
var nav = $("section.oh-wrapper.oh-main__topbar");
nav.after($(
  `
  <div id="filterTagContainerSectionNav" class="oh-titlebar-container__filters mb-2 mt-0 oh-wrapper"></div>
  `
))