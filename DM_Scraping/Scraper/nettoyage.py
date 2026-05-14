import re


def nettoyer_texte(texte):

    if not texte:
        return None

    texte = texte.strip()
    texte = re.sub(r"\s+", " ", texte)

    return texte


def detecter_devise(prix):

    if not prix:
        return "MAD"

    prix = prix.upper()

    if "€" in prix or "EUR" in prix:
        return "EUR"

    if "$" in prix or "USD" in prix:
        return "USD"

    if "DH" in prix or "MAD" in prix or "DHS" in prix:
        return "MAD"

    return "MAD"


def convertir_en_mad(valeur, devise):

    if valeur is None:
        return None

    taux = {

        "MAD": 1,

        "EUR": 10.8,

        "USD": 10.0,
    }

    return valeur * taux.get(devise, 1)


def normaliser_prix(prix):

    if not prix:
        return None

    devise = detecter_devise(prix)

    prix = nettoyer_texte(prix)

    prix = prix.replace("\u202f", "")
    prix = prix.replace(" ", "")

    prix = prix.replace("DH", "")
    prix = prix.replace("MAD", "")
    prix = prix.replace("Dhs", "")
    prix = prix.replace("dhs", "")

    prix = prix.replace("€", "")
    prix = prix.replace("EUR", "")

    prix = prix.replace("$", "")
    prix = prix.replace("USD", "")

    prix = prix.replace(",", ".")

    prix = prix.strip()

    nombres = re.findall(r"\d+(?:\.\d+)?", prix)

    if not nombres:
        return None

    try:

        valeur = float(nombres[0])

        return convertir_en_mad(
            valeur,
            devise
        )

    except:

        return None


def corriger_lien(lien, base_url=None):

    if not lien:
        return None

    lien = lien.strip()

    if base_url and lien.startswith("/"):
        return base_url + lien

    return lien


def corriger_image(lien_image, base_url=None):

    if not lien_image:
        return None

    lien_image = lien_image.strip()

    if base_url and lien_image.startswith("/"):
        return base_url + lien_image

    return lien_image


def pretraiter_produit(produit):

    return {

        "source": nettoyer_texte(
            produit.get("source")
        ) or "Inconnu",

        "query": nettoyer_texte(
            produit.get("query")
        ) or "unknown",

        "title": nettoyer_texte(
            produit.get("title")
        ),

        "price": nettoyer_texte(
            produit.get("price")
        ),

        "price_value": normaliser_prix(
            produit.get("price")
        ),

        "img_link": corriger_image(
            produit.get("img_link")
        ),

        "link": corriger_lien(
            produit.get("link")
        ),
    }


def score_pertinence(titre, requete):

    if not titre or not requete:
        return 0

    titre = titre.lower()

    requete = requete.lower()

    score = 0

    if requete in titre:
        score += 3

    for mot in requete.split():

        if mot in titre:
            score += 1

    return score