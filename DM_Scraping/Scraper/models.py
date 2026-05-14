from django.db import models

class Product(models.Model):
    source = models.CharField(max_length=50)  # Jumia, Avito, Amazon, Electroplanet...
    query = models.CharField(max_length=100, default="unknown")

    title = models.CharField(max_length=255, null=True, blank=True)
    price = models.CharField(max_length=100, null=True, blank=True)
    price_value = models.FloatField(null=True, blank=True)

    img_link = models.URLField(max_length=1000, null=True, blank=True)
    link = models.URLField(max_length=1000, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} - {self.title or 'Sans titre'}"