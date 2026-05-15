from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .scraping.jumia import jumia
from .scraping.amazon import amazon
from .scraping.avito import avito
from .scraping.aliexpress import aliexpress
from .scraping.banggood import banggood

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

            aliexpress_products = aliexpress(query) or []

            banggood_products = banggood(query) or []

            products = (
                amazon_products
                + jumia_products
                + avito_products
                + aliexpress_products
                + banggood_products
            )

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

    return render(
        request,
        "index.html",
        {
            "products": products,
            "query": query
        }
    )


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

    if "all" in selected or "aliexpress" in selected:
        products += aliexpress(query) or []

    if "all" in selected or "banggood" in selected:
        products += banggood(query) or []

    products = sorted(
        products,
        key=lambda product: score_pertinence(
            product.get("title")
            or product.get("titre_complet"),
            query
        ),
        reverse=True
    )

    cleaned_products = []

    for product in products:

        produit_nettoye = pretraiter_produit(product)

        if (
            produit_nettoye["title"]
            and produit_nettoye["link"]
        ):

            cleaned_products.append(
                produit_nettoye
            )

    return Response(cleaned_products)


@login_required(login_url="login")
def historique(request):

    products = []

    query = ""

    sources = [
        "jumia",
        "aliexpress",
        "banggood",
        "amazon",
        "avito"
    ]

    history = []

    if request.method == "GET":

        query = request.GET.get(
            "query",
            ""
        ).strip()

        sources = request.GET.getlist("sources")

        if not sources:

            sources = [
                "jumia",
                "aliexpress",
                "banggood",
                "amazon",
                "avito"
            ]

        if query:

            platform_map = {
                "jumia": "Jumia.ma",
                "aliexpress": "AliExpress",
                "banggood": "Banggood",
                "amazon": "Amazon",
                "avito": "Avito",
            }

            qs = Product.objects.filter(
                user=request.user
            ).filter(
                Q(search_query__icontains=query)
                |
                Q(titre_complet__icontains=query)
            )

            if sources and "all" not in sources:

                selected_platforms = [
                    platform_map[s]
                    for s in sources
                    if s in platform_map
                ]

                qs = qs.filter(
                    plateforme__in=selected_platforms
                )

            for p in qs.order_by(
                "-date_collecte"
            )[:50]:

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

        seen = {}

        qs_hist = Product.objects.filter(
            user=request.user
        ).values(
            "search_query",
            "plateforme",
            "date_collecte"
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

            if (
                plat
                and plat not in seen[key]["plateformes"]
            ):

                seen[key]["plateformes"].append(
                    plat
                )

        history = list(seen.values())[:20]

    return render(
        request,
        "historique.html",
        {
            "products": products,
            "query": query,
            "sources": sources,
            "history": history,
        }
    )