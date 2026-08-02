
const driver = window.driver.js.driver;



var steps = [
    { popover: { title: gettext('Dashboard'), description: gettext('Horilla dashboard section') } },
    { element: '#attendance-activity-container', popover: { title: gettext('Mark Attendance'), description: gettext('Used to mark your attendance') } },
];

if ($('#settingsMenu').length) {
    steps.push({ element: '#settingsMenu', popover: { title: gettext('Settings'), description: gettext('Settings configurations') } });
}

if ($('#notificationIcon').length) {
    steps.push({ element: '#notificationIcon', popover: { title: gettext('Notification'), description: gettext('Notifications section') } });
}

if ($('#multiLanguage').length) {
    steps.push({ element: '#multiLanguage', popover: { title: gettext('Language'), description: gettext('Multi-Language options') } });
}
if ($('#multCompany').length) {
    steps.push({ element: '#multCompany', popover: { title: gettext('Multi-Company'), description: gettext('Multi-Company options') } });
}
if ($('#mainNavProfile').length) {
    steps.push({ element: '#mainNavProfile', popover: { title: gettext('Profile'), description: gettext('Profile and change password options') } });
}
if ($('.oh-card-dashboard').length) {
    steps.push({ element: '#tileContainer .oh-card-dashboard:nth-child(1)', popover: { title: gettext('Dashboard Tiles'), description: gettext('Horilla Dashboard Tiles') } });
}
setTimeout(() => {
    if ($('.oh-btn-group').length) {
        steps.push({ element: '.oh-btn-group:nth-child(1)', popover: { title: gettext('Dashboard Actions'), description: gettext('Approve or Reject Options') } });
    }
    if ($('#addAnnouncement').length) {
        steps.push({ element: '#addAnnouncement', popover: { title: gettext('Add announcement'), description: gettext('Create announcement from dashboard') } });
    }
    if ($('#quickActions').length) {
        steps.push({ element: '#quickActions', popover: { title: gettext('Quick Actions'), description: gettext('Create Quick Requests') } });
    }
    if ($('.oh-sidebar__company').length) {
        steps.push({ element: '.oh-sidebar__company:nth-child(1)', popover: { title: gettext('Company'), description: gettext('Your current company access') } });
    }
    if ($('[data-id="dashboardNav"]').length) {
        steps.push({ element: '[data-id="dashboardNav"]', popover: { title: gettext('App'), description: gettext('Horilla Hr Apps. eg Dashboard') } });
    }
}, 1000);
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
        url: "/driver-viewed?user=" + $(".logged-in[data-user-id]").attr("data-user-id") + "&viewed=dashboard",
        success: function (response) {

        }
    });
}
