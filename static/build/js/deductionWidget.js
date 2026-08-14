function conditionalVisibility($context) {
  $context = $context || $(document);

  // Helper: show/hide a field's entire col wrapper (works for both plain inputs
  // and checkboxes wrapped in oh-switch). Uses the id_X_parent_div convention.
  function showField(ids) {
    ids.forEach(function(id) {
      var $el = $context.find(id);
      $el.show();
      $el.parent().show();
      // For checkboxes inside oh-switch, also show the col wrapper
      var $parentDiv = $context.find(id + '_parent_div');
      if ($parentDiv.length) $parentDiv.show();
    });
  }
  function hideField(ids) {
    ids.forEach(function(id) {
      var $el = $context.find(id);
      $el.hide();
      $el.parent().hide();
      // For checkboxes inside oh-switch, also hide the col wrapper
      var $parentDiv = $context.find(id + '_parent_div');
      if ($parentDiv.length) $parentDiv.hide();
    });
  }

  // Also show/hide by [for=] selectors (labels / oh-label__info divs)
  function showLabel(ids) {
    ids.forEach(function(id) {
      var bare = id.replace('#', '');
      $context.find('[for=' + bare + ']').show();
      $context.find('[for=' + bare + ']').parent().show();
    });
  }
  function hideLabel(ids) {
    ids.forEach(function(id) {
      var bare = id.replace('#', '');
      $context.find('[for=' + bare + ']').hide();
      $context.find('[for=' + bare + ']').parent().hide();
    });
  }

  // --- is_condition_based ---
  if (!$context.find('#id_is_condition_based').is(':checked')) {
    $context.find('[onclick="conditionAdd(this)"]').parent().hide();
    $context.find('.add-condition-btn-container').hide();
    $context.find('#conditionContainer').hide();
    hideField(['#id_field', '#id_value', '#id_condition']);
    hideLabel(['#id_field', '#id_value', '#id_condition']);
  } else {
    $context.find('[onclick="conditionAdd(this)"]').parent().show();
    $context.find('.add-condition-btn-container').show();
    $context.find('#conditionContainer').show();
    showField(['#id_field', '#id_value', '#id_condition']);
    showLabel(['#id_field', '#id_value', '#id_condition']);
  }

  // --- is_tax ---
  if ($context.find('#id_is_tax').is(':checked')) {
    $context.find('#id_is_fixed').prop('checked', false);
    showField(['#id_based_on', '#id_rate']);
    showLabel(['#id_based_on', '#id_rate']);
    hideField(['#id_is_condition_based', '#id_field', '#id_condition', '#id_value']);
    hideLabel(['#id_is_condition_based', '#id_field', '#id_condition', '#id_value']);
    hideField(['#id_is_fixed', '#id_amount', '#id_employer_rate', '#id_is_pretax']);
    hideLabel(['#id_is_fixed', '#id_amount', '#id_employer_rate', '#id_is_pretax']);
  } else {
    hideField(['#id_based_on', '#id_rate']);
    hideLabel(['#id_based_on', '#id_rate']);
    showField(['#id_is_fixed', '#id_amount', '#id_employer_rate', '#id_is_pretax']);
    showLabel(['#id_is_fixed', '#id_amount', '#id_employer_rate', '#id_is_pretax']);
  }

  // --- is_fixed ---
  if (!$context.find('#id_is_fixed').is(':checked')) {
    showField(['#id_based_on', '#id_rate', '#id_employer_rate']);
    showLabel(['#id_based_on', '#id_rate', '#id_employer_rate']);
    hideField(['#id_amount']);
    hideLabel(['#id_amount']);
  } else {
    hideField(['#id_based_on', '#id_rate', '#id_employer_rate']);
    hideLabel(['#id_based_on', '#id_rate', '#id_employer_rate']);
    showField(['#id_amount']);
    showLabel(['#id_amount']);
  }

  // --- include_active_employees ---
  if ($context.find('#id_include_active_employees').is(':checked')) {
    $context.find('#id_is_condition_based').prop('checked', false);
    hideField(['#id_specific_employees', '#id_is_condition_based']);
    hideLabel(['#id_specific_employees', '#id_is_condition_based']);
    hideField(['#id_field', '#id_condition', '#id_value']);
    hideLabel(['#id_field', '#id_condition', '#id_value']);
  } else {
    showField(['#id_is_condition_based']);
    showLabel(['#id_is_condition_based']);
    if ($context.find('#id_is_condition_based').is(':checked')) {
      showField(['#id_field', '#id_condition', '#id_value']);
      showLabel(['#id_field', '#id_condition', '#id_value']);
    }
  }

  // --- exclude_employees ---
  if (
    $context.find('#id_is_condition_based').is(':checked') ||
    $context.find('#id_include_active_employees').is(':checked')
  ) {
    showField(['#id_exclude_employees']);
    showLabel(['#id_exclude_employees']);
  } else {
    hideField(['#id_exclude_employees']);
    hideLabel(['#id_exclude_employees']);
  }
  if ($context.find('#id_is_condition_based').is(':checked')) {
    hideField(['#id_specific_employees']);
    hideLabel(['#id_specific_employees']);
  }

  // --- has_max_limit / maximum fields ---
  if ($context.find('#id_has_max_limit').is(':checked')) {
    showField(['#id_maximum_amount', '#id_maximum_unit']);
    showLabel(['#id_maximum_amount', '#id_maximum_unit']);
  } else {
    hideField(['#id_maximum_amount', '#id_maximum_unit']);
    hideLabel(['#id_maximum_amount', '#id_maximum_unit']);
  }

  // --- update_compensation ---
  var updateCompVal = $context.find('#id_update_compensation').val();
  if (updateCompVal && updateCompVal !== '' && updateCompVal !== 'null' && updateCompVal !== undefined) {
    $context.find('#id_include_active_employees').prop('checked', false);
    $context.find('#id_is_fixed').prop('checked', false);
    hideField(['#id_is_tax', '#id_is_pretax', '#id_based_on']);
    hideLabel(['#id_is_tax', '#id_is_pretax', '#id_based_on']);
    hideField(['#id_if_choice', '#id_if_condition', '#id_is_fixed', '#id_include_active_employees', '#id_is_condition_based']);
    hideLabel(['#id_if_choice', '#id_if_condition', '#id_is_fixed', '#id_include_active_employees', '#id_is_condition_based']);
    hideField(['#id_field', '#id_condition', '#id_value']);
    hideLabel(['#id_field', '#id_condition', '#id_value']);
    hideField(['#id_has_max_limit', '#id_maximum_amount', '#id_maximum_unit']);
    hideLabel(['#id_has_max_limit', '#id_maximum_amount', '#id_maximum_unit']);
    showField(['#id_amount']);
    showLabel(['#id_amount']);
    hideField(['#id_if_amount']);
    hideLabel(['#id_if_amount']);
    $context.find('#id_is_condition_based').prop('checked', false);
    // Show rate/employer_rate if they were hidden
    $context.find('#id_rate:hidden, #id_employer_rate:hidden').show().parent().show();
    $context.find('#id_rate_parent_div:hidden, #id_employer_rate_parent_div:hidden').show();
  } else {
    showField(['#id_is_tax']);
    showLabel(['#id_is_tax']);
    showField(['#id_has_max_limit']);
    showLabel(['#id_has_max_limit']);
    showField(['#id_if_choice', '#id_if_condition', '#id_if_amount']);
    showLabel(['#id_if_choice', '#id_if_condition', '#id_if_amount']);
  }

  // --- is_fixed hides has_max_limit col wrapper ---
  if ($context.find('#id_is_fixed').is(':checked')) {
    $context.find('#id_has_max_limit_parent_div').hide();
    hideField(['#id_maximum_unit', '#id_maximum_amount']);
  } else {
    $context.find('#id_has_max_limit_parent_div').show();
    if ($context.find('#id_has_max_limit').is(':checked')) {
      showField(['#id_maximum_unit', '#id_maximum_amount']);
    }
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
  $("form:has(#id_is_condition_based), form:has(#id_is_fixed)").each(function() {
    var $context = $(this);


    $context.find("#id_condition, #id_field, #id_value").parent().attr("class", "col-12 col-md-4 condition-highlight");

    // Add container for dynamic conditions
    var $conditionContainer = $(`<div id="conditionContainer" class="col-12 col-md-12 mt-2"></div>`);
    if ($context.find('#conditionContainer').length === 0) {
        $context.find('#id_value').parent().after($conditionContainer);
    }

    // Range conditional toggle logic
    function handleRangeToggle() {
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

    // Bind change events
    $context.find("input[type='checkbox'], select, input[type='radio']").change(function (e) {
      // e.preventDefault(); // removed to fix checkbox issues
      conditionalVisibility($context);
      handleRangeToggle();
    });

    // Initial run
    conditionalVisibility($context);
    handleRangeToggle();
    $context.find("#id_is_condition_based").trigger("change");
  });
});
