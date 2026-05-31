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

const jauge = computed(() => {
  const d = debit.value
  if (!d?.disponible || !d.echelle || d.echelle.min_m3s == null) return null
  const e = d.echelle
  const span = e.max_m3s - e.min_m3s
  const pct = (x) => Math.max(0, Math.min(100, ((x - e.min_m3s) / span) * 100))
  const vert = pct(e.seuil_tranquille_m3s)
  const orange = pct(e.seuil_fort_m3s) - vert
  return {
    vert,
    orange,
    rouge: 100 - vert - orange,
    curseur: (e.position ?? 0) * 100,
    hors: e.hors_echelle,
    min: e.min_m3s,
    max: e.max_m3s,
  }
})

const NAV_LABEL = { tranquille: 'Tranquille', moyen: 'Ça pousse', fort: 'Fort courant' }
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
        <div class="ligne" v-if="!maree.pm_bm.length">
          <span class="k">PM / BM du jour</span><span class="stale">à venir (harmonique)</span>
        </div>
        <div class="ligne" v-for="(p, i) in maree.pm_bm" :key="i">
          <span class="k">{{ p.type === 'PM' ? 'Pleine mer' : 'Basse mer' }}</span><span class="v">{{ fmtH(p.heure_locale) }} ({{ p.hauteur_m }} m)</span>
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
          <div class="jauge-bar">
            <div class="zone vert" :style="{ width: jauge.vert + '%' }"></div>
            <div class="zone orange" :style="{ width: jauge.orange + '%' }"></div>
            <div class="zone rouge" :style="{ width: jauge.rouge + '%' }"></div>
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
        <div class="ligne"><span class="k">Coucher du soleil</span><span class="v">{{ fmtH(meteo.coucher_soleil_local) }}</span></div>
        <div class="horo">Open-Meteo · {{ fmt(meteo.horodatage) }}</div>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <div class="notes" v-if="notes.length">
      <div v-for="(n, i) in notes" :key="i">• {{ n }}</div>
    </div>

    <footer>
      <p class="sources">Sources : Hub'Eau / Eaufrance · Open-Meteo · données SHOM · Météo-France</p>
      <p class="disclaimer">Aide d'information personnelle. Ne remplace pas les sources nautiques officielles (SHOM, capitainerie, Vigicrues, Météo-France marine). Données temps réel Hub'Eau brutes non expertisées.</p>
    </footer>
  </template>
</template>
