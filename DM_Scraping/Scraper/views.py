from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from concurrent.futures import ThreadPoolExecutor

from .scraping.jumia import jumia
from .scraping.aliexpress import aliexpress
from .scraping.banggood import banggood
from .scraping.amazon import amazon
from .scraping.avito import avito

from .models import Product


SCRAPERS = {
    "jumia": {
        "name": "Jumia.ma",
        "function": jumia,
    },
    "aliexpress": {
        "name": "AliExpress",
        "function": aliexpress,
    },
    "banggood": {
        "name": "Banggood",
        "function": banggood,
    },
    "amazon": {
        "name": "Amazon.com",
        "function": amazon,
    },
    "avito": {
        "name": "Avito.ma",
        "function": avito,
    },
}


def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, "login.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not username:
            messages.error(request, "Le nom d'utilisateur est obligatoire.")
            return redirect("register")

        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        login(request, user)
        return redirect("index")

    return render(request, "register.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
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

        if "all" in sources:
            sources = list(SCRAPERS.keys())

        if query:
            if mode == "database":
                platform_map = {
                    key: value["name"]
                    for key, value in SCRAPERS.items()
                }

                qs = Product.objects.filter(
                    user=request.user
                ).filter(
                    Q(search_query__icontains=query) |
                    Q(titre_complet__icontains=query)
                )

                if sources:
                    selected_platforms = [
                        platform_map[source]
                        for source in sources
                        if source in platform_map
                    ]

                    qs = qs.filter(plateforme__in=selected_platforms)

                for p in qs.order_by("-created_at")[:30]:
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

            else:
                futures = {}

                with ThreadPoolExecutor(max_workers=5) as executor:
                    for source in sources:
                        if source in SCRAPERS:
                            scraper_function = SCRAPERS[source]["function"]
                            futures[source] = executor.submit(scraper_function, query)

                for source, future in futures.items():
                    try:
                        result = future.result()

                        if result:
                            products += result

                    except Exception as e:
                        print(f"Erreur scraping {source} :", e)

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
                        search_query=query,
                        date_collecte=product.get("date_collecte"),
                        id_recherche=product.get("id_recherche"),
                    )

        seen = {}

        history_qs = Product.objects.filter(user=request.user)

        for h in history_qs.values(
            "search_query",
            "plateforme",
            "created_at"
        ).order_by("-created_at"):

            key = h["search_query"]

            if not key:
                continue

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


@login_required
def historique(request):
    products = []
    query = ""
    history = []
    sources = ["jumia", "aliexpress", "banggood", "amazon", "avito"]
    mode = "database"

    if request.method == "GET":
        query = request.GET.get("query", "").strip()
        sources = request.GET.getlist("sources")
        mode = request.GET.get("mode", "database")

        if not sources:
            sources = ["jumia", "aliexpress", "banggood", "amazon", "avito"]

        if "all" in sources:
            sources = list(SCRAPERS.keys())

        if query:
            platform_map = {
                key: value["name"]
                for key, value in SCRAPERS.items()
            }

            qs = Product.objects.filter(
                user=request.user
            ).filter(
                Q(search_query__icontains=query) |
                Q(titre_complet__icontains=query)
            )

            selected_platforms = [
                platform_map[source]
                for source in sources
                if source in platform_map
            ]

            if selected_platforms:
                qs = qs.filter(plateforme__in=selected_platforms)

            for p in qs.order_by("-created_at")[:30]:
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

        history_qs = Product.objects.filter(user=request.user)

        for h in history_qs.values(
            "search_query",
            "plateforme",
            "created_at"
        ).order_by("-created_at"):

            key = h["search_query"]

            if not key:
                continue

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

    return render(request, "historique.html", {
        "products": products,
        "query": query,
        "sources": sources,
        "history": history,
        "mode": mode,
    })