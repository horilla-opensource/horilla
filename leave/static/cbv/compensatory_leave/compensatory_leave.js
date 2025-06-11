var closeButtonText = {
    ar: "إغلاق",
    de: "Schließen",
    es: "Cerrar",
    en: "Close",
    fr: "Fermer",
  };
  
  var confirmButtonText = {
    ar: "تأكيد",
    de: "Bestätigen",
    es: "Confirmar",
    en: "Confirm",
    fr: "Confirmer",
  };
  
  var deleteCompensatoryMessages = {
    ar: "هل تريد حقًا حذف جميع طلبات الإجازة المحددة؟",
    de: "Möchten Sie wirklich alle ausgewählten Urlaubsanfragen löschen?",
    es: "¿Realmente desea eliminar todas las solicitudes de permiso seleccionadas?",
    en: "Are you sure you want to delete ?",
    fr: "Voulez-vous vraiment supprimer toutes les demandes de congé sélectionnées?",
  };


  
  tickLeaverequestsCheckboxes();
  function makeLeaverequestsListUnique(list) {
    return Array.from(new Set(list));
  }
  
  tickUserrequestsCheckboxes();
  function makeUserrequestsListUnique(list) {
    return Array.from(new Set(list));
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