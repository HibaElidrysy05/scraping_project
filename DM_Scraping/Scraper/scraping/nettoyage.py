import re


def nettoyer_texte(texte):

    if texte is None:
        return None

    texte = str(texte)
    texte = texte.strip()
    texte = re.sub(r"\s+", " ", texte)

    if texte == "":
        return None

    return texte


def detecter_devise(prix):

    if prix is None:
        return "MAD"

    prix = str(prix).upper()

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

    if prix is None:
        return None

    devise = detecter_devise(prix)

    prix = nettoyer_texte(prix)

    if prix is None:
        return None

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
    prix = prix.replace(",", "")
    prix = prix.strip()

    nombres = re.findall(r"\d+(?:\.\d+)?", prix)

    if not nombres:
        return None

    try:
        valeur = float(nombres[0])
        return convertir_en_mad(valeur, devise)
    except:
        return None


def corriger_lien(lien, base_url=None):

    if lien is None:
        return None

    lien = str(lien).strip()

    if lien == "":
        return None

    if base_url and lien.startswith("/"):
        return base_url + lien

    return lien


def corriger_image(lien_image, base_url=None):

    if lien_image is None:
        return None

    lien_image = str(lien_image).strip()

    if lien_image == "":
        return None

    if base_url and lien_image.startswith("/"):
        return base_url + lien_image

    return lien_image


def pretraiter_produit(produit):

    titre = produit.get("title") or produit.get("titre_complet")
    prix = produit.get("price") or produit.get("prix")
    source = produit.get("source") or produit.get("plateforme")
    query = produit.get("query") or produit.get("search_query")

    return {
        "source": nettoyer_texte(source) or "Inconnu",
        "query": nettoyer_texte(query) or "unknown",
        "title": nettoyer_texte(titre),
        "price": nettoyer_texte(prix),
        "price_value": normaliser_prix(prix),
        "devise": nettoyer_texte(produit.get("devise")),
        "note_vendeur": produit.get("note_vendeur"),
        "nombre_avis": produit.get("nombre_avis"),
        "etat": nettoyer_texte(produit.get("etat")),
        "type_vendeur": nettoyer_texte(produit.get("type_vendeur")),
        "img_link": corriger_image(produit.get("img_link")),
        "link": corriger_lien(produit.get("link")),
        "date_collecte": produit.get("date_collecte"),
        "id_recherche": produit.get("id_recherche"),
    }


def score_pertinence(titre, requete):

    if not titre or not requete:
        return 0

    titre = str(titre).lower()
    requete = str(requete).lower()

    score = 0

    if requete in titre:
        score += 3

    for mot in requete.split():
        if mot in titre:
            score += 1

    return score