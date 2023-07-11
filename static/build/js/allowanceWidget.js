$(document).ready(function () {
  function conditionalVisibility() {
    if (!$("#id_is_condition_based").is(":checked")) {
      $("#id_field, #id_value, #id_condition").hide();
      $("[for='id_field'], [for='id_value'], [for='id_condition']").hide();
      $("[for='id_field'], [for='id_value'], [for='id_condition']").parent().hide();
    } else {
      $("#id_field, #id_value, #id_condition").show();
      $("#id_field, #id_value, #id_condition").parent().show();
      $("[for='id_field'], [for='id_value'], [for='id_condition']").show();
      $("[for='id_field'], [for='id_value'], [for='id_condition']").parent().show();
    }

    if (!$("#id_is_fixed").is(":checked")) {
      $("#id_based_on, #id_rate").show();
      // $("#id_, #id_rate").show();
      $("#id_based_on, #id_rate").parent().show();
      $("[for='id_based_on'], [for='id_rate']").show();
      $("[for='id_has_max_limit']").show();
      $("[for='id_based_on'], [for='id_rate']").parent().show();
      $("#id_amount").hide();
      $("#id_amount").parent().hide();
      $("[for='id_amount']").hide();
      $("[for='id_amount']").parent().hide();
    } else {
      $("#id_based_on, #id_rate").hide();
      $("#id_based_on, #id_rate").parent().hide();
      $("[for='id_has_max_limit']").show();
      $("[for='id_based_on'], [for='id_rate']").hide();
      $("[for='id_based_on'], [for='id_rate']").parent().hide();
      $("#id_amount").show();
      $("#id_amount").parent().show();
      $("[for='id_amount']").show();
      $("[for='id_amount']").parent().show();
    }
    if (
      $("#id_based_on").val() == "attendance" &&
      !$("#id_is_fixed").is(":checked")
    ) {
      $(
        "#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']"
      ).show();
      $(
        "#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']"
      ).parent().show();
    } else {
      $(
        "#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']"
      ).hide();
      $(
        "#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']"
      ).parent().hide();
    }

    if (
      $("#id_based_on").val() == "shift_id" &&
      !$("#id_is_fixed").is(":checked")
    ) {
      $(
        "#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']"
      ).show();
      $(
        "#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']"
      ).parent().show();
    } else {
      $(
        "#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']"
      ).hide();
      $(
        "#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']"
      ).parent().hide();
    }

    if (
      $("#id_based_on").val() == "work_type_id" &&
      !$("#id_is_fixed").is(":checked")
    ) {
      $(
        "#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']"
      ).show();
      $(
        "#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']"
      ).parent().show();
    } else {
      $(
        "#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']"
      ).hide();
      $(
        "#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']"
      ).parent().hide();
    }

    if (
      $("#id_based_on").val() == "overtime" &&
      !$("#id_is_fixed").is(":checked")
    ) {
      $("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").show();
      $("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").parent().show();
    } else {
      $("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").hide();
      $("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").parent().hide();
    }

    if ($("#id_based_on").val() == "basic_pay") {
      if (!$("#id_is_fixed").is(":checked")) {
        $("#id_rate, [for='id_rate']").show();
        $("#id_rate, [for='id_rate']").parent().show();
      } else {
        $("#id_rate, [for='id_rate']").hide();
        $("#id_rate, [for='id_rate']").parent().hide();
      }
    } else {
      $("#id_rate, [for='id_rate']").hide();
      $("#id_rate, [for='id_rate']").parent().hide();
    }

    if ($("#id_include_active_employees").is(":checked")) {
      $(
        "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
      ).hide();
      $(
        "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
      ).parent().hide();
      $(
        "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
      ).hide();
      $(
        "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
      ).parent().hide();
    } else {
      $(
        "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
      ).show();
      $(
        "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
      ).parent().show();
      if ($("#id_is_condition_based").is(":checked")) {
        $(
          "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
        ).show();
        $(
          "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
        ).parent().show();
      }
    }
    if (
      $("#id_is_condition_based").is(":checked") ||
      $("#id_include_active_employees").is(":checked")
    ) {
      $("#id_exclude_employees, [for=id_exclude_employees]").show();
      $("#id_exclude_employees, [for=id_exclude_employees]").parent().show();
    } else {
      $("#id_exclude_employees, [for=id_exclude_employees]").hide();
      $("#id_exclude_employees, [for=id_exclude_employees]").parent().hide();
    }
    if ($("#id_is_condition_based, #id_include_active_employees").is(":checked")) {
      $("#id_specific_employees").parent().find("ul.select2-selection__rendered li").remove()
      $("#id_specific_employees").val(null)
      $("#id_specific_employees,[for=id_specific_employees]").hide();
      $("#id_specific_employees,[for=id_specific_employees]").parent().hide();
    }

    if ($("#id_has_max_limit").is(":checked")) {
      $("#id_maximum_amount, [for=id_maximum_amount]").show();
      $("#id_maximum_amount, [for=id_maximum_amount]").parent().show();
      $("#id_maximum_unit,[for=id_maximum_unit]").show();
      $("#id_maximum_unit,[for=id_maximum_unit]").parent().show();
    } else {
      $("#id_maximum_amount, [for=id_maximum_amount]").hide();
      $("#id_maximum_amount, [for=id_maximum_amount]").parent().hide();
      $("#id_maximum_unit,[for=id_maximum_unit]").hide();
      $("#id_maximum_unit,[for=id_maximum_unit]").parent().hide();
    }
    var opt = ["attendance", "shift_id", "overtime", "work_type_id"];
    if (!$("#id_is_fixed").is(":checked") && opt.includes($("#id_based_on").val())) {
      $("#id_maximum_unit,[for=id_maximum_unit]").hide();
      $("#id_maximum_unit,[for=id_maximum_unit]").parent().hide();
    }
    if ($("#id_is_fixed").is(":checked")){
      $("#id_has_max_limit").parent().parent().hide();
      $("#id_maximum_unit,#id_maximum_amount").parent().hide();
      }
      else{
        $("#id_has_max_limit").parent().parent().show();
        if ($("#id_has_max_limit").is(":checked")) {
                  
          $("#id_maximum_unit,#id_maximum_amount").parent().show();
        }
  
      }
  }
  conditionalVisibility();
  $("select, [type=checkbox]").change(function (e) {
    e.preventDefault();
    conditionalVisibility();
  });
});
