import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import PropTypes from 'prop-types';

function ThreeDTrace({ containerRef, tcpData }) {
  const sceneRef = useRef();
  const cameraRef = useRef();
  const rendererRef = useRef();
  const controlsRef = useRef();
  const pointsRef = useRef([]);
  const geometryRef = useRef();
  const lineRef = useRef();
  const testSphereRef = useRef();
  

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      60,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 200, 300);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    scene.add(new THREE.AxesHelper(100));
    scene.add(new THREE.GridHelper(300, 30));
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    
    // Line için yapı
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(0), 3));
    geometryRef.current = geometry;

    const material = new THREE.LineBasicMaterial({ color: 0xff0000 });
    const line = new THREE.Line(geometry, material);
    lineRef.current = line;
    scene.add(line);

    // Test küresi — pozisyonu son TCP noktasına gelecek
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(3, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0x00ff00 })
    );
    testSphereRef.current = sphere;
    scene.add(sphere);

    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeChild(renderer.domElement);
      renderer.dispose();
      controls.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, [containerRef]);

  // Gelen TCP verisi ile güncelle
  useEffect(() => {
    if (!tcpData || !geometryRef.current || !lineRef.current) {
      console.warn("tcpData yok veya sahne henüz hazır değil", tcpData);
      return;
    }

    const point = new THREE.Vector3(tcpData.x, tcpData.y, tcpData.z);
    pointsRef.current.push(point);

    if (pointsRef.current.length > 500) {
      pointsRef.current.shift();
    }

    const positions = new Float32Array(pointsRef.current.length * 3);
    pointsRef.current.forEach((p, i) => {
      positions.set([p.x, p.y, p.z], i * 3);
    });

    geometryRef.current.setAttribute(
      'position',
      new THREE.BufferAttribute(positions, 3)
    );
    geometryRef.current.setDrawRange(0, pointsRef.current.length);
    geometryRef.current.attributes.position.needsUpdate = true;

    // Test küresini son noktaya yerleştir
    if (testSphereRef.current) {
      testSphereRef.current.position.copy(point);
    }

  }, [tcpData]);

  return null;
}

ThreeDTrace.propTypes = {
  containerRef: PropTypes.object.isRequired,
  tcpData: PropTypes.shape({
    x: PropTypes.number,
    y: PropTypes.number,
    z: PropTypes.number,
  }),
};

export default ThreeDTrace;
