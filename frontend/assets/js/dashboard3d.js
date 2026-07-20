export function initSalesFunnel(canvasId, stageData) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
  camera.position.set(0, 15, 25);
  camera.lookAt(0, 0, 0);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(10, 20, 10);
  scene.add(dirLight);

  let yOffset = 10;
  let topRadius = 6;
  const colors = [0x6366f1, 0x8b5cf6, 0x06b6d4, 0x10b981, 0xef4444];

  const group = new THREE.Group();
  
  // Create frustums
  const data = stageData || [
    { count: 100, name: 'New' },
    { count: 70, name: 'Contacted' },
    { count: 40, name: 'Qualified' },
    { count: 20, name: 'Proposal' },
    { count: 5, name: 'Sold' }
  ];

  data.forEach((d, i) => {
    const bottomRadius = topRadius * 0.7;
    const height = 3;
    const geometry = new THREE.CylinderGeometry(topRadius, bottomRadius, height, 32);
    const material = new THREE.MeshStandardMaterial({ 
      color: colors[i % colors.length], 
      metalness: 0.3,
      roughness: 0.4,
      transparent: true,
      opacity: 0.9
    });
    
    const cylinder = new THREE.Mesh(geometry, material);
    cylinder.position.y = yOffset;
    group.add(cylinder);

    // Text Sprite (mock)
    const canvas2d = document.createElement('canvas');
    canvas2d.width = 256; canvas2d.height = 64;
    const ctx = canvas2d.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.font = '24px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(`${d.name} (${d.count})`, 128, 32);
    
    const tex = new THREE.CanvasTexture(canvas2d);
    const spriteMat = new THREE.SpriteMaterial({ map: tex });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(topRadius + 2, yOffset, 0);
    sprite.scale.set(6, 1.5, 1);
    group.add(sprite);

    topRadius = bottomRadius;
    yOffset -= height + 0.1;
  });

  scene.add(group);

  function resize() {
    if(!canvas.parentElement) return;
    const w = canvas.parentElement.clientWidth;
    const h = canvas.parentElement.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  
  window.addEventListener('resize', resize);
  resize();

  function animate() {
    requestAnimationFrame(animate);
    group.rotation.y += 0.005;
    renderer.render(scene, camera);
  }
  animate();
}

export function initRevenueHeatmap(canvasId, heatmapData) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
  camera.position.set(15, 15, 15);
  camera.lookAt(0, 0, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.5);
  dirLight.position.set(5, 15, 5);
  scene.add(dirLight);

  const group = new THREE.Group();
  
  const rows = 4;
  const cols = 6;
  
  for(let r = 0; r < rows; r++) {
    for(let c = 0; c < cols; c++) {
      const val = Math.random() * 5 + 1;
      const geo = new THREE.BoxGeometry(1, val, 1);
      const mat = new THREE.MeshStandardMaterial({ 
        color: new THREE.Color().setHSL(0.7 - (val/6)*0.7, 1, 0.5),
        metalness: 0.5,
        roughness: 0.2
      });
      const box = new THREE.Mesh(geo, mat);
      box.position.set(c * 1.2 - (cols*1.2)/2, val/2, r * 1.2 - (rows*1.2)/2);
      group.add(box);
    }
  }

  scene.add(group);

  function resize() {
    if(!canvas.parentElement) return;
    const w = canvas.parentElement.clientWidth;
    const h = canvas.parentElement.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  
  window.addEventListener('resize', resize);
  resize();

  function animate() {
    requestAnimationFrame(animate);
    group.rotation.y += 0.002;
    renderer.render(scene, camera);
  }
  animate();
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('funnel-canvas')) {
    initSalesFunnel('funnel-canvas');
    initRevenueHeatmap('heatmap-canvas');
  }
});
