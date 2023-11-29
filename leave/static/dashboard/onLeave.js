$(document).ready(function () {
  $.ajax({
    type: "GET",
    url: "/leave/employee-leave",
    dataType: "json",
    success: function (response) {
      $.each(response.employees, function (index, value) {
        $("#leaveEmployee").append(
          `<li class="oh-card-dashboard__user-item">
                    <div class="oh-profile oh-profile--md">
                      <div class="oh-profile__avatar mr-1">
                        <img src="https://ui-avatars.com/api/?name=${value}&background=random" class="oh-profile__image"
                          alt="Beth Gibbons" />
                      </div>
                      <span class="oh-profile__name oh-text--dark">${value}</span>
                    </div>
                  </li>
                  `
        );
      });
    },
  });
});
