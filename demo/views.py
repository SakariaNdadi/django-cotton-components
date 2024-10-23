from django.shortcuts import render
from .models import Car
from django.views.generic import ListView
from django.views.generic.list import MultipleObjectMixin


# Create your views here.
def index(request):
    cars = Car.objects.all()
    context = {"cars": cars, "table_cars": list(cars.values())}
    return render(request, "index.html", context)
