#!/usr/bin/env node
/**
 * Génère un modèle 3D compact de Bayonne (centre + ponton Aviron Bayonnais)
 * à partir d'OpenStreetMap (Overpass) : bâtiments extrudables, ponts, eau.
 * Sortie : web/public/bayonne3d.json (chargé à la demande par la vue 3D).
 *
 * Usage : node web/scripts/gen-bayonne3d.mjs
 */
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "public", "bayonne3d.json");

// bbox fournie (zone centre Bayonne / Nive) : S, O, N, E
const BBOX = [43.484916, -1.477983, 43.493700, -1.471245];
// Centre de projection = milieu de la bbox (caméra centrée sur la zone)
const LAT0 = (BBOX[0] + BBOX[2]) / 2;
const LON0 = (BBOX[1] + BBOX[3]) / 2;

const QUERY = `[out:json][timeout:90];
(
  way["building"](${BBOX.join(",")});
  way["bridge"]["highway"](${BBOX.join(",")});
  way["natural"="water"](${BBOX.join(",")});
  way["waterway"="riverbank"](${BBOX.join(",")});
);
out geom;`;

// projection locale équirectangulaire (mètres autour du centre)
const M_LAT = 110540;
const M_LON = 111320 * Math.cos((LAT0 * Math.PI) / 180);
const px = (lon) => +((lon - LON0) * M_LON).toFixed(1);
const pz = (lat) => +(-(lat - LAT0) * M_LAT).toFixed(1); // nord = -z

function hauteur(tags = {}) {
  if (tags.height) {
    const h = parseFloat(String(tags.height).replace(",", "."));
    if (!isNaN(h)) return h;
  }
  if (tags["building:levels"]) {
    const n = parseFloat(tags["building:levels"]);
    if (!isNaN(n)) return Math.max(3, n * 3);
  }
  return 9; // défaut ~3 niveaux
}

async function overpass() {
  let derniere;
  for (let essai = 1; essai <= 4; essai++) {
    try {
      const r = await fetch("https://overpass-api.de/api/interpreter", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "User-Agent": "vigie-bayonne3d/1.0 (https://vigie.tbrun.dev)",
          Accept: "application/json",
        },
        body: "data=" + encodeURIComponent(QUERY),
      });
      if (!r.ok) throw new Error("Overpass HTTP " + r.status);
      return await r.json();
    } catch (e) {
      derniere = e;
      console.warn(`essai ${essai} échoué (${e.message}), nouvelle tentative…`);
      await new Promise((res) => setTimeout(res, 4000));
    }
  }
  throw derniere;
}

function ring(geom) {
  return geom.map((g) => [px(g.lon), pz(g.lat)]);
}

const data = await overpass();
const buildings = [];
const bridges = [];
const water = [];

for (const el of data.elements) {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 3) continue;
  const t = el.tags || {};
  const p = ring(el.geometry);
  if (t.building) {
    buildings.push({ p, h: +hauteur(t).toFixed(1) });
  } else if (t.bridge) {
    bridges.push({ p, l: t.layer ? +t.layer : 1 });
  } else if (t.natural === "water" || t.waterway === "riverbank") {
    water.push({ p });
  }
}

const out = {
  center: [LAT0, LON0],
  bbox: BBOX,
  buildings,
  bridges,
  water,
};
writeFileSync(OUT, JSON.stringify(out));
const kb = (JSON.stringify(out).length / 1024).toFixed(0);
console.log(`écrit ${OUT}`);
console.log(`bâtiments=${buildings.length} ponts=${bridges.length} eau=${water.length} | ${kb} Ko`);
