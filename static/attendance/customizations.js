var activityButton = $("#attendance-activity-container").find("button");
outUrl = "/attendance/clock-out";
bttnUrl = activityButton.attr("hx-get");
if (outUrl == bttnUrl) {
    
}

console.log(outUrl);
console.log(bttnUrl);
console.log(activityButton);

