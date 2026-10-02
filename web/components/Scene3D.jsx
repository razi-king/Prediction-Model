"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Futuristic 3D background (Three.js / WebGL), fixed behind the whole app.
 *
 *  - a glowing wireframe crystal (icosahedron) = the "core" of DevAscend
 *  - three tilted orbit rings around it
 *  - a star field of particles in DevAscend's cyan / violet colours
 *  - "ascend" particles that keep rising upward (growth!)
 *  - a perspective grid floor
 *
 * The camera follows the mouse a little (parallax) and the scene drifts as you scroll.
 * Performance & accessibility: animation pauses when the tab is hidden, and with
 * "reduce motion" turned on in the OS only ONE still frame is drawn.
 */
export default function Scene3D() {
  const mountRef = useRef(null);
  const [fallback, setFallback] = useState(false); // true when the browser has no WebGL

  useEffect(() => {
    let disposed = false;
    let cleanup = () => {};

    // three is imported inside useEffect so it only ever runs in the browser (never on the server)
    import("three").then((THREE) => {
      if (disposed || !mountRef.current) return;
      const mount = mountRef.current;
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      // ---------- renderer, scene, camera ----------
      // Check for WebGL first (quietly), so three.js never has to fail loudly
      const probe = document.createElement("canvas");
      if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) {
        setFallback(true);
        return;
      }
      let renderer;
      try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      } catch {
        // WebGL disabled or unsupported (old GPU, locked-down PC): show the CSS version instead
        setFallback(true);
        return;
      }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      mount.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      scene.fog = new THREE.FogExp2(0x070b18, 0.045);
      const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
      camera.position.set(0, 0.6, 9);

      const CYAN = new THREE.Color("#3dd9eb");
      const VIOLET = new THREE.Color("#9b8cff");

      // ---------- the crystal ----------
      const core = new THREE.Group();
      const crystalGeo = new THREE.IcosahedronGeometry(1.6, 1);
      const wire = new THREE.LineSegments(
        new THREE.WireframeGeometry(crystalGeo),
        new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.85 })
      );
      const inner = new THREE.Mesh(
        new THREE.IcosahedronGeometry(1.05, 0),
        new THREE.MeshBasicMaterial({ color: VIOLET, transparent: true, opacity: 0.22 })
      );
      const glow = new THREE.Mesh(
        new THREE.SphereGeometry(2.3, 32, 32),
        new THREE.MeshBasicMaterial({ color: CYAN, transparent: true, opacity: 0.05 })
      );
      core.add(wire, inner, glow);

      // ---------- orbit rings ----------
      const rings = [2.6, 3.2, 3.9].map((radius, i) => {
        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(radius, 0.012, 8, 180),
          new THREE.MeshBasicMaterial({ color: i === 1 ? VIOLET : CYAN, transparent: true, opacity: 0.55 - i * 0.12 })
        );
        ring.rotation.x = Math.PI / 2.3 + i * 0.35;
        ring.rotation.y = i * 0.6;
        core.add(ring);
        return ring;
      });
      // small "satellites" riding on the rings
      const satellites = rings.map((ring, i) => {
        const s = new THREE.Mesh(
          new THREE.SphereGeometry(0.07, 12, 12),
          new THREE.MeshBasicMaterial({ color: i === 1 ? VIOLET : CYAN })
        );
        ring.add(s);
        return s;
      });

      core.position.set(3.2, 0.4, 0);
      scene.add(core);

      // ---------- star field ----------
      const STARS = 2200;
      const starPos = new Float32Array(STARS * 3);
      const starCol = new Float32Array(STARS * 3);
      for (let i = 0; i < STARS; i++) {
        const r = 12 + Math.random() * 40;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        starPos.set([r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi) * 0.6, r * Math.sin(phi) * Math.sin(theta) - 10], i * 3);
        const c = Math.random() < 0.7 ? CYAN : VIOLET;
        starCol.set([c.r, c.g, c.b], i * 3);
      }
      const starGeo = new THREE.BufferGeometry();
      starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
      starGeo.setAttribute("color", new THREE.BufferAttribute(starCol, 3));
      const stars = new THREE.Points(
        starGeo,
        new THREE.PointsMaterial({ size: 0.06, vertexColors: true, transparent: true, opacity: 0.8, depthWrite: false })
      );
      scene.add(stars);

      // ---------- ascending particles (growth) ----------
      const RISE = 420;
      const risePos = new Float32Array(RISE * 3);
      const riseSpeed = new Float32Array(RISE);
      for (let i = 0; i < RISE; i++) {
        const a = Math.random() * Math.PI * 2;
        const r = 0.4 + Math.random() * 2.2;
        risePos.set([Math.cos(a) * r, -6 + Math.random() * 12, Math.sin(a) * r], i * 3);
        riseSpeed[i] = 0.004 + Math.random() * 0.012;
      }
      const riseGeo = new THREE.BufferGeometry();
      riseGeo.setAttribute("position", new THREE.BufferAttribute(risePos, 3));
      const rising = new THREE.Points(
        riseGeo,
        new THREE.PointsMaterial({ size: 0.05, color: CYAN, transparent: true, opacity: 0.9, depthWrite: false })
      );
      rising.position.copy(core.position);
      scene.add(rising);

      // ---------- grid floor ----------
      const grid = new THREE.GridHelper(80, 80, 0x3dd9eb, 0x1c2b52);
      grid.material.transparent = true;
      grid.material.opacity = 0.35;
      grid.position.y = -3.2;
      scene.add(grid);

      // ---------- interaction ----------
      const mouse = { x: 0, y: 0 };
      const onMove = (e) => {
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = (e.clientY / window.innerHeight) * 2 - 1;
      };
      const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        // on narrow screens put the crystal in the middle, behind the content
        core.position.x = window.innerWidth < 900 ? 0 : 3.2;
        rising.position.x = core.position.x;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        if (reduceMotion) renderer.render(scene, camera);
      };
      window.addEventListener("pointermove", onMove);
      window.addEventListener("resize", onResize);
      onResize();

      // ---------- animation loop ----------
      const startTime = performance.now();
      let frame = 0;
      const tick = () => {
        frame = requestAnimationFrame(tick);
        if (document.hidden) return; // save battery when the tab is not visible
        const t = (performance.now() - startTime) / 1000; // seconds since start

        wire.rotation.y = t * 0.25;
        wire.rotation.x = t * 0.12;
        inner.rotation.y = -t * 0.4;
        inner.scale.setScalar(1 + Math.sin(t * 2) * 0.06); // "breathing" core
        rings.forEach((ring, i) => { ring.rotation.z = t * (0.15 + i * 0.08) * (i % 2 ? -1 : 1); });
        satellites.forEach((s, i) => {
          const r = rings[i].geometry.parameters.radius;
          const a = t * (0.6 + i * 0.25);
          s.position.set(Math.cos(a) * r, Math.sin(a) * r, 0);
        });
        core.position.y = 0.4 + Math.sin(t * 0.8) * 0.15;

        const p = riseGeo.attributes.position.array;
        for (let i = 0; i < RISE; i++) {
          p[i * 3 + 1] += riseSpeed[i];
          if (p[i * 3 + 1] > 6) p[i * 3 + 1] = -6;
        }
        riseGeo.attributes.position.needsUpdate = true;

        stars.rotation.y = t * 0.01;
        grid.position.z = (t * 0.6) % 1; // floor slides towards the viewer

        // parallax: camera eases towards the mouse; page scroll lifts the scene
        const scroll = Math.min(window.scrollY / window.innerHeight, 2);
        camera.position.x += (mouse.x * 0.8 - camera.position.x) * 0.04;
        camera.position.y += (0.6 - mouse.y * 0.5 + scroll * 1.2 - camera.position.y) * 0.04;
        camera.lookAt(0, scroll * 1.2, 0);

        renderer.render(scene, camera);
      };
      if (reduceMotion) renderer.render(scene, camera);
      else tick();

      cleanup = () => {
        cancelAnimationFrame(frame);
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("resize", onResize);
        scene.traverse((obj) => {
          obj.geometry?.dispose();
          obj.material?.dispose();
        });
        renderer.dispose();
        renderer.domElement.remove();
      };
    });

    return () => {
      disposed = true;
      cleanup();
    };
  }, []);

  if (fallback) {
    // Pure-CSS stand-in: the same crystal + orbit rings, animated with CSS only
    return (
      <div className="scene3d scene3d--fallback" aria-hidden="true">
        <div className="fb-orbit fb-orbit-1" />
        <div className="fb-orbit fb-orbit-2" />
        <div className="fb-orbit fb-orbit-3" />
        <div className="fb-core" />
      </div>
    );
  }
  return <div ref={mountRef} className="scene3d" aria-hidden="true" />;
}
