"""
Logique "cerveau" de l'assistant.

Responsabilité :
- décider de proposer ou non (abstention)
- définir une incertitude (low/mid/high)
- produire une explication courte (≤3 facteurs)

Ici : placeholder.
"""

from assistant.suggestions import CAT_EARS


def propose_suggestion(context: dict):
    """
    Retourne un dict suggestion ou None (abstention).
    context peut contenir:
      - has_ellipse: bool
      - trigger: "manual" | "auto"
    """

    if not context.get("has_ellipse", False):
        # Abstention
        return None

    # Prototype : incertitude fixe
    return {
        "suggestion": CAT_EARS,
        "uncertainty_pct": 70,  # affichage simple
        "explanation": [
            "Une ellipse est détectée (tête possible).",
            "Ajout d'éléments symétriques au-dessus.",
            "Suggestion optionnelle (à ajuster).",
        ],
        "what_to_do": "Appliquez si vous dessinez un chat, sinon ignorez.",
    }
