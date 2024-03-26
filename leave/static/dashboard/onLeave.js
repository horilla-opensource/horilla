// $(document).ready(function () {
//   $.ajax({
//     type: "GET",
//     url: "/leave/employee-leave",
//     dataType: "json",
//     success: function (response) {
//       if (response.employees.length) {
//         $.each(response.employees, function (index, value) {
//           $("#leaveEmployee").append(
//             `<li class="oh-card-dashboard__user-item">
//                 <div class="oh-profile oh-profile--md">
//                   <div class="oh-profile__avatar mr-1">
//                     <img src="https://ui-avatars.com/api/?name=${value}&background=random" class="oh-profile__image"
//                       alt="Beth Gibbons" />
//                   </div>
//                   <span class="oh-profile__name oh-text--dark">${value}</span>
//                 </div>
//               </li>`
//           );
//         });
//     }
//     else{
//       $("#leaveEmployee").append(
//         `<div class="">
// 						<div class="oh-404" style="position:revert; transform:none">
// 							<img style="width: 80px;height: 80px; margin-bottom:20px" src="{% static 'images/ui/no-announcement.svg' %}" class="oh-404__image" alt="Page not found. 404."/>
// 							<h5 class="oh-404__subtitle">No Announcements to show.</h5>
// 						</div>
//         </div>`
//       )
//     }
//     },
//   });
// });
