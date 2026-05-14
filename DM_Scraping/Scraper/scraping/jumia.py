import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import re


def clean_price_jumia(price_text):
    """
    Exemple:
    '4,299.00 Dhs' -> prix = 4299.0, devise = 'MAD'
    """

    if not price_text:
        return None, None

    price_text = price_text.replace("\xa0", " ").strip()

    devise = None

    if "Dhs" in price_text or "DH" in price_text or "MAD" in price_text:
        devise = "MAD"

    price_number = re.sub(r"[^0-9.]", "", price_text)

    try:
        prix = float(price_number)
    except:
        prix = None

    return prix, devise


def detect_etat_jumia(titre_complet):
    """
    Détection simple de l'état du produit depuis le titre.
    """

    if not titre_complet:
        return None

    titre_lower = titre_complet.lower()

    if "remis à neuf" in titre_lower or "reconditionné" in titre_lower or "occasion" in titre_lower:
        return "occasion"

    return "neuf"


def jumia(query):
    url = f"https://www.jumia.ma/catalog/?q={query.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    html = response.text

    soup = BeautifulSoup(html, "html.parser")

    products = soup.find_all("article", class_="prd")

    products_data = []

    id_recherche = str(uuid.uuid4())
    date_collecte = datetime.now()

    for product in products[:10]:

        try:
            link_tag = product.find("a", class_="core")
            product_link = link_tag["href"]

            if product_link.startswith("/"):
                product_link = "https://www.jumia.ma" + product_link
        except:
            product_link = None

        try:
            img_tag = product.find("img", class_="img")

            product_img_link = img_tag.get("data-src") or img_tag.get("src")
        except:
            product_img_link = None

        try:
            titre_complet = product.find("h3", class_="name").text.strip()
        except:
            titre_complet = None

        try:
            price_text = product.find("div", class_="prc").text.strip()
        except:
            price_text = None

        prix, devise = clean_price_jumia(price_text)

        note_vendeur = None
        nombre_avis = None

        etat = detect_etat_jumia(titre_complet)

        type_vendeur = None

        if titre_complet:
            products_data.append({
                "titre_complet": titre_complet,
                "prix": prix,
                "devise": devise,
                "plateforme": "Jumia.ma",
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

    return products_data


# Test
if __name__ == "__main__":
    data = jumia("iphone 13")

    for product in data:
        print(product)
        print("-" * 80)