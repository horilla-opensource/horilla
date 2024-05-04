function toggleColumns(tableId, fieldContainer) {
    var table = $(`#${tableId}[data-table-name]`)
    table.hide()
    var tableTitle = table.attr("data-table-name")
    let trs = []
    $.each($(`[data-table-name=${tableTitle}] [data-cell-title]`), function (indexInArray, valueOfElement) {
        trs.push(`
            <li class="oh-dropdown__item oh-sticy-dropdown-item">
                <span>${$(valueOfElement).attr("data-cell-title")}</span>
                <span class="oh-table__checkbox">
                    <input type="checkbox" name="showTableColumn" onchange="hideCells($(this),'${tableTitle}','${fieldContainer}')" value="${$(valueOfElement).attr("data-cell-index")}"/>
                </span>
            </li>
         `)
    });

    // toggle cells
    var visibleCells = localStorage.getItem(tableTitle)
    if (visibleCells && visibleCells != "[]") {
        table.hide();
        $("[data-cell-index]").hide();
    }
    else {
        table.show();
        $("[data-cell-index]").show();
    }

    trsString = ""
    for (let tr = 0; tr < trs.length; tr++) {
        const element = trs[tr];
        trsString = trsString + element
    }
    let selectButtons = $(`
    <div class="oh-dropdown_btn-header">
    <button onclick="$(this).parent().parent().find('[type=checkbox]').prop('checked',true).change()" class="oh-btn oh-btn--success-outline">Select All Rows</button>
    <button onclick="$(this).parent().parent().find('[type=checkbox]').prop('checked',false).change()" class="oh-btn oh-btn--primary-outline">Unselect All Rows</button>
    </div>
    `)
    $(`#${fieldContainer}`).parent().prepend(selectButtons)
    $(`#${fieldContainer}`).html(trsString);
    if (visibleCells) {
        storedIds = JSON.parse(visibleCells)
        $(`#${fieldContainer} input[type=checkbox]`).prop("checked", false)
        for (let id = 0; id < storedIds.length; id++) {
            const element = storedIds[id];
            $(`#${fieldContainer} input[type=checkbox][value=${element}]`).prop("checked", true)
            hideCells($(`#${fieldContainer} input[type=checkbox][value=${element}]`), tableTitle, fieldContainer)
        }
        $(`[data-table-name][data-table-name=${tableTitle}]`).show();
    }
}
function hideCells(jqElement, tableTitle, fieldContainer) {
    visibleCells = $(`#${fieldContainer}`).find("input[type=checkbox]:checked")
    let visibleCellsids = []
    $(`[data-table-name=${tableTitle}] [data-cell-index]`).hide();
    $.each(visibleCells, function (indexInArray, valueOfElement) {
        $(`[data-table-name=${tableTitle}] [data-cell-index=${$(valueOfElement).val()}]`).show();
        visibleCellsids.push($(valueOfElement).val())
    });
    if (jqElement.is(":checked")) {
        var storedIdsSet = new Set(JSON.parse(localStorage.getItem(tableTitle)) || []);
        storedIdsSet.add(jqElement.val());
        var storedIds = Array.from(storedIdsSet);
        localStorage.setItem(tableTitle, JSON.stringify(storedIds));
    } else {
        var storedIds = JSON.parse(localStorage.getItem(tableTitle)) || [];
        var index = storedIds.indexOf(jqElement.val());
        if (index !== -1) {
            storedIds.splice(index, 1);
            localStorage.setItem(tableTitle, JSON.stringify(storedIds));
        }
    }
    $(`[data-table-name=${tableTitle}][data-table-name]`).show();
}
