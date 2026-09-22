import React, { useState, useRef, useCallback } from 'react';

interface TacticalCompassHUDProps {
  rotation: number;
  onRotationChange: (degrees: number) => void;
  onResetRotation: () => void;
}

// Convert degrees to 16-point cardinal compass directions
const getCardinalDirection = (deg: number): string => {
  const normalized = (deg % 360 + 360) % 360;
  const directions = [
    'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
    'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
  ];
  const index = Math.round(normalized / 22.5) % 16;
  return directions[index];
};

export const TacticalCompassHUD: React.FC<TacticalCompassHUDProps> = ({
  rotation,
  onRotationChange,
  onResetRotation
}) => {
  // Widget position (relative to canvas viewport)
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 20, y: 20 });
  const [isDraggingWidget, setIsDraggingWidget] = useState<boolean>(false);
  const [isRotatingDial, setIsRotatingDial] = useState<boolean>(false);

  const widgetRef = useRef<HTMLDivElement>(null);
  const dialRef = useRef<SVGSVGElement>(null);
  const dragStartRef = useRef<{ clientX: number; clientY: number; posX: number; posY: number }>({
    clientX: 0,
    clientY: 0,
    posX: 20,
    posY: 20
  });

  const normalizedDegrees = Math.round((rotation % 360 + 360) % 360);
  const cardinal = getCardinalDirection(normalizedDegrees);
  const formattedBearing = `${normalizedDegrees.toString().padStart(3, '0')}° ${cardinal}`;

  // --- Widget Dragging Mechanics ---
  const handleWidgetPointerDown = (e: React.PointerEvent) => {
    // If clicking on dial ring, delegate to rotation handler
    if ((e.target as HTMLElement).closest('[data-compass-dial]')) return;
    
    setIsDraggingWidget(true);
    dragStartRef.current = {
      clientX: e.clientX,
      clientY: e.clientY,
      posX: pos.x,
      posY: pos.y
    };
    e.currentTarget.setPointerCapture(e.pointerId);
    e.stopPropagation();
  };

  const handleWidgetPointerMove = (e: React.PointerEvent) => {
    if (!isDraggingWidget) return;
    const dx = e.clientX - dragStartRef.current.clientX;
    const dy = e.clientY - dragStartRef.current.clientY;
    setPos({
      x: Math.max(10, dragStartRef.current.posX + dx),
      y: Math.max(10, dragStartRef.current.posY + dy)
    });
  };

  const handleWidgetPointerUp = (e: React.PointerEvent) => {
    if (isDraggingWidget) {
      setIsDraggingWidget(false);
      try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    }
  };

  // --- Compass Azimuth Ring Rotation Mechanics ---
  const handleDialPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation();
    setIsRotatingDial(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handleDialPointerMove = useCallback((e: React.PointerEvent) => {
    if (!isRotatingDial || !dialRef.current) return;
    const rect = dialRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    // Calculate angle in degrees from center (0° is North / straight up)
    const rad = Math.atan2(e.clientY - centerY, e.clientX - centerX);
    let deg = rad * (180 / Math.PI) + 90;
    if (deg < 0) deg += 360;
    
    onRotationChange(Math.round(deg));
  }, [isRotatingDial, onRotationChange]);

  const handleDialPointerUp = (e: React.PointerEvent) => {
    if (isRotatingDial) {
      setIsRotatingDial(false);
      try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    }
  };

  // Prevent default context menu on HUD
  const handleContextMenu = (e: React.MouseEvent) => e.preventDefault();

  return (
    <div
      ref={widgetRef}
      onContextMenu={handleContextMenu}
      onPointerDown={handleWidgetPointerDown}
      onPointerMove={handleWidgetPointerMove}
      onPointerUp={handleWidgetPointerUp}
      style={{
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        touchAction: 'none'
      }}
      className={`absolute z-40 select-none group flex items-center gap-3 bg-slate-950/85 backdrop-blur-md border border-slate-700/80 hover:border-emerald-400/60 rounded-full px-3.5 py-1.5 shadow-[0_8px_32px_rgba(0,0,0,0.8)] transition-shadow duration-200 cursor-grab active:cursor-grabbing ${
        isDraggingWidget ? 'ring-2 ring-emerald-400/50 shadow-[0_0_20px_rgba(16,185,129,0.3)]' : ''
      }`}
      role="toolbar"
      aria-label="Tactical Navigation Compass HUD"
      title="Click compass needle to reset North (000°); drag ring to rotate viewport matrix; drag pill to reposition HUD"
    >
      {/* Rotatable Azimuth Compass Dial */}
      <div 
        data-compass-dial
        onPointerDown={handleDialPointerDown}
        onPointerMove={handleDialPointerMove}
        onPointerUp={handleDialPointerUp}
        className="relative w-8 h-8 rounded-full cursor-ew-resize flex items-center justify-center transition-transform hover:scale-110 active:scale-95"
        title="Drag azimuth ring to rotate terrain view"
      >
        <svg
          ref={dialRef}
          viewBox="0 0 40 40"
          className="w-full h-full transform-gpu transition-transform duration-100"
          style={{ transform: `rotate(${-rotation}deg)` }}
        >
          {/* Outer Azimuth Tick Ring */}
          <circle cx="20" cy="20" r="18" fill="#0B0F17" stroke="#334155" strokeWidth="1.5" />
          
          {/* Degree Tick Marks (every 30°) */}
          {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(angle => (
            <line
              key={angle}
              x1="20"
              y1="3"
              x2="20"
              y2={angle % 90 === 0 ? "7" : "5"}
              stroke={angle === 0 ? "#EF4444" : "#64748B"}
              strokeWidth={angle % 90 === 0 ? "1.5" : "1"}
              transform={`rotate(${angle} 20 20)`}
            />
          ))}

          {/* North Direction Marker */}
          <text x="20" y="11" fill="#EF4444" fontSize="5" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
            N
          </text>

          {/* Twin-Needle Dial: Red Pointer (North) & Slate Pointer (South) */}
          <g onClick={(e) => { e.stopPropagation(); onResetRotation(); }}>
            {/* North Red Needle */}
            <polygon points="20,8 22.5,20 17.5,20" fill="#EF4444" />
            {/* South Slate Needle */}
            <polygon points="20,32 22.5,20 17.5,20" fill="#64748B" />
            {/* Center Pivot Pivot Brass Core */}
            <circle cx="20" cy="20" r="2.5" fill="#1E293B" stroke="#94A3B8" strokeWidth="1" />
          </g>
        </svg>
      </div>

      {/* High-Contrast Monospace Bearing Telemetry */}
      <div 
        className="flex flex-col cursor-pointer"
        onClick={onResetRotation}
        title="Click to reset orientation to 0° True North"
      >
        <span className="font-mono text-xs font-bold tracking-wider text-slate-100 group-hover:text-emerald-300 transition-colors tabular-nums">
          {formattedBearing}
        </span>
        <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-400">
          <span className="text-emerald-400">TRUE NORTH</span>
          <span>•</span>
          <span className="hover:underline text-slate-300">RESET 0°</span>
        </div>
      </div>
    </div>
  );
};
