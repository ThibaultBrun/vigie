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

function dShort(iso) {
  const p = iso.split('-')
  return `${p[2]}/${p[1]}`
}

function pad(n) {
  return String(n).padStart(2, '0')
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

const HEURES = 7 * 24
const NUIT_DEBUT = 22
const NUIT_FIN = 7

const pas = ref(0)
const futur = computed(() => pas.value > 0)

const creneaux = computed(() => {
  void data.value
  const out = []
  const base = new Date()
  base.setMinutes(0, 0, 0)
  base.setHours(base.getHours() + 1)
  const fin = Date.now() + HEURES * 3600000
  for (let t = base.getTime(); t <= fin; t += 3600000) {
    const h = new Date(t).getHours()
    if (h >= NUIT_FIN && h < NUIT_DEBUT) out.push(t)
  }
  return out
})

const cibleMs = computed(() => {
  if (pas.value === 0) return Date.now()
  const arr = creneaux.value
  if (!arr.length) return Date.now()
  return arr[Math.min(pas.value - 1, arr.length - 1)]
})

function estAujourdhui(d) {
  const j0 = new Date(); j0.setHours(0, 0, 0, 0)
  const jd = new Date(d); jd.setHours(0, 0, 0, 0)
  return jd.getTime() === j0.getTime()
}

function jourDate(d) {
  const dt = new Date(d)
  const j = dt.toLocaleDateString('fr-FR', { weekday: 'long' })
  return `${j} ${pad(dt.getDate())}/${pad(dt.getMonth() + 1)}`
}

function prefixeJour(d) {
  return estAujourdhui(d) ? '' : jourDate(d) + ' '
}

const cibleLabel = computed(() => {
  const d = new Date(cibleMs.value)
  const p = estAujourdhui(d) ? 'aujourd’hui' : jourDate(d)
  return `${p} ${pad(d.getHours())}:${pad(d.getMinutes())}`
})

const cibleDateStr = computed(() => {
  const d = new Date(cibleMs.value)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
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

const mareeVue = computed(() => {
  const m = maree.value
  if (!m || !m.disponible) return null
  if (!futur.value) return { niveau: m.niveau_observe_m, phase: m.phase, label: 'observé' }
  const s = mareeSel.value
  if (!s) return { niveau: m.niveau_observe_m, phase: m.phase, label: 'observé' }
  return { niveau: s.niveau_m, phase: s.phase, label: 'prévu' }
})

const meteoVue = computed(() => {
  const m = meteo.value
  if (!m || !m.disponible) return null
  const s = futur.value ? ventSel.value : m
  if (!s) return null
  return {
    vent_kmh: s.vent_kmh, vent_dir: s.vent_dir, rafales_kmh: s.rafales_kmh,
    temp_c: s.temp_c, cloud_cover_pct: s.cloud_cover_pct, ciel: s.ciel,
    pluie_mm: s.pluie_mm, pluie_proba: s.pluie_proba, orage: s.orage,
  }
})

const coefVue = computed(() => {
  const jours = maree.value?.coefficients_jours || []
  const f = jours.find((j) => j.date === cibleDateStr.value)
  return f ? f.coefficients : (maree.value?.coefficients_jour || [])
})

const coucherVue = computed(() => {
  const m = meteo.value
  if (!m) return null
  const arr = m.coucher_soleil_jours || []
  const f = arr.find((c) => (c.date || '').slice(0, 10) === cibleDateStr.value)
  return f ? f.heure : m.coucher_soleil_local
})

const VB_W = 320
const VB_H = 90

const graph = computed(() => {
  const c = maree.value?.courbe || []
  if (c.length < 2) return null
  const all = c.map((p) => ({ t: new Date(p.heure_locale).getTime(), h: p.niveau_m }))
  const dStart = all[0].t
  const dEnd = all[all.length - 1].t
  const FEN = 27 * 3600000
  let t0 = Math.max(dStart, cibleMs.value - 4 * 3600000)
  let t1 = Math.min(dEnd, t0 + FEN)
  t0 = Math.max(dStart, t1 - FEN)
  const pts = all.filter((p) => p.t >= t0 - 1800000 && p.t <= t1 + 1800000)
  if (pts.length < 2) return null
  const hs = pts.map((p) => p.h)
  const hmin = Math.min(...hs)
  const hmax = Math.max(...hs)
  const pad = (hmax - hmin) * 0.12 || 0.5
  const ylo = hmin - pad
  const yhi = hmax + pad
  const X = (t) => ((t - t0) / (t1 - t0)) * VB_W
  const Y = (h) => VB_H - ((h - ylo) / (yhi - ylo)) * VB_H
  const ligne = pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ' ' + Y(p.h).toFixed(1)).join(' ')
  const cm = Math.max(t0, Math.min(t1, cibleMs.value))
  let hc = pts[pts.length - 1].h
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].t >= cm) {
      const a = pts[i - 1]
      const b = pts[i]
      const r = b.t === a.t ? 0 : (cm - a.t) / (b.t - a.t)
      hc = a.h + (b.h - a.h) * r
      break
    }
  }
  const aire = `${ligne} L ${X(pts[pts.length - 1].t).toFixed(1)} ${VB_H} L ${X(pts[0].t).toFixed(1)} ${VB_H} Z`
  return { ligne, aire, cx: X(cm).toFixed(1), cy: Y(hc).toFixed(1) }
})

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
  return { gradient, curseur: tf(d.valeur_m3s), hors: d.valeur_m3s > e.max_m3s, min: e.min_m3s, max: e.max_m3s }
})

