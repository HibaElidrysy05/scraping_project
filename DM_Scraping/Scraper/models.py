from django.db import models

class Product(models.Model):
    title = models.CharField(max_length=500, null=True, blank=True)
    price = models.CharField(max_length=100, null=True, blank=True)
    img_link = models.URLField(max_length=1000, null=True, blank=True)
    link = models.URLField(max_length=1000, null=True, blank=True)
    search_query = models.CharField(max_length=200)
    source = models.CharField(max_length=50, default="Jumia")
    created_at = models.DateTimeField(auto_now_add=True)
    devise = models.CharField(max_length=10, null=True, blank=True)
    plateforme = models.CharField(max_length=50, null=True, blank=True)
    note_vendeur = models.CharField(max_length=20, null=True, blank=True)
    nombre_avis = models.CharField(max_length=20, null=True, blank=True)
    etat = models.CharField(max_length=50, null=True, blank=True)
    type_vendeur = models.CharField(max_length=200, null=True, blank=True)
    date_collecte = models.CharField(max_length=30, null=True, blank=True)
    id_recherche = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.title or "Produit sans titre"