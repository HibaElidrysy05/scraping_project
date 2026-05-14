import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.avito.ma"

def avito(query):
    url = f"{BASE_URL}/fr/maroc?q={query.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    products = soup.find_all("a", class_="sc-1jge648-0")

    products_data = []
    query_words = query.lower().split()

    for product in products[:30]:
        try:
            product_link = product["href"]
            if product_link.startswith("/"):
                product_link = BASE_URL + product_link
        except:
            product_link = None

        try:
            img = product.find("img", alt=True)
            product_img_link = img.get("src") or img.get("data-src")
        except:
            product_img_link = None

        try:
            product_title = product.find("p", class_="iHApav").text.strip()
        except:
            product_title = None

        try:
            product_price = product.find("span", class_="kohQqr").text.strip()
        except:
            product_price = None

        if product_title:
            title_lower = product_title.lower()

            if not any(word in title_lower for word in query_words):
                continue

        products_data.append({
            "source": "Avito",
            "link": product_link,
            "img_link": product_img_link,
            "title": product_title,
            "price": product_price,
        })

        if len(products_data) == 10:
            break

    return products_data