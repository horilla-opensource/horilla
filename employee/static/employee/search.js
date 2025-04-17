$(document).ready(function () {
  $("#employee-search").keyup(function (e) {
    $(".employee-view-type").attr("hx-vals", `{"search":"${$(this).val()}"}`);
  });


  $(".employee-view-type").click(function (e) {
    let view = $(this).attr("data-view");
    var currentURL = window.location.href;
    if (view != undefined){
      if (/\?view=[^&]+/.test(currentURL)) {
        newURL = currentURL.replace(/\?view=[^&]+/, "?view="+view);
      }
      else {
        var separator = currentURL.includes('?') ? '&' : '?';
        newURL = currentURL + separator + "view="+view;
      }
      history.pushState({}, "", newURL);
      $("#employee-search").attr("hx-vals", `{"view":"${view}"}`);
      $('#filterForm').attr("hx-vals", `{"view":"${view}"}`);
      $(".oh-btn--view-active").removeClass("oh-btn--view-active")
      $(this).children("a").addClass("oh-btn--view-active")
    }
  });


  // Active tab script
  function activeProfileTab() {
    var activeTab = localStorage.getItem("activeProfileTab")
    if (!$(activeTab).length && $(`[data-target="#personal_target"]`).length) {
      $(`[data-target="#personal_target"]`)[0].click()
    }else if(activeTab != null){
      $(".oh-general__tab-link--active").removeClass("oh-general__tab-link--active");
      $(`[data-target='${activeTab}']`).addClass("oh-general__tab-link--active");
      $(".oh-general__tab-target").addClass("d-none");
      $(activeTab).removeClass("d-none");
      if($(`[data-target="${activeTab}"]`).length>0){
        $(`[data-target="${activeTab}"]`)[0].click();
      }
    }
  }
  activeProfileTab()
  $("[data-action=general-tab]").on("click",function (e) {
    e.preventDefault();
    const targetId = $(this).attr('data-target');
    localStorage.setItem("activeProfileTab",targetId)
  });

});

function employeeFilter(element) {
  var search = $('#employee-search').val();
  const form = document.querySelector('#filterForm');
  const formData = new FormData(form);
  const queryString = new URLSearchParams(formData).toString();
  const searchParams = new URLSearchParams(queryString);
  const queryObject = Object.fromEntries(searchParams.entries());
  queryObject['search'] = search
  stringQueyObject = JSON.stringify(queryObject)
  $('#list').attr('hx-vals', stringQueyObject);
  $('#card').attr('hx-vals', stringQueyObject);
}

// Profile picture enlarging

function enlargeImage(image) {
  var enlargeImageContainer = document.getElementById('enlargeImageContainer');
  enlargeImageContainer.innerHTML = '';

  var enlargedImage = document.createElement('img');
  enlargedImage.src = image.src;
  enlargeImageContainer.appendChild(enlargedImage);

  setTimeout(function() {
    enlargeImageContainer.style.display = 'block';
  }, 250);
}

function hideEnlargeImage() {
  var enlargeImageContainer = document.getElementById('enlargeImageContainer');
  enlargeImageContainer.innerHTML = '';
  enlargeImageContainer.style.display = 'none';

}
