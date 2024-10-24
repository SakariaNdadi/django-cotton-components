from django.shortcuts import render
from .models import Car


# Create your views here.
def index(request):
    cars = Car.objects.all()
    context = {"cars": cars, "table_cars": list(cars.values())}
    return render(request, "index.html", context)


# class CarListView(ListView):
#     model = Car
#     template_name = "index.html"
#     context_object_name = "charts"
