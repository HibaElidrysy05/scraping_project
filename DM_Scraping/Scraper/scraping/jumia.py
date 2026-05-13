import requests
from bs4 import BeautifulSoup

def jumia(query):

    url = f"https://www.jumia.ma/catalog/?q={query.replace(' ','+')}"

    response = requests.get(url)

    html = response.text

    soup = BeautifulSoup(html, "html.parser")


    products = soup.find_all("a", class_="core")

    #print(products[0])
    #print(products[1])
    #print(products[2])

    print(type(products))

    products_data = []

    for product in products[:10]:
        #print(type(product))
        try:
            product_link = product["href"]
            product_link = "https://www.jumia.ma" + product_link
        except:
            product_link = None

        try:
            product_img_link = product.find("img", class_="img")["data-src"]
        except:
            product_img_link = None

        try:
            product_title = product.find("h3", class_="name").text
        except:
            product_title = None
        
        try:
            product_price = product.find("div", class_="prc").text
            #print(product_price)
        except:
            product_price = None

        products_data.append({
            "link" : product_link,
            "img_link" : product_img_link,
            "title" : product_title,
            "price" : product_price, #str in this moment
        })
    return products_data