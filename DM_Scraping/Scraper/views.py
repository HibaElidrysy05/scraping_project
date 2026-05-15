from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .scraping.jumia import jumia
from .scraping.amazon import amazon
from .scraping.avito import avito
from .scraping.aliexpress import aliexpress
from .scraping.banggood import banggood
from .models import Product


@login_required(login_url="login")
def index(request):
    products = []
    query = ""

    if request.method == "GET":
        query = request.GET.get("query", "")

        if query:
            #amazon_products = amazon(query)
            #jumia_products = jumia(query)
            #avito_products = avito(query)
            #products = amazon_products + jumia_products + avito_products

            aliexpress_products = aliexpress(query)
            banggood_products = banggood(query)
            products = banggood_products + aliexpress_products

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


@login_required(login_url="login")
def historique(request):
    products = []
    query = ""
    sources = ["jumia", "aliexpress", "banggood", "amazon", "avito"]
    history = []

    if request.method == "GET":
        query = request.GET.get("query", "").strip()
        sources = request.GET.getlist("sources")
        if not sources:
            sources = ["jumia", "aliexpress", "banggood", "amazon", "avito"]

        if query:
            platform_map = {
                "jumia": "Jumia.ma",
                "aliexpress": "AliExpress",
                "banggood": "Banggood",
                "amazon": "Amazon",
                "avito": "Avito",
            }
            # Chercher dans les produits de l'utilisateur connecté
            qs = Product.objects.filter(
                user=request.user
            ).filter(
                Q(search_query__icontains=query) | Q(titre_complet__icontains=query)
            )
            if sources and "all" not in sources:
                selected_platforms = [platform_map[s] for s in sources if s in platform_map]
                qs = qs.filter(plateforme__in=selected_platforms)

            for p in qs.order_by("-date_collecte")[:50]:
                products.append({
                    "titre_complet": p.titre_complet,
                    "prix": p.prix,
                    "devise": p.devise or "",
                    "plateforme": p.plateforme,
                    "note_vendeur": p.note_vendeur,
                    "nombre_avis": p.nombre_avis,
                    "etat": p.etat,
                    "type_vendeur": p.type_vendeur,
                    "img_link": p.img_link,
                    "link": p.link,
                    "date_collecte": p.date_collecte,
                    "id_recherche": p.id_recherche,
                })

        # Historique des recherches de l'utilisateur connecté
        seen = {}
        qs_hist = Product.objects.filter(user=request.user).values(
            "search_query", "plateforme", "date_collecte"
        ).order_by("-date_collecte")

        for h in qs_hist:
            key = h["search_query"]
            if not key:
                continue
            if key not in seen:
                seen[key] = {
                    "search_query": key,
                    "plateformes": [],
                    "date_collecte": h["date_collecte"],
                }
            plat = h["plateforme"]
            if plat and plat not in seen[key]["plateformes"]:
                seen[key]["plateformes"].append(plat)

        history = list(seen.values())[:20]

    return render(request, "historique.html", {
        "products": products,
        "query": query,
        "sources": sources,
        "history": history,
    })