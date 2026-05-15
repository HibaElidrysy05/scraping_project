from django.shortcuts import render
from django.db.models import Q
from concurrent.futures import ThreadPoolExecutor
from .scraping.jumia import jumia
from .scraping.aliexpress import aliexpress
from .scraping.banggood import banggood
from .models import Product


def index(request):
    products = []
    query = ""
    history = []
    sources = ["jumia"]
    mode = "scraping"

    if request.method == "GET":
        query = request.GET.get("query", "").strip()
        sources = request.GET.getlist("sources")
        mode = request.GET.get("mode", "scraping")
        if not sources:
            sources = ["jumia"]

        if query:
            if mode == "database":
                # Chercher dans la base de données
                platform_map = {
                    "jumia": "Jumia.ma",
                    "aliexpress": "AliExpress",
                    "banggood": "Banggood"
                }
                qs = Product.objects.filter(
                    Q(search_query__icontains=query) | Q(title__icontains=query)
                )
                if sources and "all" not in sources:
                    selected_platforms = [platform_map[s] for s in sources if s in platform_map]
                    qs = qs.filter(plateforme__in=selected_platforms)

                for p in qs.order_by("-created_at")[:30]:
                    products.append({
                        "titre_complet": p.title,
                        "prix": p.price,
                        "devise": p.devise or "",
                        "plateforme": p.plateforme or p.source,
                        "note_vendeur": p.note_vendeur,
                        "nombre_avis": p.nombre_avis,
                        "etat": p.etat,
                        "type_vendeur": p.type_vendeur,
                        "img_link": p.img_link,
                        "link": p.link,
                        "date_collecte": p.date_collecte,
                        "id_recherche": p.id_recherche,
                    })
            else:
                # Nouveau scraping
                futures = {}
                with ThreadPoolExecutor(max_workers=3) as executor:
                    if "jumia" in sources:
                        futures["jumia"] = executor.submit(jumia, query)
                    if "aliexpress" in sources:
                        futures["aliexpress"] = executor.submit(aliexpress, query)
                    if "banggood" in sources:
                        futures["banggood"] = executor.submit(banggood, query)
                for future in futures.values():
                    products += future.result()

                for product in products:
                    prix_val = product.get("prix")
                    devise_val = product.get("devise") or ""
                    price_str = f"{prix_val} {devise_val}".strip() if prix_val else ""
                    Product.objects.create(
                        title=product.get("titre_complet"),
                        price=price_str,
                        img_link=product.get("img_link"),
                        link=product.get("link"),
                        search_query=query,
                        source=product.get("plateforme", ""),
                        devise=product.get("devise"),
                        plateforme=product.get("plateforme"),
                        note_vendeur=product.get("note_vendeur"),
                        nombre_avis=product.get("nombre_avis"),
                        etat=product.get("etat"),
                        type_vendeur=product.get("type_vendeur"),
                        date_collecte=product.get("date_collecte"),
                        id_recherche=product.get("id_recherche"),
                    )

        seen = {}
        for h in Product.objects.values("search_query", "plateforme", "created_at").order_by("-created_at"):
            key = h["search_query"]
            if key not in seen:
                seen[key] = {
                    "search_query": key,
                    "plateformes": [],
                    "created_at": h["created_at"],
                }
            plat = h["plateforme"]
            if plat and plat not in seen[key]["plateformes"]:
                seen[key]["plateformes"].append(plat)

        history = list(seen.values())[:10]

    return render(request, "index.html", {
        "products": products,
        "query": query,
        "sources": sources,
        "history": history,
        "mode": mode,
    })
