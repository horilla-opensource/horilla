from django.shortcuts import render


def geofaceconfig(request):
    return render(request, "attendance/geofaceconfig/geo_face_config.html")
