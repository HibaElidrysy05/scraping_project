import re


def nettoyer_texte(texte):

    if not texte:
        return None

    texte = texte.strip()
    texte = re.sub(r"\s+", " ", texte)

    return texte


def normaliser_prix(prix):

    if not prix:
        return None

    prix = nettoyer_texte(prix)

    prix = prix.replace("\u202f", "")
    prix = prix.replace(" ", "")
    prix = prix.replace("DH", "")
    prix = prix.replace("MAD", "")
    prix = prix.replace("Dhs", "")
    prix = prix.replace("€", "")
    prix = prix.replace("$", "")
    prix = prix.replace(",", ".")
    prix = prix.strip()

    nombres = re.findall(r"\d+(?:\.\d+)?", prix)

    if not nombres:
        return None

    try:
        return float(nombres[0])

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