<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

const props = defineProps({
  niveau: { type: Number, default: null },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 4.5 },
})

const wrap = ref(null)
const erreur = ref(null)
const H = 320
let renderer, scene, camera, water, raf, ro, clock

// hauteur du plan d'eau (m réels), avec une petite exagération pour la lisibilité
function waterY(n) {
  const base = -1
  if (n == null) return base + 1.5
  return base + n * 1.6
}

function shapeFromPoly(poly) {
  const s = new THREE.Shape()
  poly.forEach(([x, z], i) => (i ? s.lineTo(x, z) : s.moveTo(x, z)))
  return s
}

async function build(el) {
  const w = el.clientWidth || 320
  const url = `${import.meta.env.BASE_URL}bayonne3d.json`
  const data = await (await fetch(url)).json()

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a2030)
  scene.fog = new THREE.Fog(0x0a2030, 500, 1600)

  camera = new THREE.PerspectiveCamera(55, w / H, 1, 4000)
  camera.position.set(380, 320, 560)
  camera.lookAt(0, 10, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, H)
  el.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0x9fc6e0, 0.8))
  const sun = new THREE.DirectionalLight(0xfff2d8, 1.0)
  sun.position.set(300, 500, 200)
  scene.add(sun)

  // Sol
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(4000, 4000),
    new THREE.MeshStandardMaterial({ color: 0x223427, roughness: 1 }),
  )
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -1.2
  scene.add(ground)

  // Bâtiments — extrudés puis fusionnés en un seul mesh
  const geos = []
  for (const b of data.buildings) {
    if (!b.p || b.p.length < 3) continue
    const g = new THREE.ExtrudeGeometry(shapeFromPoly(b.p), { depth: b.h, bevelEnabled: false })
    g.rotateX(-Math.PI / 2)
    geos.push(g)
  }
  if (geos.length) {
    const merged = mergeGeometries(geos, false)
    const buildings = new THREE.Mesh(
      merged,
      new THREE.MeshStandardMaterial({ color: 0xb9c2cc, roughness: 0.85, flatShading: true }),
    )
    scene.add(buildings)
    geos.forEach((g) => g.dispose())
  }

  // Eau (Nive/Adour) — surfaces planes à la hauteur de marée
  const wgeos = []
  for (const wpoly of data.water) {
    if (!wpoly.p || wpoly.p.length < 3) continue
    const g = new THREE.ShapeGeometry(shapeFromPoly(wpoly.p))
    g.rotateX(-Math.PI / 2)
    wgeos.push(g)
  }
  if (wgeos.length) {
    water = new THREE.Mesh(
      mergeGeometries(wgeos, false),
      new THREE.MeshStandardMaterial({
        color: 0x1fb6d6, transparent: true, opacity: 0.82, roughness: 0.2, metalness: 0.2,
      }),
    )
    water.position.y = waterY(props.niveau)
    scene.add(water)
    wgeos.forEach((g) => g.dispose())
  }

  clock = new THREE.Clock()
  const center = new THREE.Vector3(0, 10, 0)
  const animate = () => {
    raf = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()
    const a = t * 0.06
    camera.position.x = Math.sin(a) * 620
    camera.position.z = Math.cos(a) * 620
    camera.position.y = 330
    camera.lookAt(center)
    if (water) water.position.y += (waterY(props.niveau) - water.position.y) * 0.06
    renderer.render(scene, camera)
  }
  animate()

  ro = new ResizeObserver(() => {
    const ww = el.clientWidth || 320
    camera.aspect = ww / H
    camera.updateProjectionMatrix()
    renderer.setSize(ww, H)
  })
  ro.observe(el)
}

onMounted(async () => {
  try {
    await build(wrap.value)
  } catch (e) {
    erreur.value = String(e)
  }
})

watch(() => props.niveau, () => {}) // l'animation lit props.niveau en continu

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  if (ro) ro.disconnect()
  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
  }
  scene?.traverse((o) => {
    if (o.geometry) o.geometry.dispose()
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose())
  })
})
</script>

<template>
  <div ref="wrap" class="city3d">
    <div v-if="erreur" class="city3d-err">Modèle 3D indisponible : {{ erreur }}</div>
  </div>
</template>

<style scoped>
.city3d { width: 100%; height: 320px; border-radius: 12px; overflow: hidden; position: relative; }
.city3d canvas { display: block; }
.city3d-err { padding: 12px; color: #e0a24a; font-size: 0.8rem; }
</style>
