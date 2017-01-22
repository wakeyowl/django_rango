from django.http import HttpResponse

def index(request):
    return HttpResponse("Rango Says hey there Partner!")

