function conditionalVisibility() {
  if (!$("#id_is_condition_based").is(":checked")) {
    $("#id_field, #id_value, #id_condition").hide();
    $("#id_field, #id_value, #id_condition").parent().hide();
    $("[for='id_field'], [for='id_value'], [for='id_condition']").hide();
    $("[for='id_field'], [for='id_value'], [for='id_condition']")
      .parent()
      .hide();
  } else {
    $("#id_field, #id_value, #id_condition").show();
    $("#id_field, #id_value, #id_condition").parent().show();
    $("[for='id_field'], [for='id_value'], [for='id_condition']").show();
    $("[for='id_field'], [for='id_value'], [for='id_condition']")
      .parent()
      .show();
  }

  if ($("#id_is_tax").is(":checked")) {
    $("#id_is_fixed").prop("checked", false);
    $("#id_based_on,[for=id_based_on], #id_rate, [for=id_rate]").show();
    $("#id_based_on,[for=id_based_on], #id_rate, [for=id_rate]")
      .parent()
      .show();
    $(
      "#id_is_condition_based,[for=id_is_condition_based],#id_field,[for=field],#id_condition,[for=condition],#id_value,[for=id_value]"
    ).hide();
    $(
      "#id_is_condition_based,[for=id_is_condition_based],#id_field,[for=field],#id_condition,[for=condition],#id_value,[for=id_value]"
    )
      .parent()
      .hide();

    $(
      "#id_is_pre_tax,[for='id_is_pre_tax'], #id_is_fixed,[for='id_is_fixed'],#id_amount,[for='id_amount'],#id_employee_rate,[for=id_employee_rate],#id_is_pretax,[for=id_is_pretax] "
    ).hide();
    $(
      "#id_is_pre_tax,[for='id_is_pre_tax'], #id_is_fixed,[for='id_is_fixed'],#id_amount,[for='id_amount'],#id_employee_rate,[for=id_employee_rate],#id_is_pretax,[for=id_is_pretax] "
    )
      .parent()
      .hide();
  } else {
    $("#id_based_on,[for=id_based_on], #id_rate, [for=id_rate]").hide();
    $("#id_based_on,[for=id_based_on], #id_rate, [for=id_rate]")
      .parent()
      .hide();
    $(
      "#id_is_pre_tax,[for='id_is_pre_tax'], #id_is_fixed,[for='id_is_fixed'],#id_amount,[for='id_amount'],#id_employee_rate,[for=id_employee_rate],#id_is_pretax,[for=id_is_pretax] "
    ).show();
    $(
      "#id_is_pre_tax,[for='id_is_pre_tax'], #id_is_fixed,[for='id_is_fixed'],#id_amount,[for='id_amount'],#id_employee_rate,[for=id_employee_rate],#id_is_pretax,[for=id_is_pretax] "
    )
      .parent()
      .show();
  }

  if (!$("#id_is_fixed").is(":checked")) {
    $("#id_based_on, #id_rate").show();
    $("#id_based_on, #id_rate").parent().show();
    $("[for='id_based_on'], [for='id_rate']").show();
    $("[for='id_based_on'], [for='id_rate']").parent().show();
    $("#id_amount").hide();
    $("#id_amount").parent().hide();
    $("[for='id_amount']").hide();
    $("[for='id_amount']").parent().hide();
    $("#id_employer_rate, [for=id_employer_rate]").show();
    $("#id_employer_rate, [for=id_employer_rate]").parent().show();
  } else {
    $("#id_based_on, #id_rate").hide();
    $("#id_based_on, #id_rate").parent().hide();
    $("[for='id_based_on'], [for='id_rate']").hide();
    $("[for='id_based_on'], [for='id_rate']").parent().hide();
    $("#id_amount").show();
    $("#id_amount").parent().show();
    $("[for='id_amount']").show();
    $("[for='id_amount']").parent().show();
    $("#id_employer_rate, [for=id_employer_rate]").hide();
    $("#id_employer_rate, [for=id_employer_rate]").parent().hide();
  }
  if ($("#id_is_fixed").is(":checked") && !$("#id_is_tax").is(":checked")) {
    $("#id_based_on, [for=id_based_on],#id_rate,[for=id_rate]").hide();
    $("#id_based_on, [for=id_based_on],#id_rate,[for=id_rate]").parent().hide();
    $("#id_amount,[for=id_amount]").show();
    $("#id_amount,[for=id_amount]").parent().show();
  }

  if ($("#id_include_active_employees").is(":checked")) {
    $(
      "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
    ).hide();
    $(
      "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
    )
      .parent()
      .hide();
    $(
      "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
    ).hide();
    $(
      "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
    )
      .parent()
      .hide();
  } else {
    $(
      "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
    ).show();
    $(
      "#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]"
    )
      .parent()
      .show();
    if ($("#id_is_condition_based").is(":checked")) {
      $(
        "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
      ).show();
      $(
        "#id_field,[for=id_field], #id_condition,[for=id_condition], #id_value,[for=id_value]"
      )
        .parent()
        .show();
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
  if ($("#id_is_condition_based").is(":checked")) {
    $("#id_specific_employees,[for=id_specific_employees]").hide();
    $("#id_specific_employees,[for=id_specific_employees]").parent().hide();
  }

  if (
    $("#id_has_max_limit").is(":checked") &&
    !$("#id_is_fixed").is(":checked")
  ) {
    $("#id_maximum_amount, [for=id_maximum_amount]").show();
    $("#id_maximum_amount, [for=id_maximum_amount]").parent().show();
  } else {
    $("#id_maximum_amount, [for=id_maximum_amount]").hide();
    $("#id_maximum_amount, [for=id_maximum_amount]").parent().hide();
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

  if ($("#id_is_tax").is(":checked")) {
    $(
      "#id_is_condition_based,[for=id_is_condition_based],#id_field,[for=id_field],#id_condition,[for=id_condition],#id_value,[for=id_value]"
    ).hide();
    $(
      "#id_is_condition_based,[for=id_is_condition_based],#id_field,[for=id_field],#id_condition,[for=id_condition],#id_value,[for=id_value]"
    )
      .parent()
      .hide();
  }
  if ($("#id_update_compensation").val() != "") {
    $(
      "#id_is_tax, [for=id_is_tax],#id_is_pretax, [for=id_is_pretax], #id_based_on,[for=id_based_on],#id_employee_rate,[for=id_employee_rate],#id_employer_rate,[for=id_employer_rate]"
    ).hide();
    $(
      "#id_is_tax, [for=id_is_tax],#id_is_pretax, [for=id_is_pretax], #id_based_on,[for=id_based_on],#id_employee_rate,[for=id_employee_rate],#id_employer_rate,[for=id_employer_rate]"
    )
      .parent()
      .hide();
    $(
      "#id_if_choice,[for=id_if_choice],#id_if_condition,[for=id_if_condition],#id_is_fixed,[for=id_is_fixed],#id_include_active_employees,[for=id_include_active_employees],#id_is_condition_based,[for=id_is_condition_based]"
    ).hide();
    $(
      "#id_if_choice,[for=id_if_choice],#id_if_condition,[for=id_if_condition],#id_is_fixed,[for=id_is_fixed],#id_include_active_employees,[for=id_include_active_employees],#id_is_condition_based,[for=id_is_condition_based]"
    )
      .parent()
      .hide();
    $(
      "#id_field,[for=id_field],#id_condition,[for=id_condition],#id_value,[for=id_value]"
    ).hide();
    $(
      "#id_field,[for=id_field],#id_condition,[for=id_condition],#id_value,[for=id_value]"
    )
      .parent()
      .hide();
    $(
      "#id_has_max_limit,[for=id_has_max_limit],#id_maximum_amount, [for=id_maximum_amount],#id_maximum_unit,[for=id_maximum_unit]"
    ).hide();
    $(
      "#id_has_max_limit,[for=id_has_max_limit],#id_maximum_amount, [for=id_maximum_amount],#id_maximum_unit,[for=id_maximum_unit]"
    )
      .parent()
      .hide();
    $("#id_amount,[for=id_amount]").show();
    $("#id_amount,[for=id_amount]").parent().show();
    $("#id_if_amount,[for=id_if_amount]").hide();
    $("#id_is_condition_based").prop("checked", false);
  } else {
    $("#id_include_active_employees,[for=id_include_active_employees]").show();
    $("#id_include_active_employees,[for=id_include_active_employees]")
      .parent()
      .show();

    $("#id_has_max_limit,[for=id_has_max_limit]").show();
    $("#id_has_max_limit,[for=id_has_max_limit]").parent().show();
    if ($("#id_has_max_limit").is(":checked")) {
      $(
        "#id_maximum_amount, [for=id_maximum_amount],#id_maximum_unit,[for=id_maximum_unit]"
      ).show();
      $(
        "#id_maximum_amount, [for=id_maximum_amount],#id_maximum_unit,[for=id_maximum_unit]"
      ).parent().show();
    }
    $("#id_is_tax,[for=id_is_tax],#id_if_choice,[for=id_if_choice],#id_if_value,[for=id_if_value],#id_if_condition,[for=id_if_condition],#id_if_amount,[for=id_if_amount]").show();
    $("#id_is_tax,[for=id_is_tax],#id_if_choice,[for=id_if_choice],#id_if_value,[for=id_if_value],#id_if_condition,[for=id_if_condition],#id_if_amount,[for=id_if_amount]").parent().show();
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
$("input[type='checkbox'], select, input[type='radio']").change(function (e) {
  e.preventDefault();
  conditionalVisibility();
});
conditionalVisibility();
