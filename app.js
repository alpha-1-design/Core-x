let scene, camera, renderer, globe, markers = {};
let animationId;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };
let globeRotation = { x: 0.1, y: 0 };
let targetRotation = { x: 0.1, y: 0 };
let zoom = 2.5;
let targetZoom = 2.5;
let globeTexture;
let nightTexture;
let cloudTexture;
let hotspots = {};
let eventMarkers = {};
let currentMode = 'day';
let cloudLayer = null;
let hoveredMarker = null;
let tooltipEl = null;
let lastClickTime = 0;
let lastClickPos = { x: 0, y: 0 };
let isFlyingTo = false;
let flightTarget = null;
let flightStartRotation = null;
let flightStartZoom = null;
let flightStartTime = 0;
let flightDuration = 1000;
let flightEasing = null;
let touchStartDistance = 0;
let pinchCenter = { x: 0, y: 0 };
let clusters = {};
let minimapCanvas = null;
let minimapCtx = null;
let sunLight = null;
let flightPaths = [];
let lastMousePos = { x: 0, y: 0 };

const EARTH_TEXTURE_URL = 'https://unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg';
const NIGHT_TEXTURE_URL = 'https://unpkg.com/three-globe@2.31.0/example/img/earth-night.jpg';
const CLOUD_TEXTURE_URL = 'https://cdn.jsdelivr.net/npm/three-globe@2.31.0/example/img/earth-clouds.png';
const TERRAIN_NORMAL_URL = 'https://cdn.jsdelivr.net/npm/three-globe@2.31.0/example/img/earth-topology.png';
const BATHYMETRY_URL = 'https://cdn.jsdelivr.net/npm/three-globe@2.31.0/example/img/earth-bathymetry.jpg';

const THREE = window.THREE;

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

let normalMapTexture;
let bathymetryTexture;

function createGlobe() {
  const geometry = new THREE.SphereGeometry(1, 128, 128);
  
  const textureLoader = new THREE.TextureLoader();
  let terrainLoaded = false;
  let normalLoaded = false;
  let bathyLoaded = false;
  
  textureLoader.load(
    TERRAIN_NORMAL_URL,
    (normalMap) => {
      normalMapTexture = normalMap;
      normalMap.wrapS = THREE.RepeatWrapping;
      normalMap.wrapT = THREE.RepeatWrapping;
      normalLoaded = true;
      applyTerrainEnhancements();
    },
    undefined,
    () => console.warn('Could not load terrain normal map')
  );
  
  textureLoader.load(
    BATHYMETRY_URL,
    (bathymetry) => {
      bathymetryTexture = bathymetry;
      bathymetry.wrapS = THREE.RepeatWrapping;
      bathymetry.wrapT = THREE.RepeatWrapping;
      bathyLoaded = true;
      applyTerrainEnhancements();
    },
    undefined,
    () => console.warn('Could not load bathymetry map')
  );
  
  textureLoader.load(
    EARTH_TEXTURE_URL,
    (texture) => {
      globeTexture = texture;
      texture.colorSpace = THREE.SRGBColorSpace;
      terrainLoaded = true;
      applyTerrainEnhancements();
    },
    undefined,
    (error) => {
      console.warn('Could not load Earth texture, using fallback');
      createFallbackGlobe();
    }
  );
  
  textureLoader.load(NIGHT_TEXTURE_URL, (texture) => {
    nightTexture = texture;
    texture.colorSpace = THREE.SRGBColorSpace;
  });
  
  function applyTerrainEnhancements() {
    if (!globe || !terrainLoaded) return;
    
    const material = new THREE.MeshPhongMaterial({
      map: globeTexture,
      normalMap: normalMapTexture || null,
      normalScale: new THREE.Vector2(0.8, 0.8),
      bumpMap: bathymetryTexture || null,
      bumpScale: 0.03,
      specular: 0x333333,
      shininess: 10
    });
    
    globe.material = material;
  }
  
  const material = new THREE.MeshPhongMaterial({
    color: 0x1a365d,
    specular: 0x333333,
    shininess: 5
  });
  
  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);
  
  if (cloudTexture) {
    createCloudLayer();
  } else {
    textureLoader.load(
      CLOUD_TEXTURE_URL,
      (texture) => {
        cloudTexture = texture;
        createCloudLayer();
      },
      undefined,
      () => console.warn('Could not load cloud texture')
    );
  }
  
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
  scene.add(ambientLight);
  
  sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
  sunLight.position.set(5, 3, 5);
  scene.add(sunLight);
  
  const blueLight = new THREE.DirectionalLight(0x3b82f6, 0.3);
  blueLight.position.set(-5, -3, -5);
  scene.add(blueLight);
}

