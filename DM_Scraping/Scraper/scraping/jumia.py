import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import re


def jumia(query):
    url = f"https://www.jumia.ma/catalog/?q={query.strip().replace(' ', '+')}"
    id_recherche = str(uuid.uuid4())[:8]
    date_collecte = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    products_data = []

    response = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("a", class_="core")
    print(f"Jumia products found raw: {len(products)}")

    for product in products[:10]:
        try:
            link = "https://www.jumia.ma" + product["href"]
        except:
            link = None

        try:
            img_el = product.find("img", class_="img")
            img_link = img_el.get("data-src") or img_el.get("src") if img_el else None
        except:
            img_link = None

        try:
            titre_complet = product.find("h3", class_="name").get_text(strip=True)
        except:
            titre_complet = None

        if not titre_complet:
            continue

        prix = None
        devise = "MAD"
        try:
            price_text = product.find("div", class_="prc").get_text(strip=True)
            nums = re.findall(r"[\d\s]+[,.]?\d*", price_text)
            if nums:
                prix = float(nums[0].replace(" ", "").replace(",", "."))
        except:
            pass

        note_vendeur = None
        try:
            note_el = product.find("div", class_="stars")
            if note_el:
                pct = re.search(r"(\d+)%", note_el.get("style", ""))
                if pct:
                    note_vendeur = str(round(int(pct.group(1)) / 20, 1))
        except:
            pass

        nombre_avis = None
        try:
            avis_el = product.find("span", class_="rev")
            if avis_el:
                nombre_avis = re.sub(r"[^\d]", "", avis_el.get_text(strip=True))
        except:
            pass

        type_vendeur = None
        try:
            vendeur_el = product.find("div", class_="bdg")
            if vendeur_el:
                type_vendeur = vendeur_el.get_text(strip=True)
        except:
            pass

        products_data.append({
            "titre_complet": titre_complet,
            "prix": prix,
            "devise": devise,
            "plateforme": "Jumia.ma",
            "note_vendeur": note_vendeur,
            "nombre_avis": nombre_avis,
            "etat": "Neuf",
            "type_vendeur": type_vendeur,
            "img_link": img_link,
            "link": link,
            "search_query": query,
            "date_collecte": date_collecte,
            "id_recherche": id_recherche,
        })

    print(f"Jumia products returned: {len(products_data)}")
    return products_data