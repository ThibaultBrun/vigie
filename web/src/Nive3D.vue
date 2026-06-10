<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  niveau: { type: Number, default: null },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 4.5 },
})

const wrap = ref(null)
const H = 280
const BED_Y = 0.15
const TOP_Y = 3
let renderer, scene, camera, group, water, baseZ, clock, raf, ro
let targetY = 0

function niveauToY(n) {
  if (n == null) return BED_Y + 0.4
  const r = Math.max(0, Math.min(1, (n - props.min) / (props.max - props.min || 1)))
  return BED_Y + 0.25 + r * (TOP_Y - 0.5)
}

onMounted(() => {
  const el = wrap.value
  const w = el.clientWidth || 320

  scene = new THREE.Scene()
  scene.fog = new THREE.Fog(0x07313c, 9, 24)
  camera = new THREE.PerspectiveCamera(50, w / H, 0.1, 100)
  camera.position.set(0, 4.4, 8.6)
  camera.lookAt(0, 1.2, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, H)
  el.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0xffffff, 0.75))
  const sun = new THREE.DirectionalLight(0xffffff, 0.95)
  sun.position.set(5, 9, 4)
  scene.add(sun)

  group = new THREE.Group()
  scene.add(group)

  // Berges (gauche/droite) — le chenal (rivière) est l'espace entre les deux
  const bankMat = new THREE.MeshStandardMaterial({ color: 0x4f6f3c, roughness: 1 })
  const bankGeo = new THREE.BoxGeometry(4, TOP_Y, 14)
  const left = new THREE.Mesh(bankGeo, bankMat)
  left.position.set(-3.2, TOP_Y / 2, 0)
  const right = new THREE.Mesh(bankGeo, bankMat)
  right.position.set(3.2, TOP_Y / 2, 0)
  group.add(left, right)

  // Lit de la rivière
  const bed = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 0.3, 14),
    new THREE.MeshStandardMaterial({ color: 0x33403a, roughness: 1 }),
  )
  bed.position.set(0, 0.15, 0)
  group.add(bed)

  // Ponton (illustratif)
  const pont = new THREE.Mesh(
    new THREE.BoxGeometry(1.7, 0.12, 1.3),
    new THREE.MeshStandardMaterial({ color: 0x8a5a2b, roughness: 0.8 }),
  )
  pont.position.set(-1.5, 2.15, 2)
  group.add(pont)

  // Plan d'eau
  const wgeo = new THREE.PlaneGeometry(2.4, 14, 20, 60)
  const wmat = new THREE.MeshStandardMaterial({
    color: 0x1fc6d6, transparent: true, opacity: 0.8, roughness: 0.2, metalness: 0.15,
  })
  water = new THREE.Mesh(wgeo, wmat)
  water.rotation.x = -Math.PI / 2
  targetY = niveauToY(props.niveau)
  water.position.y = targetY
  group.add(water)
  baseZ = wgeo.attributes.position.array.slice()

  clock = new THREE.Clock()
  const animate = () => {
    raf = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()
    group.rotation.y = Math.sin(t * 0.12) * 0.28
    water.position.y += (targetY - water.position.y) * 0.07
    const pos = water.geometry.attributes.position
    for (let i = 0; i < pos.count; i++) {
      const x = baseZ[i * 3]
      const y = baseZ[i * 3 + 1]
      pos.array[i * 3 + 2] = Math.sin(x * 1.6 + t * 1.6) * 0.05 + Math.cos(y * 0.9 + t) * 0.04
    }
    pos.needsUpdate = true
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
})

watch(() => [props.niveau, props.min, props.max], () => {
  targetY = niveauToY(props.niveau)
})

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
  <div ref="wrap" class="nive3d"></div>
</template>

<style scoped>
.nive3d { width: 100%; height: 280px; border-radius: 12px; overflow: hidden; }
.nive3d canvas { display: block; }
</style>
