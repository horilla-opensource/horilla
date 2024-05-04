$(document).on('htmx:load',function () {
    function hidBasedOn(basedOn) {
      if (basedOn == "after") {
        $("label[for='id_rotate_after_day']").show();
        $("#id_rotate_after_day").show();

        $("label[for='id_rotate_every_weekend']").hide();
        $("#id_rotate_every_weekend").hide();
        $("label[for='id_rotate_every']").hide();
        $("#id_rotate_every").hide();
      } else if (basedOn == "weekly") {
        $("label[for='id_rotate_every_weekend']").show();
        $("#id_rotate_every_weekend").show();

        $("label[for='id_rotate_after_day']").hide();
        $("#id_rotate_after_day").hide();
        $("label[for='id_rotate_every']").hide();
        $("#id_rotate_every").hide();
      } else if (basedOn == "monthly") {
        $("label[for='id_rotate_every']").show();
        $("#id_rotate_every").show();

        $("label[for='id_rotate_after_day']").hide();
        $("#id_rotate_after_day").hide();
        $("label[for='id_rotate_every_weekend']").hide();
        $("#id_rotate_every_weekend").hide();
      }
    }
    var basedOn = $("#id_based_on");
    hidBasedOn(basedOn.val());


    basedOn.on('change',function (e) {

      hidBasedOn(basedOn.val());
    });
  });
