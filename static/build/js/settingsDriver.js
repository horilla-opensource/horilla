const driver = window.driver.js.driver;



var steps = [
    { popover: { title: 'Settings', description: 'All your company and base configurations' } },
];

if ($(".col-12.col-sm-12.col-md-12.col-lg-3").length) {
    steps.push(
        { element: '.col-12.col-sm-12.col-md-12.col-lg-3', popover: { title: 'Settings Options', description: 'Settings menu bar' } },
    )

}
if ($(".col-12.col-sm-12.col-md-12.col-lg-9").length) {
    steps.push(
        { element: '.col-12.col-sm-12.col-md-12.col-lg-9', popover: { title: 'Settings View', description: 'Selected settings view' } },
    )

}


driverObj = driver(

    {
        showProgress: false,
        animate: true,
        showButtons: ['next', 'previous', 'close'],
        steps: steps,


    }
)



function runDriver() {
    // Start driving after checking all steps
    driverObj.drive();
    $.ajax({
        type: "get",
        url: "/driver-viewed?user=" + $(".logged-in[data-user-id]").attr("data-user-id") + "&viewed=settings",
        success: function (response) {

        }
    });
}
