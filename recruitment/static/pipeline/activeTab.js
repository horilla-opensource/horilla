$(document).ready(function () {
    var activeTab = localStorage.getItem('activeTabRecruitment')
    if (activeTab != null) {
      var tab  = $(`[data-target="${activeTab}"]`)  
      var tabContent = $(activeTab)
      $(tab).attr('class', 'oh-tabs__tab oh-tabs__tab--active');   
      $(tabContent).attr('class', 'oh-tabs__content oh-tabs__content--active'); 
    }
    else{
      $('[data-target="#tab_1"]').attr('class', 'oh-tabs__tab oh-tabs__tab--active');   
      $('#tab_rec_1').attr('class', 'oh-tabs__content oh-tabs__content--active'); 
    }
    $('.oh-tabs__tab').click(function (e) { 
      var activeTab = $(this).attr('data-target');
      localStorage.setItem('activeTabRecruitment',activeTab)
    });
  });