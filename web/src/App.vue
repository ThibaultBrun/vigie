<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const SITE = new URLSearchParams(location.search).get('site') || 'bayonne-nive'
const data = ref(null)
const erreur = ref(null)
let timer = null

function fmt(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d)) return iso
  return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function fmtH(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d)) return iso
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

async function charger() {
  try {
    const r = await fetch(`data/${SITE}.json`, { cache: 'no-store' })
    if (!r.ok) throw new Error('HTTP ' + r.status)
    data.value = await r.json()
    erreur.value = null
  } catch (e) {
    erreur.value = String(e)
  }
}

onMounted(() => {
  charger()
  timer = setInterval(charger, 2 * 60 * 1000)
})

onUnmounted(() => clearInterval(timer))

const point = computed(() => data.value?.point)
const danger = computed(() => data.value?.danger)
const maree = computed(() => data.value?.maree)
const debit = computed(() => data.value?.debit)
const meteo = computed(() => data.value?.meteo)
const notes = computed(() => data.value?.notes || [])
const webcam = computed(() => data.value?.webcam)

const jauge = computed(() => {
  const d = debit.value
  if (!d?.disponible || !d.echelle || d.echelle.min_m3s == null) return null
  const e = d.echelle
  const tf = (x) => {
    const r = Math.max(0, Math.min(1, (x - e.min_m3s) / (e.max_m3s - e.min_m3s)))
    return Math.sqrt(r) * 100
  }
  const t = tf(e.seuil_tranquille_m3s)
  const f = tf(e.seuil_fort_m3s)
  const gradient = `linear-gradient(90deg, #2e8b57 0%, #59b06f ${(t * 0.6).toFixed(1)}%, #e8c84a ${t.toFixed(1)}%, #d98a3a ${((t + f) / 2).toFixed(1)}%, #c0392b ${f.toFixed(1)}%, #8a2020 100%)`
  return {
    gradient,
    curseur: tf(d.valeur_m3s),
    hors: d.valeur_m3s > e.max_m3s,
    min: e.min_m3s,
    max: e.max_m3s,
  }
})

const NAV_LABEL = { tranquille: 'Tranquille', moyen: 'Ça pousse', fort: 'Fort courant' }

const HORIZON_MIN = 48 * 60

const minutesFutur = ref(0)
const cibleMs = computed(() => Date.now() + minutesFutur.value * 60000)

function prefixeJour(d) {
  const j0 = new Date(); j0.setHours(0, 0, 0, 0)
  const jd = new Date(d); jd.setHours(0, 0, 0, 0)
  const n = Math.round((jd - j0) / 86400000)
  if (n === 0) return ''
  if (n === 1) return 'demain '
  if (n === 2) return 'après-demain '
  return new Date(d).toLocaleDateString('fr-FR', { weekday: 'short' }) + ' '
}

const cibleLabel = computed(() => {
  const d = new Date(cibleMs.value)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const p = prefixeJour(d) || 'aujourd’hui '
  return `${p}${hh}:${mm}`
})

function plusProche(liste) {
  if (!liste || !liste.length) return null
  let best = liste[0]
  let bd = Infinity
  for (const p of liste) {
    const dd = Math.abs(new Date(p.heure_locale).getTime() - cibleMs.value)
    if (dd < bd) { bd = dd; best = p }
  }
  return best
}

const mareeSel = computed(() => plusProche(maree.value?.courbe))
const ventSel = computed(() => plusProche(meteo.value?.evolution_horaire))

const prochainesMarees = computed(() => {
  const now = Date.now() - 1800000
  return (maree.value?.pm_bm || [])
    .filter((p) => new Date(p.heure_locale).getTime() >= now)
    .slice(0, 5)
})
</script>

