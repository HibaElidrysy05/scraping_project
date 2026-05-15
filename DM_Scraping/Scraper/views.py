from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .scraping.jumia import jumia
from .scraping.amazon import amazon
from .scraping.avito import avito

from .models import Product
from .scraping.nettoyage import (
    pretraiter_produit,
    score_pertinence
)


@login_required(login_url="login")
def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query", "")

        if query:
            amazon_products = amazon(query) or []
            jumia_products = jumia(query) or []
            avito_products = avito(query) or []

            products = amazon_products + jumia_products + avito_products

            for product in products:
                Product.objects.create(
                    user=request.user,
                    titre_complet=product.get("titre_complet"),
                    prix=product.get("prix"),
                    devise=product.get("devise"),
                    plateforme=product.get("plateforme"),
                    note_vendeur=product.get("note_vendeur"),
                    nombre_avis=product.get("nombre_avis"),
                    etat=product.get("etat"),
                    type_vendeur=product.get("type_vendeur"),
                    img_link=product.get("img_link"),
                    link=product.get("link"),
                    search_query=product.get("search_query"),
                    date_collecte=product.get("date_collecte"),
                    id_recherche=product.get("id_recherche"),
                )

    return render(request, "index.html", {
        "products": products,
        "query": query
    })


@api_view(["GET"])
def search_api(request):
    query = request.GET.get("query", "")
    platforms = request.GET.get("platforms", "all")

    if not query:
        return Response([])

    selected = platforms.split(",")

    products = []

    if "all" in selected or "amazon" in selected:
        products += amazon(query) or []

    if "all" in selected or "jumia" in selected:
        products += jumia(query) or []

    if "all" in selected or "avito" in selected:
        products += avito(query) or []

    cleaned_products = []

    for product in products:
        produit_nettoye = pretraiter_produit(product)

        if produit_nettoye["title"] and produit_nettoye["link"]:
            cleaned_products.append(produit_nettoye)

    return Response(cleaned_products)