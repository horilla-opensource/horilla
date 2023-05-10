$(document).ready(function () {
  $(".validate").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".validate-row").prop("checked", true);
    } else {
      $(".validate-row").prop("checked", false);
    }
  });

  $(".all-attendances").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".all-attendance-row").prop("checked", true);
    } else {
      $(".all-attendance-row").prop("checked", false);
    }
  });

  $(".ot-attendances").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
      $(".ot-attendance-row").prop("checked", true);
    } else {
      $(".ot-attendance-row").prop("checked", false);
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
  $("#validateAttendances").click(function (e) {
    e.preventDefault();
    choice = originalConfirm(
      "Do you really want to validate all the selected attendances? "
    );
    if (choice) {
      var checkedRows = $(".validate-row").filter(":checked");
      ids = [];
      checkedRows.each(function () {
        ids.push($(this).attr("id"));
      });
      $.ajax({
        type: "POST",
        url: "/attendance/validate-bulk-attendance",
        data: {
          csrfmiddlewaretoken: getCookie("csrftoken"),
          ids: JSON.stringify(ids),
        },
        success: function (response, textStatus, jqXHR) {
          if (jqXHR.status === 200) {
            location.reload(); // Reload the current page
          } else {
          }
        },
      });
    }
  });

  $("#approveOt").click(function (e) {
    e.preventDefault();
    choice = originalConfirm(
      "Do you really want to approve OT for all the selected attendances? "
    );
    if (choice) {
      var checkedRows = $(".ot-attendance-row").filter(":checked");
      ids = [];
      checkedRows.each(function () {
        ids.push($(this).attr("id"));
      });
      $.ajax({
        type: "POST",
        url: "/attendance/approve-bulk-overtime",
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

  $("#bulkDelete").click(function (e) {
    e.preventDefault();
    choice = originalConfirm(
      "Do you really want to delete all the selected attendances? "
    );
    if (choice) {
      var checkedRows = $(".attendance-checkbox").filter(":checked");
      ids = [];
      checkedRows.each(function () {
        ids.push($(this).attr("id"));
      });
      $.ajax({
        type: "POST",
        url: "/attendance/attendance-bulk-delete",
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
});
