function conditionalVisibility($context) {
  $context = $context || $(document);

  if (!$context.find("#id_is_condition_based").is(":checked")) {
    $context.find(".add-condition-btn-container").hide();
    $context.find("#conditionContainer").hide();
    $context.find(".default-condition-row").hide();
  } else {
    $context.find(".add-condition-btn-container").show();
    $context.find("#conditionContainer").show();
    $context.find(".default-condition-row").show();
    // Select2-enhanced selects need their visible container toggled too
    $context.find("#id_field, #id_condition").each(function () {
      var $container = $(this).nextAll(".select2.select2-container").first();
      $container.show();
    });
  }

  if (!$context.find("#id_is_fixed").is(":checked")) {
    $context.find("#id_based_on, #id_rate").show();
    $context.find("#id_based_on, #id_rate").parent().show();
    $context.find("[for='id_based_on'], [for='id_rate']").show();
    $context.find("[for='id_has_max_limit']").show();
    $context.find("[for='id_based_on'], [for='id_rate']").parent().show();
    $context.find("#id_amount").hide();
    $context.find("#id_amount").parent().hide();
    $context.find("[for='id_amount']").hide();
    $context.find("[for='id_amount']").parent().hide();
  } else {
    $context.find("#id_based_on, #id_rate").hide();
    $context.find("#id_based_on, #id_rate").parent().hide();
    $context.find("[for='id_has_max_limit']").show();
    $context.find("[for='id_based_on'], [for='id_rate']").hide();
    $context.find("[for='id_based_on'], [for='id_rate']").parent().hide();
    $context.find("#id_amount").show();
    $context.find("#id_amount").parent().show();
    $context.find("[for='id_amount']").show();
    $context.find("[for='id_amount']").parent().show();
  }

  if (
    $context.find("#id_based_on").val() == "attendance" &&
    !$context.find("#id_is_fixed").is(":checked")
  ) {
    $context.find("#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']").show();
    $context.find("#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']").parent().show();
  } else {
    $context.find("#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']").hide();
    $context.find("#id_per_attendance_fixed_amount, [for='id_per_attendance_fixed_amount']").parent().hide();
  }

  if (
    $context.find("#id_based_on").val() == "children" &&
    !$context.find("#id_is_fixed").is(":checked")
  ) {
    $context.find("#id_per_children_fixed_amount, [for='id_per_children_fixed_amount']").show();
    $context.find("#id_per_children_fixed_amount, [for='id_per_children_fixed_amount']").parent().show();
  } else {
    $context.find("#id_per_children_fixed_amount, [for='id_per_children_fixed_amount']").hide();
    $context.find("#id_per_children_fixed_amount, [for='id_per_children_fixed_amount']").parent().hide();
  }

  if (
    $context.find("#id_based_on").val() == "shift_id" &&
    !$context.find("#id_is_fixed").is(":checked")
  ) {
    $context.find("#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']").show();
    $context.find("#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']").parent().show();
  } else {
    $context.find("#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']").hide();
    $context.find("#id_shift_id, [for='id_shift_id'],#id_shift_per_attendance_amount, [for='id_shift_per_attendance_amount']").parent().hide();
  }

  if (
    $context.find("#id_based_on").val() == "work_type_id" &&
    !$context.find("#id_is_fixed").is(":checked")
  ) {
    $context.find("#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']").show();
    $context.find("#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']").parent().show();
  } else {
    $context.find("#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']").hide();
    $context.find("#id_work_type_id, [for='id_work_type_id'],#id_work_type_per_attendance_amount, [for='id_work_type_per_attendance_amount']").parent().hide();
  }

  if (
    $context.find("#id_based_on").val() == "overtime" &&
    !$context.find("#id_is_fixed").is(":checked")
  ) {
    $context.find("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").show();
    $context.find("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").parent().show();
  } else {
    $context.find("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").hide();
    $context.find("#id_amount_per_one_hr, [for='id_amount_per_one_hr']").parent().hide();
  }

  if ($context.find("#id_based_on").val() == "basic_pay") {
    if (!$context.find("#id_is_fixed").is(":checked")) {
      $context.find("#id_rate, [for='id_rate']").show();
      $context.find("#id_rate, [for='id_rate']").parent().show();
    } else {
      $context.find("#id_rate, [for='id_rate']").hide();
      $context.find("#id_rate, [for='id_rate']").parent().hide();
    }
  } else {
    $context.find("#id_rate, [for='id_rate']").hide();
    $context.find("#id_rate, [for='id_rate']").parent().hide();
  }

  if ($context.find("#id_include_active_employees").is(":checked")) {
    $context.find("#id_is_condition_based").prop("checked", false);
    $context.find("#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]").hide();
    $context.find("#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]").parent().hide();
    $context.find(".default-condition-row").hide();
    $context.find("#conditionContainer").hide();
    $context.find(".add-condition-btn-container").hide();
  } else {
    $context.find("#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]").show();
    $context.find("#id_specific_employees, [for=id_specific_employees],#id_is_condition_based, [for=id_is_condition_based]").parent().show();
  }

  if (
    $context.find("#id_is_condition_based").is(":checked") ||
    $context.find("#id_include_active_employees").is(":checked")
  ) {
    $context.find("#id_exclude_employees, [for=id_exclude_employees]").show();
    $context.find("#id_exclude_employees, [for=id_exclude_employees]").parent().show();
  } else {
    $context.find("#id_exclude_employees, [for=id_exclude_employees]").hide();
    $context.find("#id_exclude_employees, [for=id_exclude_employees]").parent().hide();
  }

  if ($context.find("#id_is_condition_based, #id_include_active_employees").is(":checked")) {
    $context.find("#id_specific_employees").parent().find("ul.select2-selection__rendered li").remove();
    $context.find("#id_specific_employees").val(null);
    $context.find("#id_specific_employees,[for=id_specific_employees]").hide();
    $context.find("#id_specific_employees,[for=id_specific_employees]").parent().hide();
  }

  if ($context.find("#id_has_max_limit").is(":checked")) {
    $context.find("#id_maximum_amount, [for=id_maximum_amount]").show();
    $context.find("#id_maximum_amount, [for=id_maximum_amount]").parent().show();
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").show();
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").parent().show();
  } else {
    $context.find("#id_maximum_amount, [for=id_maximum_amount]").hide();
    $context.find("#id_maximum_amount, [for=id_maximum_amount]").parent().hide();
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").hide();
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").parent().hide();
  }

  var opt = ["attendance", "shift_id", "overtime", "work_type_id"];
  if (!$context.find("#id_is_fixed").is(":checked") && opt.includes($context.find("#id_based_on").val())) {
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").hide();
    $context.find("#id_maximum_unit,[for=id_maximum_unit]").parent().hide();
  }

  if ($context.find("#id_is_fixed").is(":checked")) {
    $context.find("#id_has_max_limit").parent().parent().hide();
    $context.find("#id_maximum_unit,#id_maximum_amount").parent().hide();
  } else {
    $context.find("#id_has_max_limit").parent().parent().show();
    if ($context.find("#id_has_max_limit").is(":checked")) {
      $context.find("#id_maximum_unit,#id_maximum_amount").parent().show();
    }
  }

  if ($context.find("[name='if_condition']").val() == "range") {
    $context.find("#id_if_amount_parent_div").hide();
    $context.find("#id_start_range_parent_div").show();
    $context.find("#id_end_range_parent_div").show();
  } else {
    $context.find("#id_if_amount_parent_div").show();
    $context.find("#id_start_range_parent_div").hide();
    $context.find("#id_end_range_parent_div").hide();
  }
}

