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
$(".all-candidate").change(function (e) {
  var is_checked = $(this).is(":checked");
  if (is_checked) {
    $(".all-candidate-row").prop("checked", true);
  } else {
    $(".all-candidate-row").prop("checked", false);
  }
});
$("#archiveCandidates").click(function (e) {
  choice = originalConfirm("Do you want to archive selected candidates?")
  if (choice) {
    e.preventDefault();
    var checkedRows = $(".all-candidate-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
      type: "POST",
      url: "/recruitment/candidate-bulk-archive?is_active=False",
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
$("#unArchiveCandidates").click(function (e) {
  e.preventDefault();
  choice = originalConfirm("Do you want to un-archive selected candidates?")
  if (choice) {
    
    var checkedRows = $(".all-candidate-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
      type: "POST",
      url: "/recruitment/candidate-bulk-archive?is_active=True",
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
$("#deleteCandidates").click(function (e) {
  e.preventDefault();
  choice = originalConfirm("Do you want to delete selected candidates?")
  if (choice) {
    var checkedRows = $(".all-candidate-row").filter(":checked");
    ids = [];
    checkedRows.each(function () {
      ids.push($(this).attr("id"));
    });
    
    $.ajax({
    type: "POST",
    url: "/recruitment/candidate-bulk-delete",
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
