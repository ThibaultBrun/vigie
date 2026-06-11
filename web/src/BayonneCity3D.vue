<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const props = defineProps({
  niveau: { type: Number, default: null },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 4.5 },
})

const wrap = ref(null)
const erreur = ref(null)
const H = 320
let renderer, scene, camera, water, raf, ro, controls

// hauteur du plan d'eau : reste au niveau de la rivière, monte/descend modérément avec la marée
function waterY(n) {
  if (n == null) return -0.4
  const r = Math.max(0, Math.min(1, (n - props.min) / (props.max - props.min || 1)))
  return -1.5 + r * 2.8 // basse mer ~ -1.5 m, pleine mer ~ +1.3 m
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
  camera.position.set(280, 180, 300)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, H)
  el.appendChild(renderer.domElement)

  // Navigation libre : 1 doigt = tourner, 2 doigts = zoom/déplacer (souris : clic-gauche/molette/clic-droit)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 4, 0)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 50
  controls.maxDistance = 1400
  controls.maxPolarAngle = Math.PI * 0.49 // empêche de passer sous le sol
  controls.update()

  scene.add(new THREE.AmbientLight(0xffffff, 0.9))
  const sun = new THREE.DirectionalLight(0xfff2d8, 1.0)
  sun.position.set(300, 500, 200)
  scene.add(sun)

  // Sol = fond de plan Esri World Imagery, calé sur la bbox
  const [bS, bW, bN, bE] = data.bbox
  const mLat = 110540
  const mLon = 111320 * Math.cos((data.center[0] * Math.PI) / 180)
  const gW = (bE - bW) * mLon
  const gD = (bN - bS) * mLat
  const tex = new THREE.TextureLoader().load(`${import.meta.env.BASE_URL}bayonne-basemap.jpg`)
  tex.colorSpace = THREE.SRGBColorSpace
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(gW, gD),
    new THREE.MeshStandardMaterial({ map: tex, roughness: 1 }),
  )
  ground.rotation.x = -Math.PI / 2
  ground.position.y = 0
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

  // Ponts — tabliers au-dessus de la Nive (les lignes OSM bridge -> rubans de boîtes)
  const bgeos = []
  const BW = 8, BTH = 1, BY = 6
  for (const br of data.bridges || []) {
    const p = br.p || []
    for (let i = 0; i < p.length - 1; i++) {
      const [x1, z1] = p[i]
      const [x2, z2] = p[i + 1]
      const dx = x2 - x1, dz = z2 - z1
      const len = Math.hypot(dx, dz)
      if (len < 1) continue
      const g = new THREE.BoxGeometry(len, BTH, BW)
      g.rotateY(-Math.atan2(dz, dx))
      g.translate((x1 + x2) / 2, BY, (z1 + z2) / 2)
      bgeos.push(g)
    }
  }
  if (bgeos.length) {
    const bridges = new THREE.Mesh(
      mergeGeometries(bgeos, false),
      new THREE.MeshStandardMaterial({ color: 0xcdb49a, roughness: 0.9 }),
    )
    scene.add(bridges)
    bgeos.forEach((g) => g.dispose())
  }

  const animate = () => {
    raf = requestAnimationFrame(animate)
    controls.update()
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
  if (controls) controls.dispose()
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
