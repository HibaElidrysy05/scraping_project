from django.shortcuts import render
from .scraping.jumia import jumia
from .scraping.avito import avito
from .models import Product

def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query")

        if query:
            jumia_products = jumia(query)
            avito_products = avito(query)

            products = jumia_products + avito_products

            for product in products:
                Product.objects.create(
                    title=product.get("title"),
                    price=product.get("price"),
                    img_link=product.get("img_link"),
                    link=product.get("link"),
                    query=query,
                    source=product.get("source")
                )

    return render(request, "index.html", {
        "products": products,
        "query": query
    })