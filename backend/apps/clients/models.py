from django.db import models

from apps.common.mixins import SoftDeleteModel


class Client(SoftDeleteModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