<template>
  <div v-if="erreur" class="stale">Erreur de chargement : {{ erreur }}</div>

  <template v-if="data">
    <header>
      <h1>{{ point.nom }}</h1>
      <p class="sub">Mis à jour : {{ fmt(data.horodatage) }}</p>
    </header>

    <div v-if="danger && danger.actif && danger.messages.length" class="danger">
      ⚠️ {{ danger.messages.join(' · ') }}
    </div>

    <section class="carte planif" v-if="mareeSel || ventSel">
      <h2>🕐 Prévision (jusqu'à 48 h)</h2>
      <div class="planif-head">
        <span class="planif-heure">{{ cibleLabel }}</span>
        <button class="btn-now" @click="minutesFutur = 0">Maintenant</button>
      </div>
      <input class="slider" type="range" min="0" :max="HORIZON_MIN" step="15" v-model.number="minutesFutur" />
      <div class="ligne" v-if="mareeSel">
        <span class="k">🌊 Marée prévue</span>
        <span class="v">{{ mareeSel.niveau_m }} m · {{ mareeSel.phase }}</span>
      </div>
      <div class="ligne" v-if="ventSel">
        <span class="k">💨 Vent prévu</span>
        <span class="v">{{ ventSel.vent_dir }} {{ ventSel.vent_kmh }} km/h · raf. {{ ventSel.rafales_kmh }}</span>
      </div>
      <div class="ligne" v-if="ventSel && ventSel.temp_c != null">
        <span class="k">🌡️ Temp / nuages</span>
        <span class="v">{{ ventSel.temp_c }} °C · {{ ventSel.cloud_cover_pct }} %</span>
      </div>
      <div class="ligne" v-if="ventSel">
        <span class="k">🌧️ Pluie</span>
        <span class="v">{{ ventSel.pluie_mm ?? 0 }} mm<template v-if="ventSel.pluie_proba != null"> · {{ ventSel.pluie_proba }} %</template></span>
      </div>
      <div class="ligne orage-ligne" v-if="ventSel && ventSel.orage">
        <span class="k">⛈️ Orage</span><span class="v">prévu à cette heure</span>
      </div>
      <div class="horo">Marée : modèle harmonique · Vent/pluie/orage : prévision Open-Meteo · le débit n'est pas prévu (voir valeur actuelle ci-dessous).</div>
    </section>

    <section class="carte">
      <h2>🌊 Marée</h2>
      <template v-if="maree.disponible">
        <div class="ligne"><span class="k">Phase</span><span class="v">{{ maree.phase }}</span></div>
        <div class="ligne"><span class="k">Niveau observé</span><span class="v">{{ maree.niveau_observe_m }} m</span></div>
        <div class="ligne">
          <span class="k">Coefficient</span>
          <span class="v" v-if="maree.coefficient != null">{{ maree.coefficient }} ({{ maree.source_coef }})</span>
          <span class="stale" v-else>à venir</span>
        </div>
        <div class="ligne" v-if="!prochainesMarees.length">
          <span class="k">Prochaines marées</span><span class="stale">à venir (harmonique)</span>
        </div>
        <div class="ligne" v-for="(p, i) in prochainesMarees" :key="i">
          <span class="k">{{ p.type === 'PM' ? 'Pleine mer' : 'Basse mer' }}</span>
          <span class="v">{{ prefixeJour(p.heure_locale) }}{{ fmtH(p.heure_locale) }} ({{ p.hauteur_m }} m)</span>
        </div>
        <div class="horo">{{ maree.source_niveau }} · niveau observé {{ fmt(maree.horodatage_niveau) }}</div>
        <details class="methode" v-if="maree.methode_pm_bm">
          <summary>Décalage estuaire & méthode</summary>
          <p>{{ maree.methode_pm_bm }}</p>
        </details>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <section class="carte">
      <h2>💧 Débit Nive</h2>
      <template v-if="debit.disponible">
        <div class="ligne"><span class="k">Débit</span><span class="v">{{ debit.valeur_m3s }} m³/s</span></div>
        <div class="ligne" v-if="debit.navigation && debit.navigation.niveau">
          <span class="k">Navigation pirogue</span>
          <span class="v"><span class="nav-badge" :class="debit.navigation.niveau">{{ NAV_LABEL[debit.navigation.niveau] }}</span></span>
        </div>

        <div class="jauge" v-if="jauge">
          <div class="jauge-bar" :style="{ background: jauge.gradient }">
            <div class="curseur" :style="{ left: jauge.curseur + '%' }"></div>
          </div>
          <div class="jauge-labels">
            <span>{{ jauge.min }}</span>
            <span v-if="jauge.hors" class="stale">crue — hors échelle</span>
            <span>{{ jauge.max }}+ m³/s</span>
          </div>
        </div>

        <div class="ligne"><span class="k">Médian / module</span><span class="v">{{ debit.reperes.mediane_m3s }} / {{ debit.reperes.module_m3s }} m³/s</span></div>
        <div class="horo">{{ debit.source }} · {{ fmt(debit.horodatage) }}</div>
        <details class="methode" v-if="debit.navigation && debit.navigation.note">
          <summary>Seuils navigation</summary>
          <p>{{ debit.navigation.note }} Repères Nive à Cambo (1999–2026) : min connu {{ debit.reperes.min_connu_m3s }}, médian {{ debit.reperes.mediane_m3s }}, module {{ debit.reperes.module_m3s }}, max connu {{ debit.reperes.max_connu_m3s }} m³/s.</p>
        </details>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <section class="carte">
      <h2>🌤️ Météo</h2>
      <template v-if="meteo.disponible">
        <div class="ligne"><span class="k">Vent</span><span class="v">{{ meteo.vent_dir }} {{ meteo.vent_kmh }} km/h</span></div>
        <div class="ligne"><span class="k">Rafales</span><span class="v">{{ meteo.rafales_kmh }} km/h</span></div>
        <div class="ligne"><span class="k">Température</span><span class="v">{{ meteo.temp_c }} °C</span></div>
        <div class="ligne"><span class="k">Nuages</span><span class="v">{{ meteo.cloud_cover_pct }} %</span></div>
        <div class="ligne" v-if="meteo.ciel"><span class="k">Ciel</span><span class="v">{{ meteo.ciel }}</span></div>
        <div class="ligne" v-if="meteo.pluie_mm != null"><span class="k">Pluie</span><span class="v">{{ meteo.pluie_mm }} mm</span></div>
        <div class="ligne"><span class="k">Coucher du soleil</span><span class="v">{{ fmtH(meteo.coucher_soleil_local) }}</span></div>
        <div class="horo">Open-Meteo · {{ fmt(meteo.horodatage) }}</div>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <div class="notes" v-if="notes.length">
      <div v-for="(n, i) in notes" :key="i">• {{ n }}</div>
    </div>

    <section class="carte cam" v-if="webcam && webcam.disponible">
      <h2>🎥 Webcam <span class="cam-tag">secondaire</span></h2>
      <a :href="webcam.page_url" target="_blank" rel="noopener">
        <img :src="webcam.image_url" :alt="webcam.nom" class="cam-img" loading="lazy" />
      </a>
      <div class="horo">
        {{ webcam.nom }} —
        <a :href="webcam.page_url" target="_blank" rel="noopener">voir en direct</a>
        <span v-if="webcam.horodatage"> · capture {{ fmt(webcam.horodatage) }}</span>
      </div>
    </section>

    <footer>
      <p class="sources">Sources : Hub'Eau / Eaufrance · Open-Meteo · données SHOM · Météo-France</p>
      <p class="disclaimer">Aide d'information personnelle. Ne remplace pas les sources nautiques officielles (SHOM, capitainerie, Vigicrues, Météo-France marine). Données temps réel Hub'Eau brutes non expertisées.</p>
    </footer>
  </template>
</template>
