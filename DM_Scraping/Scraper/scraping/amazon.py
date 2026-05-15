from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
import time
import uuid
import re


def clean_price(price_text):
    """
    Exemple:
    'MAD 2,447.22' -> prix = 2447.22, devise = 'MAD'
    """

    if not price_text:
        return None, None

    price_text = price_text.replace("\xa0", " ").strip()

    devise = None

    if "MAD" in price_text:
        devise = "MAD"
    elif "$" in price_text:
        devise = "USD"
    elif "€" in price_text:
        devise = "EUR"

    price_number = re.sub(r"[^0-9.]", "", price_text)

    try:
        prix = float(price_number)
    except:
        prix = None

    return prix, devise


def clean_reviews(reviews_text):
    """
    Exemple:
    '26,150 ratings' -> 26150
    """

    if not reviews_text:
        return None

    reviews_number = re.sub(r"[^0-9]", "", reviews_text)

    try:
        return int(reviews_number)
    except:
        return None


def detect_etat(titre_complet):
    if not titre_complet:
        return None

    titre_lower = titre_complet.lower()

    if (
        "renewed" in titre_lower
        or "used" in titre_lower
        or "refurbished" in titre_lower
    ):
        return "occasion"

    return "neuf"


def amazon(query):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    products_data = []

    id_recherche = str(uuid.uuid4())
    date_collecte = datetime.now()

    try:
        url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        driver.get(url)

        time.sleep(5)

        products = driver.find_elements(
            By.CSS_SELECTOR,
            "div.s-result-item[data-component-type='s-search-result']"
        )

        for product in products[:10]:

            try:
                titre_complet = product.find_element(
                    By.CSS_SELECTOR,
                    "h2 span"
                ).text
            except:
                titre_complet = None

            try:
                product_link = product.find_element(
                    By.CSS_SELECTOR,
                    "div[data-cy='title-recipe'] a"
                ).get_attribute("href")
            except:
                product_link = None

            try:
                img_link = product.find_element(
                    By.CSS_SELECTOR,
                    "img.s-image"
                ).get_attribute("src")
            except:
                img_link = None

            try:
                price_text = product.find_element(
                    By.CSS_SELECTOR,
                    "span.a-price span.a-offscreen"
                ).get_attribute("textContent")
            except:
                price_text = None

            prix, devise = clean_price(price_text)

            try:
                note_text = product.find_element(
                    By.CSS_SELECTOR,
                    ".a-icon-alt"
                ).get_attribute("textContent")

                note_vendeur = float(note_text.split()[0])
            except:
                note_vendeur = None

            try:
                reviews_text = product.find_element(
                    By.CSS_SELECTOR,
                    "a[aria-label*='ratings']"
                ).get_attribute("aria-label")

                nombre_avis = clean_reviews(reviews_text)
            except:
                nombre_avis = None

            etat = detect_etat(titre_complet)

            type_vendeur = None

            if titre_complet:
                products_data.append({
                    "titre_complet": titre_complet,
                    "prix": prix,
                    "devise": devise,
                    "plateforme": "Amazon.com",
                    "note_vendeur": note_vendeur,
                    "nombre_avis": nombre_avis,
                    "etat": etat,
                    "type_vendeur": type_vendeur,
                    "img_link": img_link,
                    "link": product_link,
                    "search_query": query,
                    "date_collecte": date_collecte,
                    "id_recherche": id_recherche,
                })

    finally:
        driver.quit()

    return products_data