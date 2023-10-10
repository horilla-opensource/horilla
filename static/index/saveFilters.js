var savedFilters = localStorage.getItem("savedFilters");
if (savedFilters != null) {
  var filterDetails = JSON.parse(savedFilters);
  if (window.location.pathname == filterDetails.currentPath) {
    let filterForm = $(filterDetails.formSelector);
    for (var fieldName in filterDetails.filterData) {
      if (filterDetails.filterData.hasOwnProperty(fieldName)) {
        var value = filterDetails.filterData[fieldName];
        // Set the value of the corresponding form field
        filterForm.find('[name="' + fieldName + '"]').val(value);
        filterForm
          .find('[name="' + fieldName + '"]')
          .first()
          .change();
      }
    }
    setTimeout(() => {
    filterForm.find(".filterButton").click();
    setTimeout(() => {
        $("#main-section-data:first").show();
        $("#tripple-loader-contaner:first").remove();
    }, 350);
    },250 );
  }else{
    $("#main-section-data:first").show();
    $("#tripple-loader-contaner:first").remove();
  }
}else{
    $("#main-section-data:first").show();
    $("#tripple-loader-contaner:first").remove();
}
$(document).ready(function () {
  $(".filterButton").click(function (e) {
    var filterForm = $(this).parents().closest("form");
    var currentPath = window.location.pathname;
    var formDataArray = filterForm.serializeArray();
    var filterData = {};
    formDataArray.forEach(function (item) {
      filterData[item.name] = item.value;
    });
    var filterDetails = {
      currentPath: currentPath,
      formSelector: "form" + `[hx-get="${filterForm.attr("hx-get")}"]`,
      filterData: filterData,
    };
    localStorage.setItem("savedFilters", JSON.stringify(filterDetails));
  });
});
