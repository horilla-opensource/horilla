const driver = window.driver.js.driver;



var steps = [
    { popover: { title: 'Pipeline', description: 'Recruitment pipeline management' } },
    { element: '#createNewRecruitment', popover: { title: 'New Recruitment', description: 'Add new recruitment' } },
    { element: '#pipelineFilterDrop', popover: { title: 'Filter', description: 'Pipeline filter option' } },
    { element: '#viewTypes', popover: { title: 'Toggle View', description: 'Toggle view type' } },
    { element: '#pipelineSearchInput', popover: { title: 'Search', description: 'Search in candidate, recruitment and stage' } },
    { element: '.filter-field', popover: { title: 'Filter Tag', description: 'Filter tag option' } },
    { element: '#quickFilters', popover: { title: 'Quick Filters', description: 'Quick Filters' } },
    { element: '.oh-tabs__tab.oh-tabs__tab--active', popover: { title: 'Recruitment', description: 'Recruitment' } },
    { element: '.oh-tabs__content--active [data-target="#addStageModal"]', popover: { title: 'Add Stage', description: 'Add new stage to recruitment' } },
    { element: '.oh-tabs__content--active .oh-tabs__movable', popover: { title: 'Stage', description: 'Recruitment stage' } },
    { element: '.oh-tabs__content--active .oh-tabs__movable .oh-btn--secondary-outline', popover: { title: 'Add candidate', description: 'Add candidate to stage option' } },
    { element: '.oh-tabs__content--active .oh-table-config__td', popover: { title: 'Candidate', description: 'Candidate record' } },
    { element: '.oh-tabs__content--active .oh-table-config__td form', popover: { title: 'Rating', description: 'Candidate rating option' } },
    { element: '.oh-tabs__content--active .oh-select.w-100.stage-change', popover: { title: 'Change Stage', description: 'Candidate change stage option' } },
    { element: '.oh-tabs__content--active .oh-table-config__td .oh-btn-group', popover: { title: 'Options', description: 'Candidate management options' } },
];


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
        url: "/driver-viewed?user=" + $(".logged-in[data-user-id]").attr("data-user-id") + "&viewed=pipeline",
        success: function (response) {

        }
    });
}
