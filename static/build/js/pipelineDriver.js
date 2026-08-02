const driver = window.driver.js.driver;



var steps = [
    { popover: { title: gettext('Pipeline'), description: gettext('Recruitment pipeline management') } },
    { element: '#createNewRecruitment', popover: { title: gettext('New Recruitment'), description: gettext('Add new recruitment') } },
    { element: '#pipelineFilterDrop', popover: { title: gettext('Filter'), description: gettext('Pipeline filter option') } },
    { element: '#viewTypes', popover: { title: gettext('Toggle View'), description: gettext('Toggle view type') } },
    { element: '#pipelineSearchInput', popover: { title: gettext('Search'), description: gettext('Search in candidate, recruitment and stage') } },
    { element: '.filter-field', popover: { title: gettext('Filter Tag'), description: gettext('Filter tag option') } },
    { element: '#quickFilters', popover: { title: gettext('Quick Filters'), description: gettext('Quick Filters') } },
    { element: '.oh-tabs__tab.oh-tabs__tab--active', popover: { title: gettext('Recruitment'), description: gettext('Recruitment') } },
    { element: '.oh-tabs__content--active [data-target="#addStageModal"]', popover: { title: gettext('Add Stage'), description: gettext('Add new stage to recruitment') } },
    { element: '.oh-tabs__content--active .oh-tabs__movable', popover: { title: gettext('Stage'), description: gettext('Recruitment stage') } },
    { element: '.oh-tabs__content--active .oh-tabs__movable .oh-btn--secondary-outline', popover: { title: gettext('Add candidate'), description: gettext('Add candidate to stage option') } },
    { element: '.oh-tabs__content--active .oh-table-config__td', popover: { title: gettext('Candidate'), description: gettext('Candidate record') } },
    { element: '.oh-tabs__content--active .oh-table-config__td form', popover: { title: gettext('Rating'), description: gettext('Candidate rating option') } },
    { element: '.oh-tabs__content--active .oh-select.w-100.stage-change', popover: { title: gettext('Change Stage'), description: gettext('Candidate change stage option') } },
    { element: '.oh-tabs__content--active .oh-table-config__td .oh-btn-group', popover: { title: gettext('Options'), description: gettext('Candidate management options') } },
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
