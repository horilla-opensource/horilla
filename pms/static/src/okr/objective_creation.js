$(document).ready(function () {
  //    objecitve type choosing 
  $(".oh-input-objective-type-choices").hide();
  var $select = $('#id_objective_type').select2({
    // updating style for the objective type 
    minimumResultsForSearch: -1,
  })

  $select.data('select2').$selection.addClass('oh-select--lg--custom'); //adding css for the select

  $('#id_objective_type').on('change', function(){ 
      $(".oh-input-objective-type-choices").hide();
      $(this).show();
      $(this).prop("required",false)
      var value = $(this).val(); 
      $("#"+value).show();
      if (value=='individual') {
        value='employee_id'
      }
      $(`[name="department"]`).removeAttr('required')
      $(`[name="employee"]`).removeAttr('required')
      $(`[name="job_position"]`).removeAttr('required')
      
      $(`[name=${value}]`).attr('required',true)
  })

  $("#id_period").on("change",function(){
    period_id = $(this).val()
    if (period_id === 'create_new_period'){
      $.ajax({
          type: "GET",
          url: 'create-period',
          success: function (response) {
            $("#PeriodModal").addClass("oh-modal--show");
            $("#periodModalTarget").html(response);
          },
        });   
    }
  });
});