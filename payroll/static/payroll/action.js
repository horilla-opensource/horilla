var deleteMessages = {
  ar: "هل تريد حقًا حذف جميع كشوف الدفع المحددة؟",
  de: "Sind Sie sicher, dass Sie alle ausgewählten Gehaltsabrechnungen löschen möchten?",
  es: "¿Realmente quieres eliminar todas las nóminas seleccionadas?",
  en: "Do you really want to delete all the selected payslips?",
  fr: "Voulez-vous vraiment supprimer tous les bulletins de paie sélectionnés?",
};
var norowMessages = {
  ar: "لم يتم تحديد أي صفوف.",
  de: "Es wurden keine Zeilen ausgewählt.",
  es: "No se han seleccionado filas.",
  en: "No rows have been selected.",
  fr: "Aucune ligne n'a été sélectionnée.",
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

$(".all-payslip").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-payslip-row").prop("checked", true);
    $(".all-payslip-row").attr("data-checked", true);
  } else {
    $(".all-payslip-row").prop("checked", false);
    $(".all-payslip-row").attr("data-checked", false);
  }
});

$(".all-payslip-row").change(function (e) {
  e.preventDefault();
  if ($(this).is(":checked")) {
    $(this).attr("data-checked", true);
  } else {
    $(this).attr("data-checked", false);
  }
});

$("#select-all-fields").change(function () {
  const isChecked = $(this).prop("checked");
  $('[name="selected_fields"]').prop("checked", isChecked);
});

$("#DeletePayslipBulk").click(function (e) {
  e.preventDefault();

  var languageCode = null;
  getCurrentLanguageCode(function (code) {
    languageCode = code;
    var confirmMessage = deleteMessages[languageCode];
    var textMessage = norowMessages[languageCode];
    var checkedRows = $(".all-payslip-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).val());
    });
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
          $.ajax({
            type: "POST",
            url: "/payroll/payslip-bulk-delete",
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
