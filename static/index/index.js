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



function empleavetypeChange(selectElement) {
  var selectedLeavetype =selectElement.val()
  let parentForm = selectElement.parents().closest("form")
  var employeeId = parentForm.find('[name = employee_id]').val()
  var start_date = parentForm.find('[name = start_date_id]').val()
  $.ajax({
    type: "post",
    url: "/leave/employee-leave-details",
    data: {
    csrfmiddlewaretoken: getCookie("csrftoken"),
    "leave_type":selectedLeavetype,
    "employee_id":employeeId,
    "date":start_date,
    },
    success: function (response) {

      // Assuming parentForm is a reference to the form containing the element to update
      var messageDiv = parentForm.find(".leave-message");

      // Check if the messageDiv already exists, if not create it
      if (!messageDiv.length) {
        messageDiv = $("<div class='leave-message'></div>");
        parentForm.prepend(messageDiv);
      }
      // Checking leave type is selected in the form or not
      if (response.leave_count != '' && response.employee != ''){
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': '#dff0d8',
          'border': '2px solid #3c763d',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else if ( selectedLeavetype === ''){
        messageDiv.hide()
      }
      else if (selectedLeavetype != '' && response.leave_count === '' && response.employee != ''){
        messageDiv.show()
        messageDiv.text("Leave type is not assigned for selecetd employee.");
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': 'auto'
        });
      }
      else if (response.leave_count === 0.0){
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else{
        messageDiv.hide()
      }

    }
  });
}


function employeeChange(selectElement) {
  var employeeId =selectElement.val()
  let parentForm = selectElement.parents().closest("form")
  var leavetypeId = parentForm.find('[name = leave_type_id]').val()
  var start_date = parentForm.find('[name = start_date_id]').val()
  $.ajax({
    type: "post",
    url: "/leave/employee-leave-details",
    data: {
    csrfmiddlewaretoken: getCookie("csrftoken"),
    "leave_type":leavetypeId,
    "employee_id":employeeId,
    "date":start_date,
    },
    success: function (response) {

      // Assuming parentForm is a reference to the form containing the element to update
      var messageDiv = parentForm.find(".leave-message");

      // Check if the messageDiv already exists, if not create it
      if (!messageDiv.length) {
        messageDiv = $("<div class='leave-message'></div>");
        parentForm.prepend(messageDiv);
      }
      // Checking leave type is selected in the form or not
      if (response.leave_count != '' && response.employee != ''){
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': '#dff0d8',
          'border': '2px solid #3c763d',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else if ( leavetypeId === ''){
        messageDiv.hide()
      }
      else if (leavetypeId != '' && response.leave_count === '' && response.employee != ''){
        messageDiv.show()
        messageDiv.text("Leave type is not assigned for selecetd employee.");
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': 'auto'
        });
      }
      else if (response.leave_count === 0.0){
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else{
        messageDiv.hide()
      }

    }
  });
}

function dateChange(selectElement) {
  let parentForm = selectElement.parents().closest("form")
  var employeeId = parentForm.find('[name = employee_id]').val()
  var leavetypeId = parentForm.find('[name = leave_type_id]').val()
  var start_date = selectElement.val()
  $.ajax({
    type: "post",
    url: "/leave/employee-leave-details",
    data: {
    csrfmiddlewaretoken: getCookie("csrftoken"),
    "leave_type":leavetypeId,
    "employee_id":employeeId,
    "date": start_date,
    },
    success: function (response) {
      // Assuming parentForm is a reference to the form containing the element to update
      var messageDiv = parentForm.find(".leave-message");

      // Check if the messageDiv already exists, if not create it
      if (!messageDiv.length) {
        messageDiv = $("<div class='leave-message'></div>");
        parentForm.prepend(messageDiv);
      }
      // Checking leave type is selected in the form or not
      if (response.leave_count != '' && response.employee != '') {
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': '#dff0d8',
          'border': '2px solid #3c763d',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else if ( leavetypeId === ''){
        messageDiv.hide()
      }
      else if (leavetypeId != '' && response.leave_count === '' && response.employee != ''){
        messageDiv.show()
        messageDiv.text("Leave type is not assigned for selecetd employee.");
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': 'auto'
        });
      }
      else if (response.leave_count === 0.0){
        messageDiv.show()
        messageDiv.text("Available Leaves :  " + response.leave_count);
        messageDiv.css({
          'background-color': 'rgb(229 79 56 / 17%)',
          'border': '2px solid hsl(8,77%,56%)',
          'border-radius': '18px',
          'padding': '10px',
          'font-weight': 'bold',
          'margin-bottom': '15px',
          'width': '35%'
        });
      }
      else{
        messageDiv.hide()
      }
    }
  });
}

function shiftChange(selectElement) {
  var shiftId =selectElement.val()
  let parentForm = selectElement.parents().closest("form")
  var attendanceDate = parentForm.find("[name=attendance_date]").first().val()
  var employeeId = parentForm.find("[name=employee_id]").first().val()
  $.ajax({
    type: "post",
    url: "/attendance/update-shift-details",
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      "shift_id":shiftId,
      "attendance_date":attendanceDate,
      'employee_id':employeeId
    },
    success: function (response) {
      parentForm.find("[name=attendance_clock_in]").val(response.shift_start_time)
      parentForm.find("[name=attendance_clock_out]").val(response.shift_end_time)
      parentForm.find("[name=attendance_worked_hour]").val(response.worked_hour)
      parentForm.find("[name=minimum_hour]").val(response.minimum_hour)
      parentForm.find("[name=attendance_clock_out_date]").val(response.checkout_date)
      parentForm.find("[name=attendance_clock_in_date]").val(response.checkin_date)
      parentForm.find("[name=work_type_id]").val(response.work_type).change()
      if (parentForm.find("[name=attendance_date]").val().length == 0) {
        parentForm.find("[name=attendance_date]").val(response.checkin_date)
      }
    }
  });
}

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
