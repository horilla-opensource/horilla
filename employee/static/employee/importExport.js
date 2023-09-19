var downloadMessages = {
  ar: "هل ترغب في تنزيل القالب؟",
  de: "Möchten Sie die Vorlage herunterladen?",
  es: "¿Quieres descargar la plantilla?",
  en: "Do you want to download the template?",
  fr: "Voulez-vous télécharger le modèle ?",
};

var importsuccess = {
  ar: "نجح الاستيراد", // Arabic
  de: "Import erfolgreich", // German
  es: "Importado con éxito", // Spanish
  en: "Imported Successfully!", // English
  fr: "Importation réussie" // French
};

var uploadsuccess = {
  ar: "تحميل كامل", // Arabic
  de: "Upload abgeschlossen", // German
  es: "Carga completa", // Spanish
  en: "Upload Complete!", // English
  fr: "Téléchargement terminé" // French
};

var uploadingmessage = {
  ar: "جارٍ الرفع",
  de: "Hochladen...",
  es: "Subiendo...",
  en: "Uploading...",
  fr: "Téléchargement en cours...",
};

var validationmessage = {
  ar: "يرجى تحميل ملف بامتداد .xlsx فقط.",
  de: "Bitte laden Sie nur eine Datei mit der Erweiterung .xlsx hoch.",
  es: "Por favor, suba un archivo con la extensión .xlsx solamente.",
  en: "Please upload a file with the .xlsx extension only.",
  fr: "Veuillez télécharger uniquement un fichier avec l'extension .xlsx.",
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
      Swal.fire({
          text: confirmMessage,
          icon: 'question',
          showCancelButton: true,
          confirmButtonColor: '#008000',
          cancelButtonColor: '#d33',
          confirmButtonText: 'Confirm'
      }).then(function(result) {
          if (result.isConfirmed) {

              $("#loading").show();

              var xhr = new XMLHttpRequest();
              xhr.open('GET', '/employee/work-info-import', true);
              xhr.responseType = 'arraybuffer';

              xhr.upload.onprogress = function (e) {
                  if (e.lengthComputable) {
                      var percent = (e.loaded / e.total) * 100;
                      $(".progress-bar").width(percent + "%").attr("aria-valuenow", percent);
                      $("#progress-text").text("Uploading... " + percent.toFixed(2) + "%");
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
  var languageCode = null;
  getCurrentLanguageCode(function(code){
  languageCode = code;
  var importMessage = importsuccess[languageCode];
  var uploadMessage = uploadsuccess[languageCode];
  var uploadingMessage = uploadingmessage[languageCode];
  let progressBar = document.querySelector('.progress-bar');
  let progressText = document.getElementById('progress-text');

  let width = 0;
  let interval = setInterval(function() {
    if (width >= 100) {
      clearInterval(interval);
      progressText.innerText = uploadMessage;
      setTimeout(function() {
        document.getElementById('loading').style.display = 'none';
      }, 3000);
      Swal.fire({
        text: importMessage,
        icon: "success",
        showConfirmButton: false,
        timer: 2000,
        timerProgressBar: true,
      });
      setTimeout(function() {
        $('#workInfoImport').removeClass('oh-modal--show');
        location.reload(true);
      }, 2000);
    } else {
      width++;
      progressBar.style.width = width + '%';
      progressBar.setAttribute('aria-valuenow', width);
      progressText.innerText = uploadingMessage + width + '%';
    }
  }, 20);
}
)}

document.getElementById('workInfoImportForm').addEventListener('submit', function(event) {
  event.preventDefault(); 
  var languageCode = null;
  getCurrentLanguageCode(function(code){
  languageCode = code;
  var erroMessage = validationmessage[languageCode];

  var fileInput = $('#workInfoImportFile').val();
  var allowedExtensions = /(\.xlsx)$/i;

  if (!allowedExtensions.exec(fileInput)) {

    var errorMessage = document.createElement('div');
    errorMessage.classList.add('error-message');
    
    errorMessage.textContent = erroMessage;

    document.getElementById('error-container').appendChild(errorMessage);

    fileInput.value = '';
    
    setTimeout(function() {
      errorMessage.remove();
    }, 2000);

    return false;
  }
  else{

          document.getElementById('loading').style.display = 'block';


          simulateProgress();
  }

});
})
