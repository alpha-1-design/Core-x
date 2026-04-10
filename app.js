let scene, camera, renderer, globe, markers = {};
let animationId;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };
let globeRotation = { x: 0.1, y: 0 };
let targetRotation = { x: 0.1, y: 0 };
let zoom = 2.5;
let targetZoom = 2.5;
let globeTexture;
let hotspots = {};
let eventMarkers = {};

const EARTH_TEXTURE_URL = 'https://unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg';

function init() {
  scene = new THREE.Scene();
  
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = zoom;
  
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  document.getElementById('globe-container').appendChild(renderer.domElement);
  
  createStarfield();
  createGlobe();
  createAtmosphere();
  
  setupEventListeners();
  animate();
}

function createStarfield() {
  const starsGeometry = new THREE.BufferGeometry();
  const starCount = 3000;
  const positions = new Float32Array(starCount * 3);
  
  for (let i = 0; i < starCount * 3; i += 3) {
    const radius = 100 + Math.random() * 200;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    
    positions[i] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i + 1] = radius * Math.sin(phi) * Math.sin(theta);
    positions[i + 2] = radius * Math.cos(phi);
  }
  
  starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  
  const starsMaterial = new THREE.PointsMaterial({
    color: 0xffffff,
    size: 0.3,
    transparent: true,
    opacity: 0.6
  });
  
  const stars = new THREE.Points(starsGeometry, starsMaterial);
  scene.add(stars);
}

function createGlobe() {
  const geometry = new THREE.SphereGeometry(1, 64, 64);
  
  const textureLoader = new THREE.TextureLoader();
  textureLoader.load(
    EARTH_TEXTURE_URL,
    (texture) => {
      globeTexture = texture;
      texture.colorSpace = THREE.SRGBColorSpace;
      
      const material = new THREE.MeshPhongMaterial({
        map: texture,
        bumpScale: 0.05,
        specular: new THREE.Color(0x333333),
        shininess: 5
      });
      
      globe.material = material;
    },
    undefined,
    (error) => {
      console.warn('Could not load Earth texture, using fallback');
      createFallbackGlobe();
    }
  );
  
  const material = new THREE.MeshPhongMaterial({
    color: 0x1a365d,
    specular: 0x333333,
    shininess: 5
  });
  
  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);
  
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
  scene.add(ambientLight);
  
  const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
  sunLight.position.set(5, 3, 5);
  scene.add(sunLight);
  
  const blueLight = new THREE.DirectionalLight(0x3b82f6, 0.3);
  blueLight.position.set(-5, -3, -5);
  scene.add(blueLight);
}

function createFallbackGlobe() {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  
  const gradient = ctx.createLinearGradient(0, 0, 0, 512);
  gradient.addColorStop(0, '#1a365d');
  gradient.addColorStop(0.5, '#2c5282');
  gradient.addColorStop(1, '#1a365d');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 1024, 512);
  
  ctx.fillStyle = '#234e52';
  drawFallbackContinents(ctx);
  
  const texture = new THREE.CanvasTexture(canvas);
  globe.material = new THREE.MeshPhongMaterial({
    map: texture,
    specular: 0x333333,
    shininess: 5
  });
}

function drawFallbackContinents(ctx) {
  const continents = [
    [[100, 150], [180, 120], [250, 150], [280, 200], [220, 250], [120, 230], [80, 190]],
    [[350, 130], [450, 100], [520, 140], [550, 200], [500, 280], [400, 260], [340, 200]],
    [[500, 280], [580, 260], [620, 300], [600, 360], [540, 380], [480, 340]],
    [[180, 300], [240, 280], [280, 320], [260, 380], [200, 370], [160, 340]],
    [[300, 320], [360, 300], [400, 340], [380, 400], [320, 390], [280, 360]],
    [[420, 320], [480, 300], [520, 340], [500, 400], [440, 390], [400, 360]],
  ];
  
  continents.forEach(cont => {
    ctx.beginPath();
    ctx.moveTo(cont[0][0], cont[0][1]);
    cont.slice(1).forEach(p => ctx.lineTo(p[0], p[1]));
    ctx.closePath();
    ctx.fill();
  });
}

