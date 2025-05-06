var formButton = "#applyFilter";
function clearFilterFromTag(element) {
  let field_id = element.attr("data-x-field");
  $(`[name=${field_id}]`).val("");
  $(`[name=${field_id}]`).change();
  // Update all elements with the same ID to have null values
  let elementId = $(`[name=${field_id}]:last`).attr("id");
  let spanElement = $(
    `.oh-dropdown__filter-body:first #select2-id_${field_id}-container, #select2-${elementId}-container`
  );
  if (spanElement.length) {
    spanElement.attr("title", "---------");
    spanElement.text("---------");
  }
  $(formButton).click();
  console.log($(formButton));
}
function clearAllFilter(element) {
  $('[role="tooltip"]').remove();
  let field_ids = $("[data-x-field]");
  for (var i = 0; i < field_ids.length; i++) {
    let item_id = field_ids[i].getAttribute("data-x-field");

    $(`[name=${item_id}]`).val("");
    $(`[name=${item_id}]`).change();
    let elementId = $(`[name=${item_id}]:last`).attr("id");
    let spanElement = $(
      `.oh-dropdown__filter-body:first #select2-id_${item_id}-container, #select2-${elementId}-container`
    );
    if (spanElement.length) {
      spanElement.attr("title", "---------");
      spanElement.text("---------");
    }
    $(formButton).click();
    localStorage.removeItem("savedFilters");
    var url = window.location.href.split("?")[0];
    window.history.replaceState({}, document.title, url);
  }
}
