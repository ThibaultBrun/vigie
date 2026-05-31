# Vigie

Tableau de bord des conditions du moment à un point d'eau (marée, débit, météo, danger).
Usage personnel non-commercial. N'émet aucun verdict de navigabilité : affiche des
conditions brutes, avec un bandeau d'avertissement uniquement en cas de dangerosité.

Architecture multisite : chaque zone est un fichier de config dans `collector/sites/`.
Site par défaut : `bayonne-nive` (Société Nautique de Bayonne, sur la Nive).

## Architecture

Decouplee, sans serveur applicatif :

- `collector/` — collecteur Python. Aspire les API, calcule (harmonique de maree,
  vigilance) et ecrit le JSON cible dans `web/public/data/<site>.json`. Lance en cron.
- `web/` — site Vite + Vue. Lit le JSON et l'affiche. Build statique, lisible sur mobile.
- `.github/workflows/deploy.yml` — GitHub Actions : cron toutes les 15 min qui relance le
  collecteur, rebuild le site et le deploie sur GitHub Pages. Aucune cle API, repo public.

Python est impose par utide/pytides (maree harmonique) et meteofrance-api (vigilance).

## Lancer en local

Collecteur (genere le JSON dans web/public/data) :

```
cd collector
python -m pip install -r requirements.txt
python collect.py
```

Site :

```
cd web
npm install
npm run dev
```

## Deploiement (GitHub Pages)

1. Pousser le repo (public) sur GitHub.
2. Settings > Pages > Source : GitHub Actions.
3. Le workflow build + deploie a chaque push et toutes les 15 min (cron).

Le timing du cron GitHub Actions est approximatif (peut decaler de plusieurs minutes).

## Sources de donnees

- Marée (niveau observé + phase) : Hub'Eau hydrometrie, station Pont Blanc Q935251001 (H).
- Débit : Hub'Eau hydrometrie, station Cambo-les-Bains Q931251001 (Q).
- Météo : Open-Meteo (point GPS, timezone Europe/Paris).
- Coefficient : port Boucau-Bayonne (SHOM) — a integrer.
- PM/BM du jour : analyse harmonique utide sur serie longue Pont Blanc — a integrer.
- Vigilance : meteofrance-api, departement 64 — a integrer.

## Etat

Fait : pivot archi collecteur + Vite/Vue + GitHub Actions/Pages, niveau marée observé +
phase, débit + palier, météo courante + évolution horaire, bandeau danger (débit élevé),
schéma JSON cible, archi multisite, robustesse par bloc.

A faire (par ordre) : calibration paliers débit Cambo (médian/QMNA5 reels via HydroPortail),
coefficient SHOM, PM/BM harmonique (utide), vigilance Météo-France.

## Licences / citations

Source : Météo-France · données SHOM · Hub'Eau / Eaufrance · Open-Meteo.
