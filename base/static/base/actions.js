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
$(".all-rshift").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-rshift-row").prop("checked", true);
  } else {
    $(".all-rshift-row").prop("checked", false);
  }
});

$("#archiveRotatingShiftAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to archive these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rshift-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    $.ajax({
      type: "POST",
      url: "/rotating-shift-assign-bulk-archive?is_active=False",
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
$("#unArchiveRotatingShiftAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to un-archive these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rshift-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    $.ajax({
      type: "POST",
      url: "/rotating-shift-assign-bulk-archive?is_active=True",
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
$("#deleteRotatingShiftAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to delete these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rshift-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    $.ajax({
      type: "POST",
      url: "/rotating-shift-assign-bulk-delete",
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

$(".all-rwork-type").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-rwork-type-row").prop("checked", true);
  } else {
    $(".all-rwork-type-row").prop("checked", false);
  }
});

$("#archiveRotatingWorkTypeAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to archive these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rwork-type-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    $.ajax({
      type: "POST",
      url: "/rotating-work-type-assign-bulk-archive?is_active=False",
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
$("#unArchiveRotatingWorkTypeAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to un-archive these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rwork-type-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/rotating-work-type-assign-bulk-archive?is_active=True",
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
$("#deleteRotatingWorkTypeAssign").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to delete these selected allocations?"
  );
  if (choice) {
    var checkedRows = $(".all-rwork-type-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/rotating-work-type-assign-bulk-delete",
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

$(".all-shift-requests").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-shift-requests-row").prop("checked", true);
  } else {
    $(".all-shift-requests-row").prop("checked", false);
  }
});

$("#approveShiftRequest").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to approve these selected requests?"
  );
  if (choice) {
    var checkedRows = $(".all-shift-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/shift-request-bulk-approve",
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

$("#cancelShiftRequest").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to cancel these selected requests?"
  );
  if (choice) {
    var checkedRows = $(".all-shift-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/shift-request-bulk-cancel",
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

$("#deleteShiftRequest").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to delete these selected requests?"
  );
  if (choice) {
    var checkedRows = $(".all-shift-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/shift-request-bulk-delete",
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

$(".all-work-type-requests").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-work-type-requests-row").prop("checked", true);
  } else {
    $(".all-work-type-requests-row").prop("checked", false);
  }
});

$("#approveWorkTypeRequest").click(function (e) {
  var choice = originalConfirm(
    "Do you want to approve these selected requests?"
  );
  if (choice) {
    e.preventDefault();
    var checkedRows = $(".all-work-type-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/work-type-request-bulk-approve",
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

$("#deleteWorkTypeRequest").click(function (e) {
  var choice = originalConfirm(
    "Do you want to delete these selected requests?"
  );
  if (choice) {
    e.preventDefault();
    var checkedRows = $(".all-work-type-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/work-type-request-bulk-delete",
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

$("#cancelWorkTypeRequest").click(function (e) {
  e.preventDefault();
  var choice = originalConfirm(
    "Do you want to cancel these selected requests?"
  );
  if (choice) {
    var checkedRows = $(".all-work-type-requests-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });

    $.ajax({
      type: "POST",
      url: "/work-type-request-bulk-cancel",
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
