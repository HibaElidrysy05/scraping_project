from django.shortcuts import render
from .scraping.jumia import jumia
from .scraping.amazon import amazon
from .models import Product


def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query", "")

        if query:
            amazon_products = amazon(query)
            jumia_products = jumia(query)

            products = amazon_products + jumia_products

            for product in products:
                Product.objects.create(
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