function conditionAdd(btn) {
  var $context = $(btn).closest("form");
  if (!$context.length) $context = $(document);

  // Clone label and input elements from the hidden default fields
  var fieldLabel = $context.find("[for=id_field]").clone().prop("outerHTML");
  var fieldInput = $context.find("#id_field").clone().attr("name", "other_fields").removeAttr("id").attr("class", "oh-select form-control").prop("outerHTML");

  var condLabel = $context.find("[for=id_condition]").clone().prop("outerHTML");
  var condInput = $context.find("#id_condition").clone().attr("name", "other_conditions").removeAttr("id").attr("class", "oh-select form-control").prop("outerHTML");

  var valLabel = $context.find("[for=id_value]").clone().prop("outerHTML");
  var valInput = $context.find("#id_value").clone().attr("name", "other_values").removeAttr("id").attr("class", "oh-input form-control").prop("outerHTML");

  var conditionSet = $(`
    <div class="condition-highlight row m-0 mb-2 condition-row">
      <div class="col-12 col-md-4">
        ${fieldLabel}
        ${fieldInput}
      </div>
      <div class="col-12 col-md-4">
        ${condLabel}
        ${condInput}
      </div>
      <div class="col-12 col-md-4">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          ${valLabel}
          <button type="button" onclick="$(this).closest('.condition-row').remove()" title="Remove" style="background:none;border:none;cursor:pointer;color:#dc3545;padding:0;line-height:1;flex-shrink:0;">
            <ion-icon name="trash-outline" style="font-size:16px;"></ion-icon>
          </button>
        </div>
        ${valInput}
      </div>
    </div>
  `);

  $context.find("#conditionContainer").append(conditionSet);

  // Initialize Select2 on the newly added selects
  conditionSet.find("select").each(function () {
    if ($.fn.select2) {
      $(this).select2({
        dropdownParent: $(this).closest(".condition-highlight"),
        width: "100%",
      });
    }
  });
}

