from django.shortcuts import render

from horilla.decorators import login_required


@login_required
def geofaceconfig(request):
    return render(request, "attendance/geofaceconfig/geo_face_config.html")
