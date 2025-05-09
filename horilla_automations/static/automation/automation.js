function getToMail(element) {
  model = element.val();
  $.ajax({
    type: "get",
    url: "/get-to-mail-field",
    data: {
      model: model,
    },
    success: function (response) {
      $(".dynamic-condition-row").remove();
      select = $("#id_mail_to");
      select.html("");
      detailSelect = $("#id_mail_details");
      detailSelect.html("");
      mailTo = response.choices;
      mailDetail = response.mail_details_choice;

      for (let option = 0; option < mailTo.length; option++) {
        const element = mailTo[option];

        var selected = option === 0; // Set the first option as selected
        var newOption = new Option(element[1], element[0], selected, selected);
        select.append(newOption);
      }
      for (let option = 0; option < mailDetail.length; option++) {
        const element = mailDetail[option];

        var selected = option === 0; // Set the first option as selected
        var newOption = new Option(element[1], element[0], selected, selected);
        detailSelect.append(newOption);
      }
      select.trigger("change");
      detailSelect.trigger("change");

      table = $("#multipleConditionTable");
      $("#multipleConditionTable select").select2("destroy");

      totalRows = "C" + (table.find(".dynamic-condition-row").length + 1);

      fieldsChoices = [];
      $.each(response.serialized_form, function (indexInArray, valueOfElement) {
        fieldsChoices.push([valueOfElement["name"], valueOfElement["label"]]);
      });
      selectField = populateSelect(fieldsChoices, response);
      tr = `
      <tr class="dynamic-condition-row">
        <td class="sn">${totalRows}</td>
        <td id="conditionalField">
        <div hidden>${JSON.stringify(response.serialized_form)}</div>
        </td>
        <td>
        <select name="condition" onchange="addSelectedAttr(event)" class="w-100">
          <option value="==">==</option>
          <option value="!=">!=</option>
        </select>
        </td>
        <td class="condition-value-th"></td>
        <td>
        <select name="logic" onchange="addSelectedAttr(event)" class="w-100">
            <option value="and">And</option>
            <option value="or">Or</option>
        </select>
        </td>
        <td>
        <div class="oh-btn-group">
          <button
           class="oh-btn oh-btn oh-btn--light p-2 w-50"
           onclick="
            event.preventDefault();
            var clonedElement = $(this).closest('tr').clone();
            totalRows ='C' +( $(this).closest('table').find('.dynamic-condition-row').length + 1);
            clonedElement.find('.sn').html(totalRows)
            clonedElement.find('select').parent().find('span').remove()
            clonedElement.find('select').attr('class','w-100')

            $(this).closest('tr').parent().append(clonedElement)
            $('#multipleConditionTable').find('select').select2()
           "
          >
            <ion-icon name="copy-outline"></ion-icon>
          </button>
          <button
           class="oh-btn oh-btn oh-btn--light p-2 w-50"
           onclick="
            event.preventDefault();
            $(this).closest('tr').remove();
           "
          >
            <ion-icon name="trash-outline"></ion-icon>
          </button>
        </div>
        </td>
      </tr>
    `;
      table.find("tr:last").after(tr);
      $("#conditionalField").append(selectField);
      $("#multipleConditionTable select").select2();
      selectField.trigger("change");
      selectField.attr("name", "automation_multiple_condition");
    },
  });
}

function getHtml() {
  var htmlCode = `
    <form id ="multipleConditionForm">
      <table id="multipleConditionTable">
        <tr>
          <th>Code</th>
          <th>Field</th>
          <th>Condition</th>
          <th>Value</th>
          <th>Logic</th>
          <th>
          Action
          <span title="Reload" onclick="$('[name=model]').change()">
            <ion-icon name="refresh-circle"></ion-icon>
          </span>
          </th>
        </tr>
      </table>
    </form>
    <script>
    $("#multipleConditionTable").closest("[contenteditable=true]").removeAttr("contenteditable");
    </script>
  `;
  return $(htmlCode);
}

function populateSelect(data, response) {
  const selectElement = $(
    `<select class="w-100" onchange="updateValue($(this));addSelectedAttr(event)"></select>`
  );

  data.forEach((item) => {
    const $option = $("<option></option>");
    $option.val(item[0]);
    $option.text(item[1]);
    selectElement.append($option);
  });
  return selectElement;

}

