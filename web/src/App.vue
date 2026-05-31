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
  timer = setInterval(charger, 5 * 60 * 1000)
})

onUnmounted(() => clearInterval(timer))

const point = computed(() => data.value?.point)
const danger = computed(() => data.value?.danger)
const maree = computed(() => data.value?.maree)
const debit = computed(() => data.value?.debit)
const meteo = computed(() => data.value?.meteo)
const notes = computed(() => data.value?.notes || [])
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
          <span class="k">{{ p.type }}</span><span class="v">{{ fmtH(p.heure_locale) }} ({{ p.hauteur_m }} m)</span>
        </div>
        <div class="horo">{{ maree.source_niveau }} · {{ fmt(maree.horodatage_niveau) }}</div>
      </template>
      <p v-else class="stale">Donnée indisponible</p>
    </section>

    <section class="carte">
      <h2>💧 Débit Nive</h2>
      <template v-if="debit.disponible">
        <div class="ligne"><span class="k">Débit</span><span class="v">{{ debit.valeur_m3s }} m³/s</span></div>
        <div class="ligne"><span class="k">Palier</span><span class="v"><span class="badge" :class="debit.palier">{{ debit.palier }}</span></span></div>
        <div class="horo">{{ debit.source }} · {{ fmt(debit.horodatage) }}</div>
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
