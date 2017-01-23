from django.http import HttpResponse

def index(request):
    return HttpResponse("Rango Says hey there Partner! </br> <a href='/rango/about/'>about</a>")

def about(request):
    return HttpResponse("Rango Says this is the about page! </br> <a href='/rango/'>index</a>")

