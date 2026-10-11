# app/payload/governed_release.py
"""Largage civil uniquement (colis médical, balise, capteur).
 - vérrouillé sur zones/fenêtres autorisées (géorepérage)
 - double approbation humaine
 - interdit hors des catégories civiles déclarées"""
ALLOWED_CATEGORIES = {"medical_drop", "beacon", "sensor_pod"}

def authorize_release(category, geo_ok: bool, dual_token_ok: bool) -> bool:
    return category in ALLOWED_CATEGORIES and geo_ok and dual_token_ok