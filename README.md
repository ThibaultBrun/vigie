# Vigie

Tableau de bord des conditions du moment à un point d'eau (marée, débit, météo, danger).
Usage personnel non-commercial. N'émet aucun verdict de navigabilité : affiche des
conditions brutes, avec un bandeau d'avertissement uniquement en cas de dangerosité.

Architecture multisite : chaque zone est un fichier de config dans `backend/sites/`.
Site par défaut : `bayonne-nive` (Société Nautique de Bayonne, sur la Nive).

## Stack

- Back-end Python (FastAPI) — impose par utide/pytides (maree harmonique) et
  meteofrance-api (vigilance).
- Front HTML/JS pur, sans build, lisible sur mobile.
- Cache + cron de rafraichissement (a venir).

## Lancer en local

```
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Puis ouvrir http://127.0.0.1:8000/ — l'API est sur `/api/conditions?site=bayonne-nive`.

## Sources de donnees

- Marée (niveau observé + phase) : Hub'Eau hydrometrie, station Pont Blanc Q935251001 (H).
- Débit : Hub'Eau hydrometrie, station Cambo-les-Bains Q931251001 (Q).
- Météo : Open-Meteo (point GPS, timezone Europe/Paris).
- Coefficient : port Boucau-Bayonne (SHOM) — a integrer.
- PM/BM du jour : analyse harmonique utide sur serie longue Pont Blanc — a integrer.
- Vigilance : meteofrance-api, departement 64 — a integrer.

## Etat v1

Fait : niveau marée observé + phase, débit + palier, météo courante + évolution horaire,
bandeau danger (débit élevé), schéma JSON cible, archi multisite, robustesse par bloc.

A faire (par ordre) : calibration paliers débit Cambo (médian/QMNA5 reels via HydroPortail),
coefficient SHOM, PM/BM harmonique (utide), vigilance Météo-France, cache persistant + cron.

## Licences / citations

Source : Météo-France · données SHOM · Hub'Eau / Eaufrance · Open-Meteo.
