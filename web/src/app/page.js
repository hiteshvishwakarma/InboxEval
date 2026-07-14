"use client";

import React, { useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { Terminal, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';

import { PointerLockControls } from '@react-three/drei';

// --- FIRST PERSON PLAYER CONTROLLER ---
function Player() {
  const { camera } = useThree();
  const moveState = useRef({ forward: false, backward: false, left: false, right: false });
  const speed = 5;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'KeyW') moveState.current.forward = true;
      if (e.code === 'KeyS') moveState.current.backward = true;
      if (e.code === 'KeyA') moveState.current.left = true;
      if (e.code === 'KeyD') moveState.current.right = true;
    };
    const handleKeyUp = (e) => {
      if (e.code === 'KeyW') moveState.current.forward = false;
      if (e.code === 'KeyS') moveState.current.backward = false;
      if (e.code === 'KeyA') moveState.current.left = false;
      if (e.code === 'KeyD') moveState.current.right = false;
    };
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  useFrame((state, delta) => {
    const velocity = new THREE.Vector3();
    const direction = new THREE.Vector3();

    if (moveState.current.forward) velocity.z -= 1;
    if (moveState.current.backward) velocity.z += 1;
    if (moveState.current.left) velocity.x -= 1;
    if (moveState.current.right) velocity.x += 1;

    velocity.normalize();
    
    // Move relative to where the camera is looking
    direction.copy(velocity).applyQuaternion(camera.quaternion);
    direction.y = 0; // Prevent flying

    camera.position.addScaledVector(direction, speed * delta);
    
    // Hardcode a basic floor/wall collision boundary
    if (camera.position.y !== 2) camera.position.y = 2; // Fixed eye level
    if (camera.position.x > 14) camera.position.x = 14;
    if (camera.position.x < -14) camera.position.x = -14;
    if (camera.position.z > 14) camera.position.z = 14;
    if (camera.position.z < -14) camera.position.z = -14;
  });

  return <PointerLockControls />;
}

