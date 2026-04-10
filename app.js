let scene, camera, renderer, globe, markers = {}, controls;
let selectedConnection = null;
let animationId;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };
let globeRotation = { x: 0.23, y: 0 };
let targetRotation = { x: 0.23, y: 0 };
let zoom = 2.5;
let targetZoom = 2.5;

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
  createGridLines();
  
  setupEventListeners();
  animate();
}

function createStarfield() {
  const starsGeometry = new THREE.BufferGeometry();
  const starCount = 2000;
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
    size: 0.5,
    transparent: true,
    opacity: 0.8
  });
  
  const stars = new THREE.Points(starsGeometry, starsMaterial);
  scene.add(stars);
}

function createGlobe() {
  const geometry = new THREE.SphereGeometry(1, 64, 64);
  
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  
  const gradient = ctx.createLinearGradient(0, 0, 0, 256);
  gradient.addColorStop(0, '#0a1628');
  gradient.addColorStop(0.5, '#0d1f35');
  gradient.addColorStop(1, '#081018');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 512, 256);
  
  drawContinents(ctx);
  
  const texture = new THREE.CanvasTexture(canvas);
  
  const material = new THREE.MeshPhongMaterial({
    map: texture,
    emissive: 0x112244,
    emissiveIntensity: 0.3,
    shininess: 10,
    transparent: true,
    opacity: 0.95
  });
  
  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);
  
  const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
  scene.add(ambientLight);
  
  const sunLight = new THREE.DirectionalLight(0xffffff, 1);
  sunLight.position.set(5, 3, 5);
  scene.add(sunLight);
  
  const blueLight = new THREE.DirectionalLight(0x00b8ff, 0.3);
  blueLight.position.set(-5, -3, -5);
  scene.add(blueLight);
}

function drawContinents(ctx) {
  ctx.fillStyle = '#1a3a5c';
  
  const continents = [
    [[150, 80], [180, 90], [200, 85], [210, 100], [190, 120], [160, 110], [140, 90]],
    [[250, 70], [280, 60], [310, 70], [320, 90], [300, 110], [270, 100], [250, 85]],
    [[380, 100], [420, 90], [450, 110], [440, 130], [400, 140], [370, 120]],
    [[80, 140], [120, 130], [140, 150], [120, 170], [90, 160], [70, 150]],
    [[200, 140], [240, 130], [260, 150], [240, 170], [210, 160]],
    [[320, 160], [360, 150], [380, 170], [350, 180], [310, 170]]
  ];
  
  continents.forEach(cont => {
    ctx.beginPath();
    ctx.moveTo(cont[0][0], cont[0][1]);
    cont.slice(1).forEach(p => ctx.lineTo(p[0], p[1]));
    ctx.closePath();
    ctx.fill();
  });
}

function createGridLines() {
  const gridMaterial = new THREE.LineBasicMaterial({ 
    color: 0x00ff9d, 
    transparent: true, 
    opacity: 0.15 
  });
  
  for (let i = 0; i < 18; i++) {
    const theta = (i / 18) * Math.PI * 2;
    const points = [];
    for (let j = -80; j <= 80; j += 10) {
      const lat = j * Math.PI / 180;
      const x = Math.cos(lat) * Math.cos(theta) * 1.002;
      const y = Math.sin(lat) * 1.002;
      const z = Math.cos(lat) * Math.sin(theta) * 1.002;
      points.push(new THREE.Vector3(x, y, z));
    }
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geometry, gridMaterial);
    scene.add(line);
  }
  
  for (let i = 0; i < 8; i++) {
    const lat = (i - 4) * 20 * Math.PI / 180;
    const points = [];
    for (let j = 0; j <= 360; j += 5) {
      const lng = j * Math.PI / 180;
      const x = Math.cos(lat) * Math.cos(lng) * 1.002;
      const y = Math.sin(lat) * 1.002;
      const z = Math.cos(lat) * Math.sin(lng) * 1.002;
      points.push(new THREE.Vector3(x, y, z));
    }
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geometry, gridMaterial);
    scene.add(line);
  }
}

function latLngToVector3(lat, lng) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lng + 180) * Math.PI / 180;
  
  const x = -(Math.sin(phi) * Math.cos(theta));
  const z = Math.sin(phi) * Math.sin(theta);
  const y = Math.cos(phi);
  
  return new THREE.Vector3(x, y, z);
}

