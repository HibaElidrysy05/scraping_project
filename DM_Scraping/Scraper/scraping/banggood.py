from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import re
import time


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def banggood(query):
    # Forcer l'URL en anglais
    url = f"https://www.banggood.com/search/{query.strip().replace(' ', '-')}.html?language=en"
    id_recherche = str(uuid.uuid4())[:8]
    date_collecte = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    products_data = []
    driver = get_driver()

    try:
        # Forcer la langue anglaise via cookies
        driver.get("https://www.banggood.com")
        time.sleep(2)
        driver.add_cookie({"name": "ckLanguage", "value": "en", "domain": ".banggood.com"})
        driver.add_cookie({"name": "currency", "value": "USD", "domain": ".banggood.com"})

        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(4)

        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 1600);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        print(f"Banggood page size: {len(driver.page_source)}")

        # Trouver tous les liens produit (pattern: -p-XXXXXXX.html)
        all_product_links = soup.find_all("a", href=re.compile(r'-p-\d+\.html'))
        print(f"Banggood product links: {len(all_product_links)}")

        # Grouper par URL: garder seulement le lien avec titre (pas l'image)
        products_by_url = {}
        for a_tag in all_product_links:
            href = a_tag.get("href", "")
            if not href.startswith("http"):
                href = "https://www.banggood.com" + href
            base = href.split("?")[0]

            titre = a_tag.get("title") or a_tag.get_text(strip=True)
            titre = titre.strip() if titre else ""

            # Garder ce lien seulement s'il a un titre valide
            if len(titre) >= 5:
                if base not in products_by_url:
                    products_by_url[base] = {"link": href, "a_tag": a_tag, "titre": titre}

        print(f"Banggood unique products with title: {len(products_by_url)}")

        for base_link, data in list(products_by_url.items())[:10]:
            titre_complet = data["titre"]
            a_tag = data["a_tag"]
            link = data["link"]

            # Prix — remonter dans le DOM
            prix = None
            devise = "USD"
            parent = a_tag.parent
            for _ in range(5):
                if parent is None:
                    break
                price_el = parent.select_one("[class*='price']") or parent.select_one(".price")
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    nums = re.findall(r"[\d,]+\.?\d*", price_text)
                    if nums:
                        try:
                            prix = float(nums[0].replace(",", ""))
                            devise = "EUR" if "€" in price_text else "USD"
                        except ValueError:
                            pass
                    break
                parent = parent.parent

            # Image — remonter dans le DOM
            img_link = None
            card = a_tag.parent
            for _ in range(5):
                if card is None:
                    break
                img_el = card.find("img")
                if img_el:
                    img_link = img_el.get("data-src") or img_el.get("src") or img_el.get("data-original")
                    if img_link and img_link.startswith("//"):
                        img_link = "https:" + img_link
                    break
                card = card.parent

            products_data.append({
                "titre_complet": titre_complet,
                "prix": prix,
                "devise": devise,
                "plateforme": "Banggood",
                "note_vendeur": None,
                "nombre_avis": None,
                "etat": "Neuf",
                "type_vendeur": None,
                "img_link": img_link,
                "link": link,
                "search_query": query,
                "date_collecte": date_collecte,
                "id_recherche": id_recherche,
            })


    finally:
        driver.quit()

    return products_data