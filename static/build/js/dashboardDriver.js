
const driver = window.driver.js.driver;



var steps = [
    { popover: { title: 'Dashboard', description: 'Horilla dashboard section' } },
    { element: '#attendance-activity-container', popover: { title: 'Mark Attendance', description: 'Used to mark your attendance' } },
];

if ($('#settingsMenu').length) {
    steps.push({ element: '#settingsMenu', popover: { title: 'Settings', description: 'Settings configurations' } });
}

if ($('#notificationIcon').length) {
    steps.push({ element: '#notificationIcon', popover: { title: 'Notification', description: 'Notifications section' } });
}

if ($('#multiLanguage').length) {
    steps.push({ element: '#multiLanguage', popover: { title: 'Language', description: 'Multi-Language options' } });
}
if ($('#multCompany').length) {
    steps.push({ element: '#multCompany', popover: { title: 'Multi-Company', description: 'Multi-Company options' } });
}
if ($('#mainNavProfile').length) {
    steps.push({ element: '#mainNavProfile', popover: { title: 'Profile', description: 'Profile and change password options' } });
}
if ($('.oh-card-dashboard').length) {
    steps.push({ element: '#tileContainer .oh-card-dashboard:nth-child(1)', popover: { title: 'Dashboard Tiles', description: 'Horilla Dashboard Tiles' } });
}
setTimeout(() => {
    if ($('.oh-btn-group').length) {
        steps.push({ element: '.oh-btn-group:nth-child(1)', popover: { title: 'Dashboard Actions', description: 'Approve or Reject Options' } });
    }
    if ($('#addAnnouncement').length) {
        steps.push({ element: '#addAnnouncement', popover: { title: 'Add announcement', description: 'Create announcement from dashboard' } });
    }
    if ($('#quickActions').length) {
        steps.push({ element: '#quickActions', popover: { title: 'Quick Actions', description: 'Create Quick Requests' } });
    }
    if ($('.oh-sidebar__company').length) {
        steps.push({ element: '.oh-sidebar__company:nth-child(1)', popover: { title: 'Company', description: 'Your current company access' } });
    }
    if ($('[data-id="dashboardNav"]').length) {
        steps.push({ element: '[data-id="dashboardNav"]', popover: { title: 'App', description: 'Horilla Hr Apps. eg Dashboard' } });
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