function createCloudLayer() {
  if (!cloudTexture) return;
  
  const cloudGeometry = new THREE.SphereGeometry(1.02, 128, 128);
  const cloudMaterial = new THREE.MeshPhongMaterial({
    map: cloudTexture,
    transparent: true,
    opacity: 0.4,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
  
  cloudLayer = new THREE.Mesh(cloudGeometry, cloudMaterial);
  cloudLayer.visible = false;
  scene.add(cloudLayer);
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
      varying vec3 vPosition;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vNormal;
      varying vec3 vPosition;
      uniform vec3 sunDirection;
      
      void main() {
        vec3 viewDir = normalize(-vPosition);
        vec3 normal = normalize(vNormal);
        
        float sunInfluence = max(0.0, dot(normal, sunDirection));
        
        float fresnel = pow(1.0 - max(0.0, dot(viewDir, normal)), 3.0);
        
        vec3 dayColor = vec3(0.4, 0.6, 1.0);
        vec3 sunsetColor = vec3(1.0, 0.5, 0.2);
        vec3 nightColor = vec3(0.1, 0.15, 0.3);
        
        float dayFactor = sunInfluence;
        float sunsetFactor = max(0.0, 1.0 - abs(sunInfluence - 0.5) * 2.0);
        
        vec3 atmosphereColor = mix(nightColor, dayColor, dayFactor);
        atmosphereColor = mix(atmosphereColor, sunsetColor, sunsetFactor * 0.5);
        
        float intensity = fresnel * 0.8 + (1.0 - fresnel) * 0.2;
        
        gl_FragColor = vec4(atmosphereColor, intensity * 0.6);
      }
    `,
    blending: THREE.AdditiveBlending,
    side: THREE.BackSide,
    transparent: true,
    uniforms: {
      sunDirection: { value: new THREE.Vector3(1, 0.5, 1).normalize() }
    }
  });
  
  const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
  atmosphere.userData.isAtmosphere = true;
  scene.add(atmosphere);
}

function updateAtmosphere() {
  if (!sunLight) return;
  
  scene.children.forEach(child => {
    if (child.userData && child.userData.isAtmosphere && child.material.uniforms) {
      const sunDir = new THREE.Vector3();
      sunDir.copy(sunLight.position).normalize();
      child.material.uniforms.sunDirection.value = sunDir;
    }
  });
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
  
  createTooltip();
  createMinimap();
  
  container.addEventListener('mousedown', (e) => {
    if (e.target === renderer.domElement) {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    }
  });
  
  container.addEventListener('mousemove', (e) => {
    lastMousePos = { x: e.clientX, y: e.clientY };
    if (!isDragging && !isFlyingTo) {
      checkHover(e.clientX, e.clientY);
    }
    if (!isDragging) return;
    
    const deltaX = e.clientX - previousMousePosition.x;
    const deltaY = e.clientY - previousMousePosition.y;
    
    targetRotation.y += deltaX * 0.005;
    targetRotation.x += deltaY * 0.005;
    targetRotation.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, targetRotation.x));
    
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });
  
  container.addEventListener('mouseup', () => { isDragging = false; });
  container.addEventListener('mouseleave', () => { 
    isDragging = false; 
    hideTooltip();
  });
  
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    e.stopPropagation();
    targetZoom += e.deltaY * 0.002;
    targetZoom = Math.max(1.5, Math.min(5, targetZoom));
  }, { passive: false });
  
  container.addEventListener('dblclick', (e) => {
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (lastClickTime > 0 && Date.now() - lastClickTime < 300) {
      const dist = Math.sqrt((x - lastClickPos.x) ** 2 + (y - lastClickPos.y) ** 2);
      if (dist < 50) {
        targetZoom = Math.max(1.5, targetZoom - 0.8);
      }
    }
    targetZoom = Math.min(5, targetZoom + 0.8);
    lastClickTime = Date.now();
    lastClickPos = { x, y };
  });
  
  container.addEventListener('touchstart', (e) => {
    if (e.target === renderer.domElement) {
      if (e.touches.length === 1) {
        isDragging = true;
        previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        isDragging = false;
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        touchStartDistance = Math.sqrt(dx * dx + dy * dy);
        pinchCenter = {
          x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          y: (e.touches[0].clientY + e.touches[1].clientY) / 2
        };
      }
    }
  }, { passive: false });
  
  container.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (e.touches.length === 1 && isDragging && !isFlyingTo) {
      const deltaX = e.touches[0].clientX - previousMousePosition.x;
      const deltaY = e.touches[0].clientY - previousMousePosition.y;
      
      targetRotation.y += deltaX * 0.005;
      targetRotation.x += deltaY * 0.005;
      targetRotation.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, targetRotation.x));
      
      previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const scale = distance / touchStartDistance;
      
      targetZoom = Math.max(1.5, Math.min(5, targetZoom * (1 + (scale - 1) * 0.3)));
      touchStartDistance = distance;
    }
  }, { passive: false });
  
  container.addEventListener('touchend', () => { isDragging = false; });
  
  container.addEventListener('click', onGlobeClick);
  container.addEventListener('touchend', (e) => {
    if (!isDragging && e.changedTouches.length > 0) {
      const touch = e.changedTouches[0];
      onGlobeClick({ clientX: touch.clientX, clientY: touch.clientY });
    }
  });
  
  document.addEventListener('keydown', onKeyDown);
  window.addEventListener('resize', onWindowResize);
}

function onGlobeClick(event) {
  if (isDragging) return;
  
  const container = document.getElementById('globe-container');
  const rect = container.getBoundingClientRect();
  
  const mouse = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  );
  
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera);
  
  const allMarkers = [...Object.values(eventMarkers), ...Object.values(hotspots)];
  
  if (allMarkers.length > 0) {
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
  
  const globeIntersect = raycaster.intersectObject(globe);
  if (globeIntersect.length > 0) {
    const point = globeIntersect[0].point;
    const lat = 90 - Math.acos(point.y) * 180 / Math.PI;
    const lng = Math.atan2(point.z, -point.x) * 180 / Math.PI - 180;
    
    const nearestRegion = findNearestRegion(lat, lng);
    if (nearestRegion) {
      window.dispatchEvent(new CustomEvent('regionSelected', { detail: nearestRegion }));
    }
  }
}

function findNearestRegion(lat, lng) {
  let nearest = null;
  let minDist = Infinity;
  
  const regionData = window.regions || {};
  const regionList = Array.isArray(regionData) ? regionData : Object.values(regionData || {});
  for (const region of regionList) {
    if (!region || !region.lat || !region.lng) continue;
    const dist = Math.sqrt((lat - region.lat) ** 2 + (lng - region.lng) ** 2);
    if (dist < minDist) {
      minDist = dist;
      nearest = region;
    }
  }
  
  return nearest;
}

function selectRegion(lat, lng, animate = true) {
  if (animate) {
    flyTo(lat, lng, 2.0);
  } else {
    const pos = latLngToVector3(lat, lng);
    targetRotation.y = Math.atan2(pos.x, pos.z) + Math.PI;
    targetRotation.x = Math.asin(pos.y) * 0.5;
    targetZoom = 2.0;
  }
}

function flyTo(lat, lng, zoomLevel = 2.0, duration = 1000) {
  const pos = latLngToVector3(lat, lng);
  
  isFlyingTo = true;
  flightTarget = { lat, lng, zoom: zoomLevel };
  flightStartRotation = { x: globeRotation.x, y: globeRotation.y };
  flightStartZoom = zoom;
  flightStartTime = Date.now();
  flightDuration = duration;
  
  const targetY = Math.atan2(pos.x, pos.z) + Math.PI;
  const targetX = Math.asin(pos.y) * 0.5;
  
  flightTarget.rotation = { x: targetX, y: targetY };
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function onKeyDown(e) {
  const ROTATION_SPEED = 0.08;
  const ZOOM_SPEED = 0.3;
  
  switch(e.key) {
    case 'ArrowLeft':
      targetRotation.y -= ROTATION_SPEED;
      break;
    case 'ArrowRight':
      targetRotation.y += ROTATION_SPEED;
      break;
    case 'ArrowUp':
      targetRotation.x = Math.max(-Math.PI / 2.5, targetRotation.x - ROTATION_SPEED);
      break;
    case 'ArrowDown':
      targetRotation.x = Math.min(Math.PI / 2.5, targetRotation.x + ROTATION_SPEED);
      break;
    case '+':
    case '=':
      targetZoom = Math.max(1.5, targetZoom - ZOOM_SPEED);
      break;
    case '-':
      targetZoom = Math.min(5, targetZoom + ZOOM_SPEED);
      break;
    case 'Home':
      targetRotation = { x: 0.1, y: 0 };
      targetZoom = 2.5;
      break;
  }
}

function createTooltip() {
  tooltipEl = document.createElement('div');
  tooltipEl.className = 'globe-tooltip';
  tooltipEl.style.cssText = `
    position: absolute;
    background: rgba(17, 24, 39, 0.95);
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
    color: #f1f5f9;
    pointer-events: none;
    z-index: 1000;
    display: none;
    max-width: 250px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    backdrop-filter: blur(8px);
  `;
  document.getElementById('globe-container').appendChild(tooltipEl);
}

function showTooltip(x, y, content) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = content;
  tooltipEl.style.display = 'block';
  tooltipEl.style.left = (x + 15) + 'px';
  tooltipEl.style.top = (y + 15) + 'px';
}

function hideTooltip() {
  if (!tooltipEl) return;
  tooltipEl.style.display = 'none';
}

function checkHover(clientX, clientY) {
  const container = document.getElementById('globe-container');
  const rect = container.getBoundingClientRect();
  
  const mouse = new THREE.Vector2(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1
  );
  
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera);
  
  const allMarkers = [...Object.values(eventMarkers), ...Object.values(hotspots)];
  
  if (allMarkers.length > 0) {
    const intersects = raycaster.intersectObjects(allMarkers, true);
    
    if (intersects.length > 0) {
      let obj = intersects[0].object;
      while (obj.parent && obj.parent !== globe) {
        obj = obj.parent;
      }
      
      if (obj.userData.eventId) {
        const event = obj.userData.event;
        showTooltip(clientX, clientY, `
          <div style="font-weight: 600; margin-bottom: 4px;">${event.title || 'Event'}</div>
          <div style="color: #64748b; font-size: 11px;">
            ${event.category} • ${event.severity}
          </div>
        `);
        container.style.cursor = 'pointer';
        return;
      }
      
      if (obj.userData.regionCode) {
        const region = obj.userData.region;
        showTooltip(clientX, clientY, `
          <div style="font-weight: 600; margin-bottom: 4px;">${region.name}</div>
          <div style="color: #64748b; font-size: 11px;">
            Risk Score: ${region.score || 0}
          </div>
        `);
        container.style.cursor = 'pointer';
        return;
      }
    }
  }
  
  hideTooltip();
  container.style.cursor = 'grab';
}

function createMinimap() {
  const minimapContainer = document.createElement('div');
  minimapContainer.className = 'minimap-container';
  minimapContainer.style.cssText = `
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 150px;
    height: 150px;
    border: 1px solid #374151;
    border-radius: 8px;
    background: rgba(17, 24, 39, 0.9);
    overflow: hidden;
    z-index: 100;
  `;
  
  minimapCanvas = document.createElement('canvas');
  minimapCanvas.width = 150;
  minimapCanvas.height = 150;
  minimapCtx = minimapCanvas.getContext('2d');
  
  minimapContainer.appendChild(minimapCanvas);
  document.getElementById('globe-container').appendChild(minimapContainer);
}

function updateMinimap() {
  if (!minimapCtx) return;
  
  const w = minimapCanvas.width;
  const h = minimapCanvas.height;
  
  minimapCtx.fillStyle = '#0a0e17';
  minimapCtx.fillRect(0, 0, w, h);
  
  minimapCtx.strokeStyle = '#1f2937';
  minimapCtx.lineWidth = 0.5;
  
  for (let i = 0; i < w; i += 15) {
    minimapCtx.beginPath();
    minimapCtx.moveTo(i, 0);
    minimapCtx.lineTo(i, h);
    minimapCtx.stroke();
  }
  for (let i = 0; i < h; i += 15) {
    minimapCtx.beginPath();
    minimapCtx.moveTo(0, i);
    minimapCtx.lineTo(w, i);
    minimapCtx.stroke();
  }
  
  const centerX = w / 2;
  const centerY = h / 2;
  
  minimapCtx.beginPath();
  minimapCtx.arc(centerX, centerY, 30, 0, Math.PI * 2);
  minimapCtx.fillStyle = '#1e3a5f';
  minimapCtx.fill();
  minimapCtx.strokeStyle = '#3b82f6';
  minimapCtx.lineWidth = 1;
  minimapCtx.stroke();
  
  const viewScale = (5 - zoom) / 3.5;
  minimapCtx.beginPath();
  minimapCtx.arc(centerX, centerY, 20 * viewScale, 0, Math.PI * 2);
  minimapCtx.fillStyle = 'rgba(59, 130, 246, 0.2)';
  minimapCtx.fill();
  
  const markerAngle = -globeRotation.y;
  const markerDist = 30;
  const mx = centerX + Math.sin(markerAngle) * markerDist;
  const my = centerY - Math.cos(markerAngle) * markerDist;
  
  minimapCtx.beginPath();
  minimapCtx.arc(mx, my, 4, 0, Math.PI * 2);
  minimapCtx.fillStyle = '#ef4444';
  minimapCtx.fill();
  
  Object.values(eventMarkers).forEach(marker => {
    const event = marker.userData.event;
    if (!event || event.lat === undefined) return;
    
    const lngNorm = (event.lng + 180) / 360;
    const latNorm = (90 - event.lat) / 180;
    
    const ex = lngNorm * w;
    const ey = latNorm * h;
    
    const dist = Math.sqrt((ex - centerX) ** 2 + (ey - centerY) ** 2);
    if (dist < 40) {
      const severityColors = {
        'critical': '#ef4444',
        'high': '#f97316',
        'medium': '#f59e0b',
        'low': '#3b82f6'
      };
      minimapCtx.beginPath();
      minimapCtx.arc(ex, ey, 2, 0, Math.PI * 2);
      minimapCtx.fillStyle = severityColors[event.severity] || '#10b981';
      minimapCtx.fill();
    }
  });
}

function updateSunPosition() {
  if (!sunLight) return;
  
  const now = new Date();
  const hour = now.getUTCHours() + now.getUTCMinutes() / 60;
  
  const angle = (hour / 24) * Math.PI * 2 - Math.PI / 2;
  
  const sunX = Math.cos(angle) * 5;
  const sunZ = Math.sin(angle) * 5;
  
  sunLight.position.set(sunX, 2, sunZ);
}

function createFlightPath(startLat, startLng, endLat, endLng, predictions = []) {
  const points = [];
  const steps = 50;
  
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    
    const lat = startLat + (endLat - startLat) * t;
    const lng = startLng + (endLng - startLng) * t;
    const altitude = Math.sin(t * Math.PI) * 0.5;
    
    const pos = latLngToVector3(lat, lng, 1 + altitude);
    points.push(pos);
  }
  
  const curve = new THREE.CatmullRomCurve3(points);
  const tubeGeometry = new THREE.TubeGeometry(curve, 64, 0.003, 8, false);
  const tubeMaterial = new THREE.MeshBasicMaterial({
    color: 0xf97316,
    transparent: true,
    opacity: 0.6
  });
  
  const path = new THREE.Mesh(tubeGeometry, tubeMaterial);
  scene.add(path);
  
  const sphereGeo = new THREE.SphereGeometry(0.015, 16, 16);
  const sphereMat = new THREE.MeshBasicMaterial({ color: 0xf97316 });
  const sphere = new THREE.Mesh(sphereGeo, sphereMat);
  scene.add(sphere);
  
  const progress = { t: 0 };
  flightPaths.push({ path, sphere, progress, predictions, startLat, endLat, startLng, endLng });
}

function updateFlightPaths(time) {
  flightPaths.forEach(fp => {
    fp.t += 0.005;
    if (fp.t > 1) fp.t = 0;
    
    const points = fp.path.geometry.parameters.path.points;
    const idx = Math.floor(fp.t * (points.length - 1));
    const pos = points[Math.min(idx, points.length - 1)];
    
    fp.sphere.position.copy(pos);
  });
}

function clusterMarkers() {
  const zoomLevel = Math.round((5 - zoom) * 2);
  
  if (zoomLevel >= 3) {
    Object.values(eventMarkers).forEach(m => m.visible = true);
    return;
  }
  
  const threshold = 0.05 / (zoomLevel + 1);
  
  Object.values(eventMarkers).forEach(m => m.visible = true);
  
  const markersArray = Object.entries(eventMarkers);
  
  for (let i = 0; i < markersArray.length; i++) {
    const [id1, m1] = markersArray[i];
    if (!m1.visible) continue;
    
    const lat1 = m1.userData.event?.lat || 0;
    const lng1 = m1.userData.event?.lng || 0;
    
    for (let j = i + 1; j < markersArray.length; j++) {
      const [id2, m2] = markersArray[j];
      if (!m2.visible) continue;
      
      const lat2 = m2.userData.event?.lat || 0;
      const lng2 = m2.userData.event?.lng || 0;
      
      const dist = Math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2);
      
      if (dist < threshold * 20) {
        m2.visible = false;
      }
    }
  }
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  animationId = requestAnimationFrame(animate);
  
  if (isFlyingTo && flightTarget) {
    const elapsed = Date.now() - flightStartTime;
    const progress = Math.min(elapsed / flightDuration, 1);
    const eased = easeInOutCubic(progress);
    
    targetRotation.x = flightStartRotation.x + (flightTarget.rotation.x - flightStartRotation.x) * eased;
    targetRotation.y = flightStartRotation.y + (flightTarget.rotation.y - flightStartRotation.y) * eased;
    targetZoom = flightStartZoom + (flightTarget.zoom - flightStartZoom) * eased;
    
    if (progress >= 1) {
      isFlyingTo = false;
      flightTarget = null;
    }
  }
  
  globeRotation.x += (targetRotation.x - globeRotation.x) * 0.08;
  globeRotation.y += (targetRotation.y - globeRotation.y) * 0.08;
  
  globe.rotation.x = globeRotation.x;
  globe.rotation.y = globeRotation.y;
  
  zoom += (targetZoom - zoom) * 0.08;
  camera.position.z = zoom;
  
  const time = Date.now() * 0.001;
  
  Object.values(eventMarkers).forEach(marker => {
    if (!marker.visible) return;
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
  
  updateFlightPaths(time);
  updateMinimap();
  clusterMarkers();
  updateAtmosphere();
  
  renderer.render(scene, camera);
}

function loadEvents(events, animate = false) {
  if (animate) {
    const currentIds = new Set(Object.keys(eventMarkers));
    const newIds = new Set(events.map(e => e.id));
    
    events.forEach(event => {
      if (!currentIds.has(event.id)) {
        addEventMarker(event);
        animateMarkerIn(event.id);
      }
    });
    
    currentIds.forEach(id => {
      if (!newIds.has(id)) {
        const marker = eventMarkers[id];
        if (marker) {
          animateMarkerOut(id, () => {
            globe.remove(eventMarkers[id]);
            delete eventMarkers[id];
          });
        }
      }
    });
  } else {
    clearEventMarkers();
    events.forEach(event => addEventMarker(event));
  }
}

function animateMarkerIn(eventId) {
  const marker = eventMarkers[eventId];
  if (!marker) return;
  
  marker.scale.set(0, 0, 0);
  const startTime = Date.now();
  const duration = 500;
  
  function animate() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    
    marker.scale.set(eased, eased, eased);
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }
  animate();
}

function animateMarkerOut(eventId, callback) {
  const marker = eventMarkers[eventId];
  if (!marker) {
    callback();
    return;
  }
  
  const startTime = Date.now();
  const duration = 300;
  const startScale = marker.scale.x;
  
  function animate() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(progress, 2);
    
    marker.scale.set(startScale * eased, startScale * eased, startScale * eased);
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    } else {
      callback();
    }
  }
  animate();
}

function loadHotspots(regions) {
  clearHotspots();
  regions.forEach(region => {
    if (region.score >= 10) {
      addHotspotMarker(region);
    }
  });
}

function addFlightPath(startLat, startLng, endLat, endLng) {
  createFlightPath(startLat, startLng, endLat, endLng);
}

window.globeAPI = {
  loadEvents,
  loadHotspots,
  selectRegion,
  flyTo,
  addFlightPath,
  latLngToVector3,
  setMode(mode) {
    currentMode = mode;
    
    if (mode === 'night' && nightTexture) {
      globe.material.map = nightTexture;
      globe.material.normalMap = null;
      globe.material.bumpMap = null;
      globe.material.needsUpdate = true;
    } else if ((mode === 'day' || mode === 'cloud') && globeTexture) {
      globe.material.map = globeTexture;
      if (normalMapTexture) {
        globe.material.normalMap = normalMapTexture;
      }
      if (bathymetryTexture) {
        globe.material.bumpMap = bathymetryTexture;
      }
      globe.material.needsUpdate = true;
    }
    
    if (cloudLayer) {
      cloudLayer.visible = (mode === 'cloud') || (mode === 'day');
    }
  },
  zoomIn() {
    targetZoom = Math.max(1.5, targetZoom - 0.5);
  },
  zoomOut() {
    targetZoom = Math.min(5, targetZoom + 0.5);
  },
  resetView() {
    targetRotation = { x: 0.1, y: 0 };
    targetZoom = 2.5;
  },
  getZoom() {
    return zoom;
  },
  isAnimating() {
    return isFlyingTo;
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
