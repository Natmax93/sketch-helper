# Sketch Helper – Prototype HAII

Projet Master 2 - AI2D 2025-2026 Humain AI Interaction

Sketch Helper est un prototype d’application de dessin interactif développé dans le cadre du cours
Interaction Humain–IA (HAII). Il explore l’impact d’une assistance intelligente contrôlée sur la performance de création graphique.

## Prérequis

- Python >= 3.10
- PySide6 = 6.9.3
- Système testé : Linux / macOS

## Installation

1. Cloner le dépôt :
    ```bash
    git clone https://github.com/Natmax93/sketch-helper.git
    cd sketch-helper
    ```

## Lancement

Depuis la racine du projet :

```bash
python3 main.py
```

## Utilisation – Mode normal

L’application propose :

### Outils de dessin

- Stylo (dessin libre)
- Gomme
- Ligne, rectangle, ellipse, triangle
- Sélection, déplacement, duplication
- Annuler / Rétablir

### Couleurs

- Palette rapide (noir, rouge, bleu, vert, gris)
- Couleur personnalisée via “…”

### Assistant IA (optionnel)

- Génération IA : panneau latéral d’éléments préfaits
- Assistant flottant : suggestion manuelle
- Auto-suggestions : propositions automatiques contextuelles

## Mode Test (expérience)

Le mode Test permet d’évaluer l’impact de l’assistance IA.

Déroulement :

1. Cliquer sur “Test”
2. Choisir une condition :
    - Sans IA (H_ONLY)
    - Avec IA (H_PLUS_IA)
3. Reproduire 3 dessins modèles (chat, château, voiture)
4. Cliquer sur “Done” uniquement lorsque le dessin est jugé satisfaisant
5. Évaluer la ressemblance

## Organisation du projet

- main.py : point d’entrée
- ui/ : interfaces graphiques (menu, éditeur, panneaux)
- drawing/ : logique de dessin (scene, outils, undo/redo)
- assistant/ : logique de suggestions et génération IA
- logs/ : journalisation des interactions
- assets/ : images et ressources
