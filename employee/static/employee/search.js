$(document).ready(function () {
  $("#employee-search").keyup(function (e) {
    $(".employee-view-type").attr("hx-vals", `{"search":"${$(this).val()}"}`);
  });
  $(".employee-view-type").click(function (e) {
    let view = $(this).attr("data-view");
    $("#employee-search").attr("hx-vals", `{"view":"${view}"}`);
    $('#filterForm').attr("hx-vals", `{"view":"${view}"}`);
  });

});

function employeeFilter(element) {
  var search = $('#employee-search').val();
  const form = document.querySelector('#filterForm');
  const formData = new FormData(form);
  const queryString = new URLSearchParams(formData).toString();
  const searchParams = new URLSearchParams(queryString);
  const queryObject = Object.fromEntries(searchParams.entries());
  queryObject['search'] = search
  stringQueyObject = JSON.stringify(queryObject)
  $('#list').attr('hx-vals', stringQueyObject);
  $('#card').attr('hx-vals', stringQueyObject);
}