function createAtmosphere() {
  const atmosphereGeometry = new THREE.SphereGeometry(1.02, 64, 64);
  const atmosphereMaterial = new THREE.ShaderMaterial({
    vertexShader: `
      varying vec3 vNormal;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vNormal;
      void main() {
        float intensity = pow(0.7 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
        gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * intensity;
      }
    `,
    blending: THREE.AdditiveBlending,
    side: THREE.BackSide,
    transparent: true
  });
  
  const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
  scene.add(atmosphere);
}

function latLngToVector3(lat, lng, radius = 1.01) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lng + 180) * Math.PI / 180;
  
  const x = -(Math.sin(phi) * Math.cos(theta));
  const z = Math.sin(phi) * Math.sin(theta);
  const y = Math.cos(phi);
  
  return new THREE.Vector3(x * radius, y * radius, z * radius);
}

function getSeverityColor(severity) {
  switch (severity) {
    case 'critical': return 0xef4444;
    case 'high': return 0xf97316;
    case 'medium': return 0xf59e0b;
    case 'low': return 0x3b82f6;
    default: return 0x10b981;
  }
}

function getScoreColor(score) {
  if (score >= 75) return 0xef4444;
  if (score >= 50) return 0xf97316;
  if (score >= 25) return 0xf59e0b;
  return 0x10b981;
}

function addEventMarker(event) {
  if (!event.lat || !event.lng) return;
  
  const pos = latLngToVector3(event.lat, event.lng);
  const color = getSeverityColor(event.severity);
  
  const markerGroup = new THREE.Group();
  markerGroup.position.copy(pos);
  markerGroup.userData = { eventId: event.id, event: event };
  
  const coreGeo = new THREE.SphereGeometry(0.015, 16, 16);
  const coreMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.9 });
  const core = new THREE.Mesh(coreGeo, coreMat);
  markerGroup.add(core);
  
  const glowGeo = new THREE.SphereGeometry(0.03, 16, 16);
  const glowMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.2
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  markerGroup.add(glow);
  
  const ringGeo = new THREE.RingGeometry(0.025, 0.04, 32);
  const ringMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.5,
    side: THREE.DoubleSide
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.lookAt(new THREE.Vector3(0, 0, 0));
  ring.userData.isRing = true;
  markerGroup.add(ring);
  
  globe.add(markerGroup);
  eventMarkers[event.id] = markerGroup;
}

function addHotspotMarker(region) {
  const pos = latLngToVector3(region.lat, region.lng, 1.005);
  const color = getScoreColor(region.score);
  
  const group = new THREE.Group();
  group.position.copy(pos);
  group.userData = { regionCode: region.code, region: region };
  
  const ringGeo = new THREE.RingGeometry(0.06, 0.1, 32);
  const ringMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: Math.min(0.8, region.score / 100),
    side: THREE.DoubleSide
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.lookAt(new THREE.Vector3(0, 0, 0));
  ring.userData.isHotspotRing = true;
  ring.userData.baseOpacity = Math.min(0.8, region.score / 100);
  group.add(ring);
  
  if (region.score >= 50) {
    const pulseGeo = new THREE.RingGeometry(0.08, 0.12, 32);
    const pulseMat = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide
    });
    const pulse = new THREE.Mesh(pulseGeo, pulseMat);
    pulse.lookAt(new THREE.Vector3(0, 0, 0));
    pulse.userData.isPulse = true;
    pulse.userData.baseOpacity = 0.3;
    group.add(pulse);
  }
  
  globe.add(group);
  hotspots[region.code] = group;
}

function clearEventMarkers() {
  Object.values(eventMarkers).forEach(marker => globe.remove(marker));
  eventMarkers = {};
}

function clearHotspots() {
  Object.values(hotspots).forEach(h => globe.remove(h));
  hotspots = {};
}

