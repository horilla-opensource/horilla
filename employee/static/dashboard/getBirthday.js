function upcomingBirthdays(response) {
  let container = $("#birthdayContainer");
  let dotsContainer = $("#birthdayDots");
  birthdays = response.birthdays;
  for (let index = 0; index < birthdays.length; index++) {
    activeDotClass = "";
    let element = birthdays[index];
    if (index == 0) {
      activeDotClass = "oh-dashboard__events-nav-item--active";
    }
    dotsContainer.append(`
      <li onclick="moveSlider(event)"  class="oh-dashboard__events-nav-item ${activeDotClass} " data-target="${index}">
      </li>
      `);

    container.append(`
      <div class="oh-dashboard__event">
        <div class="oh-dasboard__event-photo">
          <img
            onload="autoSlider()"
            src="${element.profile}"
            style="
            width: 100%;
            height: 100%;
            object-fit: cover;
          "/>
        </div>
        <div class="oh-dasboard__event-details">
          <span class="oh-dashboard__event-title">Birthday</span>
          <span class="oh-dashboard__event-main">${element.name}</span>
          <span class="oh-dashboard__event-date">${element.dob}, ${element.daysUntilBirthday}</span>
          <span class="oh-dashboard__event-date" style="font-size:10px;">${element.job_position}, ${element.department}</span>
        </div>
      </div>
      `);
  }
}

$(function () {
  $.ajax({
    url: "/employee/get-birthday",
    type: "get",
    success: function (response) {
      // Code to handle the response
      upcomingBirthdays(response);
    },
  });
});

function autoSlider() {
  let slideElements = $(".oh-dashboard__events-nav-item");
  if (slideElements.length > 0) {
    let sliderReel = $(".oh-dashbaord__events-reel");

    // Iterator
    let i = 0;

    // Move slider in an interval of 5 seconds
    setInterval(function () {
      // Increment iterator
      i++;
      // Reset iterator
      if (i == slideElements.length) {
        i = 0;
      }

      sliderReel[0].style.transform = `translateX(-${i * 100}%)`;
      let currSlide = $(`.oh-dashboard__events-nav-item[data-target="${i}"]`);
      // Remove existing active class
      $(".oh-dashboard__events-nav-item--active").removeClass(
        "oh-dashboard__events-nav-item--active"
      );
      // Add active class to new slide
      currSlide.addClass("oh-dashboard__events-nav-item--active");
    }, 5000);
  }

  let sliderEls = $(".oh-dashboard__event");

  if (sliderEls.length > 0) {
    const colors = [
      "#16a085",
      "#2980b9",
      "#e74c3c",
      "#8e44ad",
      "#f39c12",
      "#c0392b",
      "#6F1E51",
      "#5758BB",
    ];

    sliderEls.each(function (index, sliderEl) {
      // Generate a color key based on a random number between the number of colors
      let colorKey = Math.floor(Math.random() * colors.length);

      if (sliderEl) {
        sliderEl.style.backgroundColor = colors[colorKey];
      }
    });
  }
}

function moveSlider(e) {
  let clickedEl = $(e.target).closest(".oh-dashboard__events-nav-item");
  let targetSlideNumber = +clickedEl.data("target");
  let sliderReel = $(".oh-dashbaord__events-reel");

  if (targetSlideNumber >= 0 && sliderReel.length > 0) {
    sliderReel[0].style.transform = `translateX(-${targetSlideNumber * 100}%)`;
    // Remove existing active class
    $(".oh-dashboard__events-nav-item--active").removeClass(
      "oh-dashboard__events-nav-item--active"
    );
    clickedEl.addClass("oh-dashboard__events-nav-item--active");
  }
}
