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
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def aliexpress(query):
    url = f"https://www.aliexpress.com/wholesale?SearchText={query.strip().replace(' ', '+')}"
    id_recherche = str(uuid.uuid4())[:8]
    date_collecte = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    products_data = []
    driver = get_driver()

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)

        # Scroll pour charger les produits
        for y in [600, 1200, 1800]:
            driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(1.5)

        current_url = driver.current_url
        print(f"AliExpress URL: {current_url[:80]}")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_links = soup.find_all("a", href=lambda h: h and "/item/" in h)
        print(f"AliExpress /item/ links: {len(product_links)}")

        seen = set()
        for a_tag in product_links:
            if len(products_data) >= 10:
                break

            link = a_tag.get("href", "")
            if not link.startswith("http"):
                link = "https:" + link

            base_link = link.split("?")[0]
            if base_link in seen:
                continue
            seen.add(base_link)

            title_el = a_tag.find(["h3", "h1", "h2"])
            titre_complet = title_el.get_text(strip=True) if title_el else None
            if not titre_complet:
                texts = [t.strip() for t in a_tag.stripped_strings if len(t.strip()) > 8]
                titre_complet = texts[0] if texts else None
            if not titre_complet:
                continue

            prix = None
            devise = None
            full_text = a_tag.get_text(" ", strip=True)

            #Supprimer les espaces → gérer prix splitté en spans: "MAD 3 , 264 . 32" → "MAD3,264.32"
            compact = re.sub(r'\s+', '', full_text)

            #Chercher les prix : devise AVANT le nombre uniquement (format AliExpress),
            matches = re.findall(r'(?:MAD|US$|$|€)[\d,]+.?\d*', compact)

            # Collecter tous les prix valides → prendre le minimum (prix soldé, pas le barré)
            all_prices = []
            for raw in matches:
                nums = re.findall(r'[\d,]+\.?\d*', raw)
                if nums:
                    try:
                        val = float(nums[0].replace(",", ""))
                        if val > 100:  # ignorer les ratings (0–5)
                            if "MAD" in raw:
                                currency = "MAD"
                            elif "$" in raw:
                                currency = "USD"
                            elif "€" in raw:
                                currency = "EUR"
                            else:
                                currency = "USD"
                            all_prices.append((val, currency))
                    except ValueError:
                        pass

            if all_prices:
                # Le prix le plus bas = prix de vente (pas le prix barré)
                all_prices.sort(key=lambda x: x[0])
                prix, devise = all_prices[0]

            img_el = a_tag.find("img")
            img_link = None
            if img_el:
                img_link = img_el.get("src") or img_el.get("data-src")
                if img_link and img_link.startswith("//"):
                    img_link = "https:" + img_link

            products_data.append({
                "titre_complet": titre_complet,
                "prix": prix,
                "devise": devise or "USD",
                "plateforme": "AliExpress",
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

        print(f"AliExpress products found: {len(products_data)}")

    finally:
        driver.quit()

    return products_data