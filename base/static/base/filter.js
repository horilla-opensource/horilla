function filterFormSubmit(formId) {
  var formData = $("#" + formId).serialize();
  var count = 0;
  formData.split("&").forEach(function (field) {
    var parts = field.split("=");
    var value = parts[1];
    if (parts[0] !== "view"){
      if (value && value !== "unknown") {
        count++;
      }
    }
  });
  $("#filterCount").empty();
  if (count > 0) {
    $("#filterCount").text(`(${count})`);
  }
}

$("#filterForm").submit(function (e) {
  filterFormSubmit("filterForm");
});

$("#filterForm2").submit(function (e) {
  filterFormSubmit("filterForm2");
});
