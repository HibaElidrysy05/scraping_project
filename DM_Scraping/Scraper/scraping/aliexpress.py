from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
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
    products_data = []
    driver = get_driver()

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(4)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # AliExpress product links all contain /item/ in href
        product_links = soup.find_all("a", href=lambda h: h and "/item/" in h)

        seen = set()
        for a_tag in product_links:
            if len(products_data) >= 10:
                break

            link = a_tag.get("href", "")
            if not link.startswith("http"):
                link = "https:" + link

            # Deduplicate by link
            base_link = link.split("?")[0]
            if base_link in seen:
                continue
            seen.add(base_link)

            # Title — h3 or h1 inside the card
            title_el = a_tag.find(["h3", "h1", "h2"])
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

                         # Price extraction — separate sale, original, discount
            import re
            price = None
            for el in a_tag.find_all(True):
                text = el.get_text(strip=True)
                if text and len(text) < 60 and any(c.isdigit() for c in text):
                    if "MAD" in text or "$" in text or "€" in text:
                        prices = re.findall(r'(?:MAD|€|\$)\s*[\d,]+\.?\d*', text)
                        discount = re.findall(r'-?\d+%', text)
                        if prices:
                            price = prices[0]
                            break

            # Image
            img_el = a_tag.find("img")
            img_link = None
            if img_el:
                img_link = img_el.get("src") or img_el.get("data-src")
                if img_link and img_link.startswith("//"):
                    img_link = "https:" + img_link

            products_data.append({
                "title": title,
                "price": price,
                "img_link": img_link,
                "link": link,
            })

        print(f"AliExpress products found: {len(products_data)}")

    finally:
        driver.quit()

    return products_data