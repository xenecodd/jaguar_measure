import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

function ThreeDTrace({ containerRef }) {
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      60, 
      container.clientWidth / container.clientHeight, 
      0.1, 
      1000
    );
    camera.position.set(0, 200, 300);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Basic lighting
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);

    // Add a grid helper
    const gridSize = 300;
    const gridDivisions = 30;
    const gridHelper = new THREE.GridHelper(gridSize, gridDivisions);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Add axes helper
    const axesHelper = new THREE.AxesHelper(100);
    scene.add(axesHelper);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls setup
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle window resize
    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeChild(renderer.domElement);
      renderer.dispose();
      controls.dispose();
    };
  }, [containerRef]);

  return null;
}

export default ThreeDTrace;