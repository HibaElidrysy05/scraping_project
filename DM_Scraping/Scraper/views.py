from django.shortcuts import render
from .scraping.jumia import jumia
from .models import Product

def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query")

        if query:
            products = jumia(query)

            for product in products:
                Product.objects.create(
                    title=product.get("title"),
                    price=product.get("price"),
                    img_link=product.get("img_link"),
                    link=product.get("link"),
                    search_query=query,
                    source="Jumia"
                )

    return render(request, "index.html", {
        "products": products,
        "query": query
    })
    