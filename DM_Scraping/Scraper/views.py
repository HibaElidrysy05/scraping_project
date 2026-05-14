from django.shortcuts import render

from .scraping.jumia import jumia
from .scraping.avito import avito

from .models import Product

from .nettoyage import pretraiter_produit, score_pertinence


def index(request):

    products = []
    query = ""

    if request.method == "GET":

        query = request.GET.get("query")

        if query:

            jumia_products = jumia(query)
            avito_products = avito(query)

            products = jumia_products + avito_products

            products = sorted(
                products,
                key=lambda product: score_pertinence(
                    product.get("title"),
                    query
                ),
                reverse=True
            )

            for product in products:

                produit_nettoye = pretraiter_produit(product)

                if produit_nettoye["title"] and produit_nettoye["link"]:

                    if not Product.objects.filter(
                        link=produit_nettoye["link"]
                    ).exists():

                        Product.objects.create(
                            source=produit_nettoye["source"],
                            query=query,
                            title=produit_nettoye["title"],
                            price=produit_nettoye["price"],
                            price_value=produit_nettoye["price_value"],
                            img_link=produit_nettoye["img_link"],
                            link=produit_nettoye["link"]
                        )

    return render(request, "index.html", {
        "products": products,
        "query": query
    })