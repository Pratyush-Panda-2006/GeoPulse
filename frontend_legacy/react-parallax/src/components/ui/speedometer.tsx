import React from 'react';

interface SpeedometerProps {
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  label?: string;
}

const Speedometer: React.FC<SpeedometerProps> = ({ 
  value, 
  min = 0, 
  max = 200, 
  unit = "ms",
  label = "LATENCY"
}) => {
  const [displayValue, setDisplayValue] = React.useState(0);
  const [textValue, setTextValue] = React.useState(0);
  const currentTextValue = React.useRef(0);
  
  React.useEffect(() => {
    // Animate the dial
    const timeout = setTimeout(() => setDisplayValue(value), 50);
    
    // Animate the text counting up or down
    let start = currentTextValue.current;
    const duration = 1000;
    const steps = 60;
    const difference = value - start;
    const increment = difference / steps;
    const stepTime = duration / steps;
    
    const timer = setInterval(() => {
      start += increment;
      // Check if we reached or passed the target value
      if ((increment >= 0 && start >= value) || (increment < 0 && start <= value)) {
        setTextValue(value);
        currentTextValue.current = value;
        clearInterval(timer);
      } else {
        setTextValue(start);
        currentTextValue.current = start;
      }
    }, stepTime);
    
    return () => {
      clearTimeout(timeout);
      clearInterval(timer);
    };
  }, [value]);

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  // 240 degree arc -> 2/3 of circle
  const arcLength = (240 / 360) * circumference;
  
  // Calculate percentage based on min and max
  const ratio = Math.max(0, Math.min(1, (displayValue - min) / (max - min)));
  const valueLength = ratio * arcLength;

  // Generate ticks
  const numTicks = 30;
  const ticks = Array.from({ length: numTicks + 1 }).map((_, i) => {
    const deg = 150 + (i * 240) / numTicks;
    const rad = (deg * Math.PI) / 180;
    const isMajor = i % 5 === 0;
    const innerR = isMajor ? 32 : 36;
    const outerR = 38;
    const x1 = 50 + innerR * Math.cos(rad);
    const y1 = 50 + innerR * Math.sin(rad);
    const x2 = 50 + outerR * Math.cos(rad);
    const y2 = 50 + outerR * Math.sin(rad);
    
    // Number label for major ticks
    let labelNode = null;
    if (isMajor) {
      const labelR = 24;
      const lx = 50 + labelR * Math.cos(rad);
      const ly = 50 + labelR * Math.sin(rad);
      const tickValue = Math.round(min + (i / numTicks) * (max - min));
      labelNode = (
        <text 
          x={lx} y={ly} 
          className="text-[4px] fill-gray-500 font-mono" 
          textAnchor="middle" 
          alignmentBaseline="middle"
        >
          {tickValue}
        </text>
      );
    }
    
    return (
      <g key={i}>
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" className={isMajor ? "text-gray-400" : "text-gray-600"} strokeWidth={isMajor ? 1 : 0.5} />
        {labelNode}
      </g>
    );
  });

  return (
    <div className="relative w-full max-w-[280px] mx-auto flex flex-col items-center">
      <svg viewBox="0 0 100 100" className="w-full drop-shadow-2xl">
        {/* Ticks */}
        {ticks}

        {/* Background Track */}
        <circle 
          cx="50" cy="50" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference}`}
          transform="rotate(150 50 50)"
        />

        {/* Foreground Track */}
        <circle 
          cx="50" cy="50" r={radius}
          fill="none"
          stroke="white"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${valueLength} ${circumference}`}
          className="transition-all duration-1000 ease-out"
          transform="rotate(150 50 50)"
        />
        
        {/* Center Text */}
        <text x="50" y="55" textAnchor="middle" className="text-xl font-bold fill-white font-mono tracking-tighter">
          {textValue.toFixed(0)}
        </text>
        <text x="50" y="65" textAnchor="middle" className="text-[6px] fill-gray-400 font-mono tracking-widest uppercase">
          {unit}
        </text>
      </svg>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center">
         <span className="font-mono text-[10px] text-gray-500 tracking-widest uppercase">{label}</span>
      </div>
    </div>
  );
};

export default Speedometer;
