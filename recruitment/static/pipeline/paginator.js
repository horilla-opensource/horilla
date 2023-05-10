// paginator
$(document).ready(function () {
$('.candidate-table').each(function() {
    var id = $(this).attr('data-stage-id');
    let table = $(`#candidateTable${id}`)
    let container = $(`#candidateContainer${id} .change-cand`)
    var navId = id
table.after(`<div id="nav${navId}"></div>`);
var rowsShown = 1;
var rowsTotal = container.length;
var numPages = rowsTotal / rowsShown;
for (var i = 0; i < numPages; i++) {
    var pageNum = i + 1;
    $(`#nav${navId}`).append('<a href="#" rel="' + i + '">' + pageNum + "</a> ");
}
$(`#nav${navId}`).prepend(
    '<input type="number" min="1" max="' + numPages + '" value="1">'
);
container.hide();
container.slice(0, rowsShown).show();
$(`#nav${navId} a:first`).addClass("active");
$(`#nav${navId} a`).bind("click", function () {
    $(`#nav${navId} a`).removeClass("active");
    $(this).addClass("active");
    var currPage = $(this).attr("rel");
    var startItem = currPage * rowsShown;
    var endItem = startItem + rowsShown;
    container
    .css("opacity", "0.0")
    .hide()
    .slice(startItem, endItem)
    .css("display", "table-row")
    .animate(
        {
        opacity: 1,
        },
        300
    );
});
$(`#nav${navId} input`).bind("change", function () {
    var pageNum = $(this).val() - 1;
    if (pageNum >= 0 && pageNum < numPages) {
    $(`#nav${navId} a`).removeClass("active");
    $(`#nav${navId} a[rel=" + ${pageNum} + "]`).addClass("active");
    var startItem = pageNum * rowsShown;
    var endItem = startItem + rowsShown;
    $("#candidateTable1 tbody tr")
        .css("opacity", "0.0")
        .hide()
        .slice(startItem, endItem)
        .css("display", "table-row")
        .animate(
        {
            opacity: 1,
        },
        300
        );
    } else {
    $(this).val("");
    }
});
});

});