$(document).ready(function () {
  $("form:has(#id_is_fixed)").each(function() {
    var $context = $(this);

    // ── Step 1: Wrap the 3 default condition columns into one highlighted box ──
    var $fieldParent = $context.find("#id_field_parent_div");
    var $condParent  = $context.find("#id_condition_parent_div");
    var $valParent   = $context.find("#id_value_parent_div");

    // Fallback: use grandparent traversal if explicit IDs not found
    if (!$fieldParent.length) $fieldParent = $context.find("#id_field").parent().parent();
    if (!$condParent.length)  $condParent  = $context.find("#id_condition").parent().parent();
    if (!$valParent.length)   $valParent   = $context.find("#id_value").parent().parent();

    if ($fieldParent.length && !$fieldParent.closest(".default-condition-row").length) {
      var $wrapper = $('<div class="default-condition-row condition-highlight row m-0 mb-2"></div>');
      $fieldParent.before($wrapper);
      // Use attr to REPLACE existing col classes entirely (not add on top)
      $fieldParent.attr("class", "col-12 col-md-4");
      $condParent.attr("class", "col-12 col-md-4");
      $valParent.attr("class", "col-12 col-md-4");
      $wrapper.append($fieldParent, $condParent, $valParent);
    }

    // ── Step 2: Insert the conditionContainer after the default row ──
    if ($context.find("#conditionContainer").length === 0) {
      var $container = $('<div id="conditionContainer" class="col-12 p-0"></div>');
      $context.find(".default-condition-row").first().after($container);
    }

    // ── Step 3: Insert "Add Condition" button after the is_condition_based toggle ──
    if ($context.find(".add-condition-btn-container").length === 0) {
      var $addMore = $(`
        <div class="add-condition-btn-container col-12" style="text-align:right;margin-top:-4px;margin-bottom:8px;">
          <a href="javascript:void(0)" onclick="conditionAdd(this)" title="Add Condition" class="text-primary-600"
             style="display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:500;">
            <ion-icon name="add-outline" style="font-size:14px;"></ion-icon>
            Add Condition
          </a>
        </div>
      `);
      $context.find("#id_is_condition_based_parent_div").after($addMore);
    }

    // ── Step 4: Bind change events ──
    $context.find("select, [type=checkbox]").change(function (e) {
      e.preventDefault();
      conditionalVisibility($context);
    });

    // ── Step 5: Run initial visibility ──
    conditionalVisibility($context);
    // Trigger the condition-based toggle to set initial state
    $context.find("#id_is_condition_based").trigger("change");
  });
});