function FloppyDisk() {
  const [hovered, setHover] = useState(false);
  return (
    <group position={[-3.2, 0.55, 0.5]} onClick={(e) => { e.stopPropagation(); alert('Initiating Golden Dataset Download...'); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <boxGeometry args={[0.4, 0.4, 0.05]} />
        <meshStandardMaterial color={hovered ? "#00ffff" : "#333"} metalness={0.5} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[0.25, 0.2]} />
        <meshBasicMaterial color="#fff" />
      </mesh>
      {hovered && (
        <Html position={[0, 0.2, 0]} center>
          <div className="bg-black/80 text-cyan-400 font-mono text-[10px] p-1 border border-cyan-500 whitespace-nowrap">
            download_dataset.csv
          </div>
        </Html>
      )}
    </group>
  );
}

function AirVent({ lightsOn }) {
  const [hovered, setHover] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const isSecretRevealed = !lightsOn;

  return (
    <group position={[2, 0, 2]} onClick={(e) => { 
      if (!isSecretRevealed) return;
      e.stopPropagation(); 
      setUnlocked(true);
    }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.5, 1.5]} />
        <meshStandardMaterial color="#0a0a0a" wireframe={true} />
      </mesh>
      
      <mesh position={[0, -0.5, 0]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={isSecretRevealed ? "#ff0000" : "#000"} emissive={isSecretRevealed ? "#ff0000" : "#000"} emissiveIntensity={isSecretRevealed ? (hovered ? 5 : 2) : 0} />
      </mesh>

      {unlocked && isSecretRevealed && (
        <Html position={[0, 1, 0]} center>
          <div className="w-96 p-6 bg-red-950/90 border border-red-500 rounded text-red-500 font-mono text-sm text-center shadow-[0_0_50px_rgba(255,0,0,0.5)]">
            <h2 className="text-xl font-black mb-4">THE ARCHITECT'S TERMINAL</h2>
            <p className="mb-4">PRESS ESC TO UNLOCK MOUSE.</p>
            <p className="mb-4 text-xs">AWAITING CRYPTOGRAPHIC KEY...</p>
            <input type="password" placeholder="ENTER TOLERANCE..." className="w-full bg-black border border-red-500 text-red-500 p-2 text-center outline-none" />
            <button className="mt-4 border border-red-500 px-4 py-1 hover:bg-red-500 hover:text-black" onClick={() => setUnlocked(false)}>CLOSE</button>
          </div>
        </Html>
      )}
    </group>
  );
}

function ServerRack() {
  const [hovered, setHover] = useState(false);
  const [interacting, setInteracting] = useState(false);

  return (
    <group position={[4, 0, 0]} onClick={(e) => { e.stopPropagation(); setInteracting(true); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh position={[0, 1.5, 0]}>
        <boxGeometry args={[1.5, 3, 1]} />
        <meshStandardMaterial color="#111" metalness={0.8} roughness={0.2} />
      </mesh>
      
      {[0.5, 1.2, 1.9, 2.6].map((y, i) => (
        <mesh key={i} position={[0, y, 0.51]}>
          <boxGeometry args={[1.2, 0.2, 0.1]} />
          <meshStandardMaterial color={hovered ? "#00ffff" : "#005555"} emissive={hovered ? "#00ffff" : "#005555"} emissiveIntensity={2} />
        </mesh>
      ))}

      {interacting && (
        <Html position={[0, 1.5, 0.6]} transform distanceFactor={2}>
          <div className="w-64 p-4 bg-black/90 border border-cyan-500 rounded-lg text-cyan-400 font-mono text-xs">
            <div className="flex justify-between items-center mb-2 border-b border-cyan-900 pb-2">
              <span className="flex items-center gap-2"><Terminal size={14} /> MCP_SERVER</span>
              <button onClick={(e) => { e.stopPropagation(); setInteracting(false); }} className="text-red-500 hover:text-white">X</button>
            </div>
            <p className="text-green-400 mb-1">{'>'} STATUS: ONLINE</p>
            <p className="text-neutral-500 mb-1">{'>'} MISSING PHYSICAL PLIERS CONNECTION</p>
            <button className="w-full bg-cyan-900/50 hover:bg-cyan-500 hover:text-black border border-cyan-500 py-1 transition-colors mt-2">
              Initialize Socket
            </button>
          </div>
        </Html>
      )}
    </group>
  );
}

function Desk() {
  const [hovered, setHover] = useState(false);
  return (
    <group position={[-4, 0, 0]} onClick={(e) => { e.stopPropagation(); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[3, 0.1, 1.5]} />
        <meshStandardMaterial color="#222" metalness={0.5} roughness={0.8} />
      </mesh>
      <mesh position={[0, 1.2, -0.4]} rotation={[-0.1, 0, 0]}>
        <boxGeometry args={[1.8, 1.2, 0.05]} />
        <meshStandardMaterial color={hovered ? "#fff" : "#111"} emissive={hovered ? "#444" : "#000"} />
      </mesh>

      <FloppyDisk />

      <Html position={[0, 1.2, -0.3]} transform distanceFactor={1.5}>
        <div className="w-48 p-2 bg-black border border-white text-white font-mono text-center">
          <h3 className="mb-2 font-bold uppercase">Eval Arena</h3>
          <p className="text-[8px] text-neutral-500 mb-2">PRESS ESC TO UNLOCK MOUSE</p>
          <Link href="/arena" className="block w-full bg-white text-black py-1 hover:bg-cyan-400 transition-colors pointer-events-auto">
            ENTER
          </Link>
        </div>
      </Html>
    </group>
  );
}

function LightSwitch({ lightsOn, setLightsOn }) {
  const [hovered, setHover] = useState(false);
  return (
    <group position={[0, 2, -6]} onClick={(e) => { e.stopPropagation(); setLightsOn(!lightsOn); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh>
        <boxGeometry args={[0.4, 0.6, 0.1]} />
        <meshStandardMaterial color="#222" metalness={0.8} />
      </mesh>
      <mesh position={[0, lightsOn ? 0.1 : -0.1, 0.05]} rotation={[lightsOn ? -0.2 : 0.2, 0, 0]}>
        <boxGeometry args={[0.15, 0.3, 0.1]} />
        <meshStandardMaterial color={hovered ? "#fff" : "#888"} />
      </mesh>
      <mesh position={[0, 0.4, 0.05]}>
        <sphereGeometry args={[0.05, 8, 8]} />
        <meshStandardMaterial color={lightsOn ? "#00ff00" : "#ff0000"} emissive={lightsOn ? "#00ff00" : "#ff0000"} emissiveIntensity={2} />
      </mesh>
      {hovered && (
        <Html position={[0, -0.6, 0]} center>
          <div className="bg-black text-white font-mono text-xs p-1 border border-white">
            {lightsOn ? 'MAIN_BREAKER: ON' : 'MAIN_BREAKER: OFF'}
          </div>
        </Html>
      )}
    </group>
  );
}

export default function Home() {
  const [isClient, setIsClient] = useState(false);
  const [lightsOn, setLightsOn] = useState(true);

  useEffect(() => { setIsClient(true); }, []);
  if (!isClient) return <div className="min-h-screen bg-black" />;

  return (
    <div className="min-h-screen bg-[#050505] overflow-hidden relative">
      {/* 2D HUD / Crosshair */}
      <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-white/50 rounded-full -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none mix-blend-difference" />
      
      <div className="absolute top-0 left-0 w-full p-6 z-10 flex justify-between items-start pointer-events-none">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tighter">InboxEval</h1>
          <p className="text-neutral-500 font-mono text-xs">FPS SPATIAL UI PROTOTYPE v1.0</p>
        </div>
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 text-neutral-400 font-mono text-sm pointer-events-none text-center bg-black/50 p-2 rounded">
        <strong>WASD</strong> to Move | <strong>Click</strong> to Interact | <strong>ESC</strong> to Unlock Mouse
      </div>

      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 2, 8], fov: 60 }}>
          <color attach="background" args={['#050505']} />
          <ambientLight intensity={lightsOn ? 0.5 : 0.05} />
          {lightsOn && <spotLight position={[4, 8, 2]} angle={0.5} intensity={2} color="#00ffff" />}
          {lightsOn && <spotLight position={[-4, 6, 2]} angle={0.5} intensity={1} color="#ffffff" />}
          
          <gridHelper args={[30, 30, lightsOn ? '#00ffff' : '#111', '#111']} position={[0, -0.01, 0]} />
          
          <Player />
          <ServerRack />
          <Desk />
          <LightSwitch lightsOn={lightsOn} setLightsOn={setLightsOn} />
          <AirVent lightsOn={lightsOn} />
        </Canvas>
      </div>
    </div>
  );
}
