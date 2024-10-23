from django.shortcuts import render
from .models import Car


# Create your views here.
def index(request):
    cars = Car.objects.all()
    context = {"cars": cars}
    return render(request, "index.html", context)
