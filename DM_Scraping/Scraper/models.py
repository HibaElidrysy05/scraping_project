from django.db import models

class Product(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    price = models.CharField(max_length=100, null=True, blank=True)
    img_link = models.URLField(null=True, blank=True)
    link = models.URLField(null=True, blank=True,max_length=1000)
    search_query = models.CharField(max_length=100)
    source = models.CharField(max_length=50, default="Jumia")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or "Produit sans titre"