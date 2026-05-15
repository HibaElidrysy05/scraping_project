import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid

from .nettoyage import (
    nettoyer_texte,
    normaliser_prix,
    corriger_lien,
    corriger_image,
    score_pertinence,
)


BASE_URL = "https://www.avito.ma"


def detect_devise_avito(price_text):
    """
    Exemple:
    '2 500 DH' -> 'MAD'
    """

    if not price_text:
        return None

    price_text = price_text.upper()

    if "DH" in price_text or "MAD" in price_text or "DHS" in price_text:
        return "MAD"

    return None


def detect_etat_avito(titre_complet):
    """
    Détection simple de l'état du produit depuis le titre.
    """

    if not titre_complet:
        return None

    titre_lower = titre_complet.lower()

    if (
        "occasion" in titre_lower
        or "utilisé" in titre_lower
        or "used" in titre_lower
        or "2ème main" in titre_lower
        or "deuxième main" in titre_lower
    ):
        return "occasion"

    if (
        "neuf" in titre_lower
        or "nouveau" in titre_lower
        or "jamais utilisé" in titre_lower
    ):
        return "neuf"

    return None


def avito(query):
    url = f"{BASE_URL}/fr/maroc?q={query.replace(' ', '+')}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)

    html = response.text

    soup = BeautifulSoup(html, "html.parser")

    products = soup.find_all("a", class_="sc-1jge648-0")

    products_data = []

    id_recherche = str(uuid.uuid4())
    date_collecte = datetime.now()

    for product in products[:30]:

        try:
            product_link = product.get("href")
            product_link = corriger_lien(product_link, BASE_URL)
        except:
            product_link = None

        try:
            img_tag = product.find("img", alt=True)
            product_img_link = img_tag.get("src") or img_tag.get("data-src")
            product_img_link = corriger_image(product_img_link, BASE_URL)
        except:
            product_img_link = None

        try:
            titre_complet = product.find("p", class_="iHApav").text.strip()
            titre_complet = nettoyer_texte(titre_complet)
        except:
            titre_complet = None

        try:
            price_text = product.find("span", class_="kohQqr").text.strip()
            price_text = nettoyer_texte(price_text)
        except:
            price_text = None

        prix = normaliser_prix(price_text)

        devise = detect_devise_avito(price_text)

        etat = detect_etat_avito(titre_complet)

        note_vendeur = None

        nombre_avis = None

        type_vendeur = None

        if titre_complet:
            pertinence = score_pertinence(titre_complet, query)

            if pertinence == 0:
                continue

            products_data.append({
                "titre_complet": titre_complet,
                "prix": prix,
                "devise": devise,
                "plateforme": "Avito.ma",
                "note_vendeur": note_vendeur,
                "nombre_avis": nombre_avis,
                "etat": etat,
                "type_vendeur": type_vendeur,
                "img_link": product_img_link,
                "link": product_link,
                "search_query": query,
                "date_collecte": date_collecte,
                "id_recherche": id_recherche,
            })

        if len(products_data) == 10:
            break

    return products_data