const prochainesMarees = computed(() => {
  const now = Date.now() - 1800000
  return (maree.value?.pm_bm || [])
    .filter((p) => new Date(p.heure_locale).getTime() >= now)
    .slice(0, 2)
})

const NIVEAUX = {
  1: { label: 'Tranquille', classe: 'tranquille' },
  2: { label: 'Modéré', classe: 'moyen' },
  3: { label: 'Soutenu', classe: 'soutenu' },
  4: { label: 'Fort', classe: 'fort' },
}

const remontee = computed(() => {
  const d = debit.value
  const m = maree.value
  if (!d?.disponible || !m?.disponible) return null
  const v = d.valeur_m3s
  const st = d.echelle?.seuil_tranquille_m3s ?? 15
  const sf = d.echelle?.seuil_fort_m3s ?? 40
  const riverLvl = v <= st ? 1 : (v >= sf ? 3 : 2)
  const riverTxt = v <= st ? 'débit faible' : (v >= sf ? 'débit fort' : 'débit moyen')

  const c = m.courbe || []
  let slope = 0
  if (c.length > 1) {
    let bi = 0, bd = Infinity
    for (let i = 0; i < c.length; i++) {
      const dd = Math.abs(new Date(c[i].heure_locale).getTime() - cibleMs.value)
      if (dd < bd) { bd = dd; bi = i }
    }
    const a = Math.min(bi, c.length - 2)
    slope = (c[a + 1].niveau_m - c[a].niveau_m) * 4
  }
  const ph = (futur.value ? mareeSel.value?.phase : m.phase) || ''
  const force = Math.abs(slope)
  let adj = 0
  let tideTxt = ''
  if (ph.includes('étale') || force < 0.25) {
    adj = 0
    tideTxt = 'étale (courant de marée quasi nul)'
  } else if (ph.includes('montante')) {
    adj = force > 0.7 ? -2 : -1
    tideTxt = 'flot' + (force > 0.7 ? ' fort' : '') + ' — la marée pousse vers l’amont (aide)'
  } else {
    adj = force > 0.7 ? 2 : 1
    tideTxt = 'jusant' + (force > 0.7 ? ' fort' : '') + ' — la marée tire vers l’aval (gêne)'
  }
  const lvl = Math.max(1, Math.min(4, riverLvl + adj))
  return { ...NIVEAUX[lvl], texte: `${riverTxt} + ${tideTxt}.` }
})
</script>

