var formButton = "#applyFilter";

function clearFilterFromTag(element) {
	let form = $(formButton).closest('form');
	let search_url = form.attr("hx-get") || "";
	let urlParts = search_url.split('?');
	let baseUrl = urlParts[0];
	let field_id = element.attr("data-x-field");

	if (urlParts.length > 1) {
		let params = new URLSearchParams(urlParts[1]);
		let keysToRemove = [];
		for (let key of params.keys()) {
			let is_in_form = form.find('[name]').filter(function () { return this.name === key; }).length > 0;
			if (key === field_id || is_in_form) {
				keysToRemove.push(key);
			}
		}
		for (let key of keysToRemove) {
			params.delete(key);
		}
		let newParams = params.toString();
		form.attr("hx-get", newParams ? baseUrl + '?' + newParams : baseUrl);
	} else {
		form.attr("hx-get", baseUrl);
	}

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
}

function clearAllFilter(element) {
	$('[role="tooltip"]').remove();
	let form = $(formButton).closest('form')
	let search_url = form.attr("hx-get")
	let swap_target = form.attr("hx-target")
	form.attr("hx-get", search_url.split('?')[0])
	let newUrl = search_url.split('?')[0]
	htmx.ajax("GET", newUrl, {
		target: swap_target,
		swap: "innerHTML"
	});
	localStorage.removeItem("savedFilters");
}
