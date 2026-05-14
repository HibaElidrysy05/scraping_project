from django.shortcuts import render
from .scraping.jumia import jumia
from .scraping.aliexpress import aliexpress
from .models import Product

def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query", "")
        source = request.GET.get("source", "jumia")
        source_label = ""

        if query:
            if source == "aliexpress":
                products = aliexpress(query)
                source_label = "AliExpress"
            else:
                products = jumia(query)
                source_label = "Jumia"

            for product in products:
                Product.objects.create(
                    title=product.get("title"),
                    price=product.get("price"),
                    img_link=product.get("img_link"),
                    link=product.get("link"),
                    search_query=query,
                    source=source_label
                )

    return render(request, "index.html", {
        "products": products,
        "query": query,
        "source": source,
    })
