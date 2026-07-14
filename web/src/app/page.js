"use client";

import React, { useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { Terminal, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';

function CameraRig({ target }) {
  useFrame((state, delta) => {
    const positions = {
      overview: new THREE.Vector3(0, 4, 12),
      server: new THREE.Vector3(4, 2, 3),
      desk: new THREE.Vector3(-4, 1.5, 3),
    };
    const targets = {
      overview: new THREE.Vector3(0, 0, 0),
      server: new THREE.Vector3(4, 1, 0),
      desk: new THREE.Vector3(-4, 0.5, 0),
    };
    
    const step = 2.5 * delta;
    state.camera.position.lerp(positions[target], step);
    
    const dummyCamera = new THREE.PerspectiveCamera();
    dummyCamera.position.copy(state.camera.position);
    dummyCamera.lookAt(targets[target]);
    state.camera.quaternion.slerp(dummyCamera.quaternion, step);
  });
  return null;
}

function ServerRack({ onClick, isFocused }) {
  const [hovered, setHover] = useState(false);
  useEffect(() => { document.body.style.cursor = hovered ? 'pointer' : 'auto'; }, [hovered]);

  return (
    <group position={[4, 0, 0]} onClick={(e) => { e.stopPropagation(); onClick(); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      {/* Main Chassis */}
      <mesh position={[0, 1.5, 0]}>
        <boxGeometry args={[1.5, 3, 1]} />
        <meshStandardMaterial color="#111" metalness={0.8} roughness={0.2} />
      </mesh>
      
      {/* Glowing Server Blades */}
      {[0.5, 1.2, 1.9, 2.6].map((y, i) => (
        <mesh key={i} position={[0, y, 0.51]}>
          <boxGeometry args={[1.2, 0.2, 0.1]} />
          <meshStandardMaterial color={hovered ? "#00ffff" : "#005555"} emissive={hovered ? "#00ffff" : "#005555"} emissiveIntensity={2} />
        </mesh>
      ))}

      {isFocused && (
        <Html position={[0, 1.5, 0.6]} transform distanceFactor={2}>
          <div className="w-64 p-4 bg-black/90 border border-cyan-500 rounded-lg text-cyan-400 font-mono text-xs">
            <div className="flex items-center gap-2 mb-2 border-b border-cyan-900 pb-2">
              <Terminal size={14} /> MCP_SERVER
            </div>
            <p className="text-green-400 mb-1">{'>'} STATUS: ONLINE</p>
            <button className="w-full bg-cyan-900/50 hover:bg-cyan-500 hover:text-black border border-cyan-500 py-1 transition-colors mt-2">
              Initialize Socket
            </button>
          </div>
        </Html>
      )}
    </group>
  );
}

function Desk({ onClick, isFocused }) {
  const [hovered, setHover] = useState(false);
  useEffect(() => { document.body.style.cursor = hovered ? 'pointer' : 'auto'; }, [hovered]);

  return (
    <group position={[-4, 0, 0]} onClick={(e) => { e.stopPropagation(); onClick(); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[3, 0.1, 1.5]} />
        <meshStandardMaterial color="#222" metalness={0.5} roughness={0.8} />
      </mesh>
      <mesh position={[0, 1.2, -0.4]} rotation={[-0.1, 0, 0]}>
        <boxGeometry args={[1.8, 1.2, 0.05]} />
        <meshStandardMaterial color={hovered ? "#fff" : "#111"} emissive={hovered ? "#444" : "#000"} />
      </mesh>

      {isFocused && (
        <Html position={[0, 1.2, -0.3]} transform distanceFactor={1.5}>
          <div className="w-48 p-2 bg-black border border-white text-white font-mono text-center">
            <h3 className="mb-2 font-bold uppercase">Eval Arena</h3>
            <Link href="/arena" className="block w-full bg-white text-black py-1 hover:bg-cyan-400 transition-colors">
              ENTER
            </Link>
          </div>
        </Html>
      )}
    </group>
  );
}

function LightSwitch({ onClick, lightsOn }) {
  const [hovered, setHover] = useState(false);
  useEffect(() => { document.body.style.cursor = hovered ? 'pointer' : 'auto'; }, [hovered]);

  return (
    <group position={[0, 2, -6]} onClick={(e) => { e.stopPropagation(); onClick(); }} onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
      {/* Wall Box */}
      <mesh>
        <boxGeometry args={[0.4, 0.6, 0.1]} />
        <meshStandardMaterial color="#222" metalness={0.8} />
      </mesh>
      {/* The Switch Toggle */}
      <mesh position={[0, lightsOn ? 0.1 : -0.1, 0.05]} rotation={[lightsOn ? -0.2 : 0.2, 0, 0]}>
        <boxGeometry args={[0.15, 0.3, 0.1]} />
        <meshStandardMaterial color={hovered ? "#fff" : "#888"} />
      </mesh>
      {/* Status Light */}
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
  const [target, setTarget] = useState('overview');
  const [isClient, setIsClient] = useState(false);
  const [lightsOn, setLightsOn] = useState(true);

  useEffect(() => { setIsClient(true); }, []);
  if (!isClient) return <div className="min-h-screen bg-black" />;

  return (
    <div className="min-h-screen bg-[#050505] overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full p-6 z-10 flex justify-between items-start pointer-events-none">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tighter">InboxEval</h1>
          <p className="text-neutral-500 font-mono text-xs">SPATIAL UI PROTOTYPE v0.3</p>
        </div>
        
        <AnimatePresence>
          {target !== 'overview' && (
            <motion.button
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
              onClick={() => setTarget('overview')}
              className="pointer-events-auto flex items-center gap-2 bg-white text-black px-4 py-2 font-mono text-sm uppercase hover:bg-cyan-400 transition-colors"
            >
              <ArrowLeft size={16} /> Back to Room
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {target === 'overview' && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-12 left-1/2 -translate-x-1/2 z-10 text-neutral-400 font-mono text-sm pointer-events-none text-center"
          >
            Click an object to interact.<br/>
            <span className="text-xs opacity-50">Hint: Try the breaker switch on the back wall.</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 4, 12], fov: 45 }}>
          <color attach="background" args={['#050505']} />
          <ambientLight intensity={lightsOn ? 0.5 : 0.05} />
          {lightsOn && <spotLight position={[4, 8, 2]} angle={0.5} intensity={2} color="#00ffff" />}
          {lightsOn && <spotLight position={[-4, 6, 2]} angle={0.5} intensity={1} color="#ffffff" />}
          
          <gridHelper args={[30, 30, lightsOn ? '#00ffff' : '#111', '#111']} position={[0, -0.01, 0]} />
          
          <CameraRig target={target} />
          <ServerRack onClick={() => setTarget('server')} isFocused={target === 'server'} />
          <Desk onClick={() => setTarget('desk')} isFocused={target === 'desk'} />
          <LightSwitch onClick={() => setLightsOn(!lightsOn)} lightsOn={lightsOn} />
        </Canvas>
      </div>
    </div>
  );
}
