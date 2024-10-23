from django.db import models


# Create your models here.
class Car(models.Model):
    id = models.AutoField(primary_key=True)
    manufacturer = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    TRANSMISSION_CHOICES = [
        ("Automatic", "Automatic"),
        ("Manual", "Manual"),
    ]
    transmission = models.CharField(max_length=10, choices=TRANSMISSION_CHOICES)
    color = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.year})"