function updateMarkerStatus(eventId, severity) {
  const marker = eventMarkers[eventId];
  if (!marker) return;
  
  const color = getSeverityColor(severity);
  marker.children.forEach(child => {
    if (child.material) {
      child.material.color.setHex(color);
    }
  });
}

function setupEventListeners() {
  const container = document.getElementById('globe-container');
  
  container.addEventListener('mousedown', (e) => {
    isDragging = true;
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });
  
  container.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    
    const deltaX = e.clientX - previousMousePosition.x;
    const deltaY = e.clientY - previousMousePosition.y;
    
    targetRotation.y += deltaX * 0.005;
    targetRotation.x += deltaY * 0.005;
    targetRotation.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, targetRotation.x));
    
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });
  
  container.addEventListener('mouseup', () => { isDragging = false; });
  container.addEventListener('mouseleave', () => { isDragging = false; });
  
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    targetZoom += e.deltaY * 0.002;
    targetZoom = Math.max(1.5, Math.min(5, targetZoom));
  });
  
  container.addEventListener('click', onGlobeClick);
  
  window.addEventListener('resize', onWindowResize);
}

function onGlobeClick(event) {
  const container = document.getElementById('globe-container');
  const rect = container.getBoundingClientRect();
  
  const mouse = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  );
  
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera);
  
  const allMarkers = [...Object.values(eventMarkers), ...Object.values(hotspots)];
  if (allMarkers.length === 0) return;
  
  const intersects = raycaster.intersectObjects(allMarkers, true);
  
  for (let intersect of intersects) {
    let obj = intersect.object;
    while (obj.parent && obj.parent !== globe) {
      obj = obj.parent;
    }
    if (obj.userData.eventId) {
      window.dispatchEvent(new CustomEvent('eventSelected', { detail: obj.userData.event }));
      return;
    }
    if (obj.userData.regionCode) {
      window.dispatchEvent(new CustomEvent('regionSelected', { detail: obj.userData.region }));
      return;
    }
  }
}

function selectRegion(lat, lng) {
  const pos = latLngToVector3(lat, lng);
  targetRotation.y = Math.atan2(pos.x, pos.z) + Math.PI;
  targetRotation.x = Math.asin(pos.y) * 0.5;
  targetZoom = 2.0;
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  animationId = requestAnimationFrame(animate);
  
  globeRotation.x += (targetRotation.x - globeRotation.x) * 0.08;
  globeRotation.y += (targetRotation.y - globeRotation.y) * 0.08;
  
  globe.rotation.x = globeRotation.x;
  globe.rotation.y = globeRotation.y;
  
  zoom += (targetZoom - zoom) * 0.08;
  camera.position.z = zoom;
  
  const time = Date.now() * 0.001;
  
  Object.values(eventMarkers).forEach(marker => {
    marker.children.forEach(child => {
      if (child.userData.isRing) {
        child.rotation.z += 0.02;
        child.material.opacity = 0.3 + Math.sin(time * 2) * 0.2;
      }
    });
  });
  
  Object.values(hotspots).forEach(hotspot => {
    hotspot.children.forEach(child => {
      if (child.userData.isHotspotRing) {
        child.rotation.z += 0.005;
      }
      if (child.userData.isPulse) {
        const scale = 1 + Math.sin(time * 1.5) * 0.3;
        child.scale.set(scale, scale, scale);
        child.material.opacity = child.userData.baseOpacity * (0.5 + Math.sin(time * 1.5) * 0.5);
      }
    });
  });
  
  renderer.render(scene, camera);
}

function loadEvents(events) {
  clearEventMarkers();
  events.forEach(event => addEventMarker(event));
}

function loadHotspots(regions) {
  clearHotspots();
  regions.forEach(region => {
    if (region.score >= 10) {
      addHotspotMarker(region);
    }
  });
}

window.globeAPI = {
  loadEvents,
  loadHotspots,
  selectRegion,
  latLngToVector3
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
