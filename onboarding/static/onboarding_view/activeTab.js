$(document).ready(function () {
    var activeTab = localStorage.getItem('activeTabOnboarding')
    if (activeTab != null) {
        var tab = $(`[data-target="${activeTab}"]`)
        var tabContent = $(activeTab)
        $(tab).attr('class', 'oh-tabs__tab oh-tabs__tab--active');
        $(tabContent).attr('class', 'oh-tabs__content oh-tabs__content--active');
    }
    else {
        var targetId = $('.oh-tabs__tab[data-target]:first').attr("data-target")
        $('.oh-tabs__tab[data-target]:first').attr('class', 'oh-tabs__tab oh-tabs__tab--active');
        $(`${targetId}`).attr('class', 'oh-tabs__content oh-tabs__content--active');
    }
    $('.oh-tabs__tab').click(function (e) {
        var activeTab = $(this).attr('data-target');
        localStorage.setItem('activeTabOnboarding', activeTab)
    });
});
    