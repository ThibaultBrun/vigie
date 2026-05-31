const SITE = new URLSearchParams(location.search).get("site") || "bayonne-nive";

function fmtHeure(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function fmtHeureCourte(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function ligne(k, v) {
  return `<div class="ligne"><span class="k">${k}</span><span class="v">${v}</span></div>`;
}

function rendreMaree(m) {
  const el = document.getElementById("maree");
  if (!m.disponible) { el.innerHTML = `<p class="stale">Donnée indisponible</p>`; return; }
  let h = "";
  h += ligne("Phase", m.phase);
  h += ligne("Niveau observé", `${m.niveau_observe_m} m`);
  if (m.coefficient != null) h += ligne("Coefficient", `${m.coefficient} (${m.source_coef})`);
  else h += ligne("Coefficient", `<span class="stale">à venir</span>`);
  if (m.pm_bm && m.pm_bm.length) {
    m.pm_bm.forEach(p => h += ligne(p.type, `${fmtHeureCourte(p.heure_locale)} (${p.hauteur_m} m)`));
  } else {
    h += ligne("PM / BM du jour", `<span class="stale">à venir (harmonique)</span>`);
  }
  h += `<div class="horo">${m.source_niveau} · ${fmtHeure(m.horodatage_niveau)}</div>`;
  el.innerHTML = h;
}

function rendreDebit(d) {
  const el = document.getElementById("debit");
  if (!d.disponible) { el.innerHTML = `<p class="stale">Donnée indisponible</p>`; return; }
  let h = "";
  h += ligne("Débit", `${d.valeur_m3s} m³/s`);
  h += ligne("Palier", `<span class="badge ${d.palier}">${d.palier}</span>`);
  h += `<div class="horo">${d.source} · ${fmtHeure(d.horodatage)}</div>`;
  el.innerHTML = h;
}

function rendreMeteo(m) {
  const el = document.getElementById("meteo");
  if (!m.disponible) { el.innerHTML = `<p class="stale">Donnée indisponible</p>`; return; }
  let h = "";
  h += ligne("Vent", `${m.vent_dir} ${m.vent_kmh} km/h`);
  h += ligne("Rafales", `${m.rafales_kmh} km/h`);
  h += ligne("Température", `${m.temp_c} °C`);
  h += ligne("Nuages", `${m.cloud_cover_pct} %`);
  h += ligne("Coucher du soleil", fmtHeureCourte(m.coucher_soleil_local));
  h += `<div class="horo">Open-Meteo · ${fmtHeure(m.horodatage)}</div>`;
  el.innerHTML = h;
}

function rendreDanger(danger) {
  const el = document.getElementById("danger");
  if (danger && danger.actif && danger.messages.length) {
    el.innerHTML = "⚠️ " + danger.messages.join(" · ");
    el.classList.remove("hidden");
  } else {
    el.classList.add("hidden");
  }
}

async function charger() {
  try {
    const r = await fetch(`/api/conditions?site=${encodeURIComponent(SITE)}`);
    const data = await r.json();
    document.getElementById("titre").textContent = data.point.nom;
    document.getElementById("horodatage").textContent = "Mis à jour : " + fmtHeure(data.horodatage);
    rendreDanger(data.danger);
    rendreMaree(data.maree);
    rendreDebit(data.debit);
    rendreMeteo(data.meteo);
    const notes = document.getElementById("notes");
    notes.innerHTML = (data.notes && data.notes.length) ? data.notes.map(n => "• " + n).join("<br>") : "";
  } catch (e) {
    document.getElementById("contenu").innerHTML = `<p class="stale">Erreur de chargement : ${e}</p>`;
  }
}

charger();
setInterval(charger, 5 * 60 * 1000);