function updateValue(element) {
  console.log(">>>>>>>>>>>>>>>>>>>>>>")
  json = element.closest('table').find('#conditionalField div[hidden]').text()
  console.log(json)

  field = element.val();
  // attr = json
  //   .replace(/[\u0000-\u001F\u007F-\u009F]/g, "")
  //   .replace(/\\n/g, "\\\\n")
  //   .replace(/\\t/g, "\\\\t");

  response = JSON.parse(json);

  valueElement = createElement(field, response);
  element.closest("tr").find(".condition-value-th").html("");
  element.closest("tr").find(".condition-value-th").html(valueElement);
  if (valueElement.is("select")) {
    valueElement.select2();
  }
}

function createElement(field, serialized_form) {
  let element;
  fieldItem = {};

  $.each(serialized_form, function (indexInArray, valueOfElement) {
    if (valueOfElement.name == field) {
      fieldItem = valueOfElement;
    }
  });

  switch (fieldItem.type) {
    case "CheckboxInput":
      element = document.createElement("input");
      element.type = "checkbox";
      element.checked = true;
      element.onchange = function () {
        if (this.checked) {
          $(this).attr("checked", true);
          $(this).val("on");
        } else {
          $(this).attr("checked", false);
          $(this).val("off");
        }
      };
      element.name = "automation_multiple_condition";
      element.className = "oh-switch__checkbox oh-switch__checkbox";
      // Create the wrapping div
      const wrapperDiv = document.createElement("div");
      wrapperDiv.className = "oh-switch";
      wrapperDiv.style.width = "30px";
      // Append the checkbox input to the div
      wrapperDiv.appendChild(element);
      $(element).change();
      element = wrapperDiv;
      break;

    case "Select":
    case "SelectMultiple":
      element = document.createElement("select");
      if (fieldItem.type === "SelectMultiple") {
        element.multiple = true;
      }
      element.onchange = function (event) {
        addSelectedAttr(event);
      };
      fieldItem.options.forEach((optionValue) => {
        if (optionValue.value) {
          const option = document.createElement("option");
          option.value = optionValue.value;
          option.textContent = optionValue.label;
          element.appendChild(option);
        }
      });
      break;

    case "Textarea":
      element = document.createElement("textarea");
      element.style = `
      height: 29px !important;
      margin-top: 5px;
      `;
      element.className = "oh-input w-100";
      if (fieldItem.max_length) {
        element.maxLength = fieldItem.max_length;
      }
      element.onchange = function (event) {
        $(this).html($(this).val());
      };
      break;
    case "TextInput":
      element = document.createElement("input");
      element.type = "text";
      element.style = `
      height: 30px !important;
      `;
      element.className = "oh-input w-100";
      if (fieldItem.max_length) {
        element.maxLength = fieldItem.max_length;
      }
      element.onchange = function (event) {
        $(this).attr("value", $(this).val());
      };
      break;
    case "EmailInput":
      element = document.createElement("input");
      element.type = "email";
      element.style = `
      height: 30px !important;
      `;
      element.className = "oh-input w-100";
      if (fieldItem.max_length) {
        element.maxLength = fieldItem.max_length;
      }
      element.onchange = function (event) {
        $(this).attr("value", $(this).val());
      };
      break;
    case "NumberInput":
      element = document.createElement("input");
      element.type = "number";
      element.style = `
      height: 30px !important;
      `;
      element.className = "oh-input w-100";
      if (fieldItem.max_length) {
        element.maxLength = fieldItem.max_length;
      }
      element.onchange = function (event) {
        $(this).attr("value", $(this).val());
      };
      break;
    default:
      element = document.createElement("input");
      element.type = "text";
      element.style = `
      height: 30px !important;
      `;
      element.className = "oh-input w-100";
      if (fieldItem.max_length) {
        element.maxLength = fieldItem.max_length;
      }
      element.onchange = function (event) {
        $(this).attr("value", $(this).val());
      };
      break;
  }
  if (element) {
    element.name = "automation_multiple_condition";
    if (fieldItem.required) {
      element.required = true;
    }

    // Create label
    const label = document.createElement("label");
    label.textContent = fieldItem.label;
    label.htmlFor = "automation_multiple_condition";

    return $(element);
  }
}

function addSelectedAttr(event) {
  const options = Array.from(event.target.options);
  options.forEach((option) => {
    if (option.selected) {
      option.setAttribute("selected", "selected");
    } else {
      option.removeAttribute("selected");
    }
  });
}
