
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
  choice = originalConfirm("Do you want to download template?");
  if (choice) {
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