<template>
  <div v-if="erreur" class="stale">Erreur de chargement : {{ erreur }}</div>

  <template v-if="data">
    <header>
      <h1>{{ point.nom }}</h1>
      <p class="sub">Données réelles : {{ fmt(data.horodatage) }}</p>
    </header>

    <div v-if="danger && danger.actif && danger.messages.length" class="danger">
      ⚠️ {{ danger.messages.join(' · ') }}
    </div>

    <section class="carte tbar">
      <div class="tbar-head">
        <span class="tbar-label">{{ futur ? cibleLabel : '🕐 Maintenant' }}</span>
        <button class="btn-now" v-if="futur" @click="pas = 0">↩ Maintenant</button>
      </div>
      <input class="slider" type="range" min="0" :max="creneaux.length" step="1" v-model.number="pas" />
      <div class="tbar-hint">
        {{ futur ? 'Prévisions à cette heure — débit & webcam non prévisibles (grisés)' : 'Glisse pour projeter jusqu’à 48 h' }}
      </div>
    </section>

    <section class="carte" v-if="remontee">
      <h2>🛶 Remontée pirogue <span class="tag-prev" v-if="futur">{{ cibleLabel }}</span></h2>
      <div class="ligne">
        <span class="k">Effort estimé</span>
        <span class="v"><span class="nav-badge" :class="remontee.classe">{{ remontee.label }}</span></span>
      </div>
      <div class="horo">{{ remontee.texte }}</div>
      <div class="note-nonprev">Estimation combinée débit + marée. Débit supposé = actuel ({{ debit.valeur_m3s }} m³/s, non prévu) ; effet marée calculé pour l’heure choisie.</div>
    </section>

    <section class="carte">
      <h2>🌊 Marée <span class="tag-prev" v-if="futur">prévue</span></h2>
      <svg v-if="graph" class="tide-graph" :viewBox="`0 0 ${VB_W} ${VB_H}`" preserveAspectRatio="none">
        <path :d="graph.aire" class="tg-area" />
        <path :d="graph.ligne" class="tg-line" />
        <line :x1="graph.cx" :x2="graph.cx" y1="0" :y2="VB_H" class="tg-cursor" />
        <circle :cx="graph.cx" :cy="graph.cy" r="3" class="tg-dot" />
      </svg>
      <template v-if="mareeVue">
        <div class="ligne"><span class="k">Phase</span><span class="v">{{ mareeVue.phase }}</span></div>
        <div class="ligne"><span class="k">Niveau {{ mareeVue.label }}</span><span class="v">{{ mareeVue.niveau }} m</span></div>
        <div class="ligne">
          <span class="k">Coefficient</span>
          <span class="v" v-if="coefVue.length">{{ coefVue.join(' / ') }} <span class="cf-src">({{ maree.source_coef }})</span></span>
          <span class="stale" v-else>indisponible</span>
        </div>
        <div class="coef7" v-if="maree.coefficients_jours && maree.coefficients_jours.length">
          <div class="cj" :class="{ 'cj-sel': j.date === cibleDateStr }" v-for="(j, i) in maree.coefficients_jours" :key="i">
            <span class="cj-d">{{ dShort(j.date) }}</span>
            <span class="cj-c">{{ j.coefficients.length ? Math.max(...j.coefficients) : '—' }}</span>
          </div>
        </div>
        <div class="ligne" v-if="!prochainesMarees.length">
          <span class="k">Prochaines marées</span><span class="stale">à venir (harmonique)</span>
        </div>
        <div class="ligne" v-for="(p, i) in prochainesMarees" :key="i">
          <span class="k">{{ p.type === 'PM' ? 'Pleine mer' : 'Basse mer' }}</span>
          <span class="v">{{ prefixeJour(p.heure_locale) }}{{ fmtH(p.heure_locale) }} ({{ p.hauteur_m }} m)</span>
        </div>
        <details class="methode" v-if="maree.methode_pm_bm">
          <summary>Décalage estuaire & méthode</summary>
          <p>{{ maree.methode_pm_bm }}</p>
        </details>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <section class="carte" :class="{ grise: futur }">
      <h2>💧 Débit Nive <span class="tag-nonprev" v-if="futur">non prévu</span></h2>
      <template v-if="debit.disponible">
        <div class="ligne"><span class="k">Débit</span><span class="v">{{ debit.valeur_m3s }} m³/s</span></div>
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
        <div class="ligne"><span class="k">Mesuré à</span><span class="v">{{ fmt(debit.horodatage) }}</span></div>
        <div class="horo">{{ debit.source }}</div>
        <details class="methode" v-if="debit.navigation && debit.navigation.note">
          <summary>Seuils navigation</summary>
          <p>{{ debit.navigation.note }} Repères Nive à Cambo (1999–2026) : min connu {{ debit.reperes.min_connu_m3s }}, médian {{ debit.reperes.mediane_m3s }}, module {{ debit.reperes.module_m3s }}, max connu {{ debit.reperes.max_connu_m3s }} m³/s.</p>
        </details>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
      <div class="note-nonprev" v-if="futur">Le débit n’est pas prévisible — valeur actuelle affichée.</div>
    </section>

    <section class="carte">
      <h2>🌤️ Météo <span class="tag-prev" v-if="futur">prévue</span></h2>
      <template v-if="meteoVue">
        <div class="ligne"><span class="k">Vent</span><span class="v">{{ meteoVue.vent_dir }} {{ meteoVue.vent_kmh }} km/h</span></div>
        <div class="ligne"><span class="k">Rafales</span><span class="v">{{ meteoVue.rafales_kmh }} km/h</span></div>
        <div class="ligne"><span class="k">Température</span><span class="v">{{ meteoVue.temp_c }} °C</span></div>
        <div class="ligne"><span class="k">Nuages</span><span class="v">{{ meteoVue.cloud_cover_pct }} %</span></div>
        <div class="ligne" v-if="meteoVue.ciel"><span class="k">Ciel</span><span class="v">{{ meteoVue.ciel }}</span></div>
        <div class="ligne" v-if="meteoVue.pluie_mm > 0">
          <span class="k">Pluie</span>
          <span class="v">{{ meteoVue.pluie_mm }} mm<template v-if="meteoVue.pluie_proba != null"> · {{ meteoVue.pluie_proba }} %</template></span>
        </div>
        <div class="ligne orage-ligne" v-if="meteoVue.orage">
          <span class="k">⛈️ Orage</span><span class="v">{{ futur ? 'prévu à cette heure' : 'en cours' }}</span>
        </div>
        <div class="ligne"><span class="k">Coucher du soleil</span><span class="v">{{ fmtH(coucherVue) }}</span></div>
        <div class="horo" v-if="!futur">Open-Meteo · {{ fmt(meteo.horodatage) }}</div>
        <div class="horo" v-else>Prévision Open-Meteo</div>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <div class="notes" v-if="notes.length">
      <div v-for="(n, i) in notes" :key="i">• {{ n }}</div>
    </div>

    <section class="carte cam" :class="{ grise: futur }" v-if="webcam && webcam.disponible">
      <h2>🎥 Webcam <span class="cam-tag">{{ futur ? 'instant présent' : 'secondaire' }}</span></h2>
      <a :href="webcam.page_url" target="_blank" rel="noopener">
        <img :src="webcam.image_url" :alt="webcam.nom" class="cam-img" loading="lazy" />
      </a>
      <div class="horo">
        {{ webcam.nom }} —
        <a :href="webcam.page_url" target="_blank" rel="noopener">voir en direct</a>
        <span v-if="webcam.horodatage"> · capture {{ fmt(webcam.horodatage) }}</span>
      </div>
      <div class="note-nonprev" v-if="futur">Image en direct — pas de projection dans le futur.</div>
    </section>

    <footer>
      <p class="sources">Sources : Hub'Eau / Eaufrance · Open-Meteo · données SHOM · Météo-France</p>
      <p class="disclaimer">Aide d'information personnelle. Ne remplace pas les sources nautiques officielles (SHOM, capitainerie, Vigicrues, Météo-France marine). Données temps réel Hub'Eau brutes non expertisées.</p>
    </footer>
  </template>
</template>
