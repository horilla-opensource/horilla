$(document).ready(function () {
    var activeTab = localStorage.getItem("activeTabRecruitment");
    var tab = activeTab ? $(`[data-target="${activeTab}"]`).first() : $();
    var tabContent = activeTab ? $(activeTab).first() : $();

    // Fallback to first available recruitment tab when saved target is stale/missing.
    if (!tab.length || !tabContent.length) {
        tab = $(".oh-tabs__tab").first();
        var firstTarget = tab.attr("data-target");
        tabContent = firstTarget ? $(firstTarget).first() : $();
    }

    if (tab.length && tabContent.length) {
        $(".oh-tabs__tab").removeClass("oh-tabs__tab--active");
        $(".oh-tabs__content").removeClass("oh-tabs__content--active");
        tab.addClass("oh-tabs__tab--active");
        tabContent.addClass("oh-tabs__content--active");
    }

    $(".oh-tabs__tab").click(function () {
        var currentTarget = $(this).attr("data-target");
        if (currentTarget) {
            localStorage.setItem("activeTabRecruitment", currentTarget);
        }
    });
});

  $(document).ready(function () {
    $('.oh-tabs__tab').click(function (e) {
        // Remove fw-bold class from all tabs
        $('.oh-tabs__tab').removeClass('fw-bold');

        // Add fw-bold class to the clicked tab
        $(this).addClass('fw-bold');

        // Your existing code for storing the active tab
        var activeTab = $(this).attr('data-target');
        localStorage.setItem('activeTabOnboarding', activeTab);
    });

    // Your existing code for setting the active tab on page load
    var activeTab = localStorage.getItem('activeTabOnboarding');
    if (activeTab != null) {
        var tab = $(`[data-target="${activeTab}"]`);
        $(tab).addClass('fw-bold');
    }
});
