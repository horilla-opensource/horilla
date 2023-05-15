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
$(".all-employee").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-employee-row").prop("checked", true);
  } else {
    $(".all-employee-row").prop("checked", false);
  }
});
$(".all-employee").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-employee-row").prop("checked", true);
  } else {
    $(".all-employee-row").prop("checked", false);
  }
});
$("#archiveEmployees").click(function (e) {
  choice = originalConfirm('Do you want to delete archive all this selected employees?')
  if (choice) {
    e.preventDefault();
    var checkedRows = $(".all-employee-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
      type: "POST",
      url: "/employee/employee-bulk-archive?is_active=False",
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
$("#unArchiveEmployees").click(function (e) {
  e.preventDefault();
  choice = originalConfirm('Do you want to delete archive all this selected employees?')
  if (choice) {
    var checkedRows = $(".all-employee-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
      type: "POST",
      url: "/employee/employee-bulk-archive?is_active=True",
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
$("#deleteEmployees").click(function (e) {
  e.preventDefault();
  choice = originalConfirm('Do you want to delete archive all this selected employees?')
  if (choice) {
    var checkedRows = $(".all-employee-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
      type: "POST",
      url: "/employee/employee-bulk-delete",
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