function addMarker(connection) {
  const pos = latLngToVector3(connection.lat, connection.lng);
  
  let color = 0x00ff9d;
  if (connection.status === 'warning') color = 0xffaa00;
  if (connection.status === 'offline') color = 0xff3366;
  
  const markerGroup = new THREE.Group();
  markerGroup.position.copy(pos);
  markerGroup.userData = { connectionId: connection.id };
  
  const sphereGeo = new THREE.SphereGeometry(0.03, 16, 16);
  const sphereMat = new THREE.MeshBasicMaterial({ 
    color: color,
    transparent: true,
    opacity: 0.9
  });
  const sphere = new THREE.Mesh(sphereGeo, sphereMat);
  markerGroup.add(sphere);
  
  const glowGeo = new THREE.SphereGeometry(0.06, 16, 16);
  const glowMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.2
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  markerGroup.add(glow);
  
  const ringGeo = new THREE.RingGeometry(0.04, 0.06, 32);
  const ringMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.4,
    side: THREE.DoubleSide
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.lookAt(new THREE.Vector3(0, 0, 0));
  ring.userData.isRing = true;
  ring.userData.baseOpacity = 0.4;
  markerGroup.add(ring);
  
  globe.add(markerGroup);
  markers[connection.id] = markerGroup;
}

function updateMarkerStatus(connectionId, status) {
  const markerGroup = markers[connectionId];
  if (!markerGroup) return;
  
  let color = 0x00ff9d;
  if (status === 'warning') color = 0xffaa00;
  if (status === 'offline') color = 0xff3366;
  
  markerGroup.children.forEach(child => {
    if (child.material) {
      child.material.color.setHex(color);
    }
  });
}

function removeMarker(connectionId) {
  const markerGroup = markers[connectionId];
  if (markerGroup) {
    globe.remove(markerGroup);
    delete markers[connectionId];
  }
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
    targetRotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, targetRotation.x));
    
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
  
  const intersects = raycaster.intersectObjects(globe.children, true);
  
  let foundConnection = null;
  
  for (let intersect of intersects) {
    let obj = intersect.object;
    while (obj.parent && obj.parent !== globe) {
      obj = obj.parent;
    }
    if (obj.userData && obj.userData.connectionId) {
      foundConnection = obj.userData.connectionId;
      break;
    }
  }
  
  if (foundConnection) {
    selectConnection(foundConnection);
  }
}

function selectConnection(connectionId) {
  selectedConnection = connectionId;
  
  document.querySelectorAll('.connection-item').forEach(el => {
    el.classList.remove('selected');
    if (el.dataset.id === connectionId) {
      el.classList.add('selected');
    }
  });
  
  const marker = markers[connectionId];
  if (marker) {
    const pos = marker.position.clone().normalize();
    targetRotation.y = Math.atan2(pos.x, pos.z);
    targetRotation.x = Math.asin(pos.y) * 0.5;
    targetZoom = 1.8;
  }
  
  window.dispatchEvent(new CustomEvent('connectionSelected', { detail: connectionId }));
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  animationId = requestAnimationFrame(animate);
  
  globeRotation.x += (targetRotation.x - globeRotation.x) * 0.1;
  globeRotation.y += (targetRotation.y - globeRotation.y) * 0.1;
  
  globe.rotation.x = globeRotation.x;
  globe.rotation.y = globeRotation.y;
  
  zoom += (targetZoom - zoom) * 0.1;
  camera.position.z = zoom;
  
  Object.values(markers).forEach(marker => {
    marker.children.forEach(child => {
      if (child.userData.isRing) {
        child.rotation.z += 0.01;
        const pulse = 0.3 + Math.sin(Date.now() * 0.003) * 0.2;
        child.material.opacity = pulse;
      }
    });
  });
  
  renderer.render(scene, camera);
}

function loadConnections(connections) {
  Object.values(markers).forEach(m => globe.remove(m));
  markers = {};
  
  connections.forEach(conn => addMarker(conn));
}

function updateConnectionStatus(connectionId, status) {
  if (markers[connectionId]) {
    updateMarkerStatus(connectionId, status);
  }
}

window.globeAPI = {
  loadConnections,
  selectConnection,
  updateConnectionStatus
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}