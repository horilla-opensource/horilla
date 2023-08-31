var downloadMessages = {
  ar: "هل ترغب في تنزيل القالب؟",
  de: "Möchten Sie die Vorlage herunterladen?",
  es: "¿Quieres descargar la plantilla?",
  en: "Do you want to download the template?",
  fr: "Voulez-vous télécharger le modèle ?",
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
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


// Get the form element
var form = document.getElementById("workInfoImportForm");

// Add an event listener to the form submission
form.addEventListener("submit", function (event) {
  // Prevent the default form submission
  event.preventDefault();

  // Create a new form data object
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
      "X-CSRFToken": getCookie('csrftoken'), // Replace with your csrf token value
    },
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
      link.download = "ImportError.xlsx";
      document.body.appendChild(link);
      link.click();
    },
    error: function (xhr, textStatus, errorThrown) {
      console.error("Error downloading file:", errorThrown);
    },
  });
});

$("#work-info-import").click(function (e) {
  e.preventDefault();
  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = downloadMessages[languageCode];
    // Use SweetAlert for the confirmation dialog
    Swal.fire({
      text: confirmMessage,
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#008000',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Confirm'
    }).then(function(result) {
      if (result.isConfirmed) {
        $.ajax({
          type: "GET",
          url: "/employee/work-info-import",
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
            link.download = "work_info_template.xlsx";
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
});