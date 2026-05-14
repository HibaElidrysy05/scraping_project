from django.db import models


class Product(models.Model):
    titre_complet = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    prix = models.FloatField(
        null=True,
        blank=True
    )

    devise = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    plateforme = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    note_vendeur = models.FloatField(
        null=True,
        blank=True
    )

    nombre_avis = models.IntegerField(
        null=True,
        blank=True
    )

    etat = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    type_vendeur = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    img_link = models.URLField(
        max_length=1000,
        null=True,
        blank=True
    )

    link = models.URLField(
        max_length=1000,
        null=True,
        blank=True
    )

    search_query = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    date_collecte = models.DateTimeField(
        null=True,
        blank=True
    )

    id_recherche = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "Product"

    def __str__(self):
        return self.titre_complet or "Produit sans titre"