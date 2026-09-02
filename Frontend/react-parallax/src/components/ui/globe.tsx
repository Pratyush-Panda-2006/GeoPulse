import React from "react";

const Globe: React.FC = () => {
  return (
    <>
      <style>
        {`
          @keyframes earthRotate {
            0% { background-position: 0 0; }
            100% { background-position: 400px 0; }
          }
          @keyframes twinkling { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-slow { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-long { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
          @keyframes twinkling-fast { 0%,100% { opacity:0.1; } 50% { opacity:1; } }
        `}
      </style>
      <div className="flex items-center justify-center h-screen w-full fixed top-0 left-0 -z-10 bg-[#0a0a0a]">
        <div
          className="relative w-[500px] h-[500px] md:w-[700px] md:h-[700px] rounded-full overflow-hidden shadow-[0_0_40px_rgba(255,255,255,0.2),-10px_0_16px_#c3f4ff_inset,30px_4px_50px_#000_inset,-48px_-4px_68px_#c3f4ff99_inset,500px_0_88px_#00000066_inset,300px_0_76px_#000000aa_inset]"
          style={{
            backgroundImage: "url('https://pub-940ccf6255b54fa799a9b01050e6c227.r2.dev/globe.jpeg')",
            backgroundSize: "cover",
            backgroundPosition: "left",
            animation: "earthRotate 30s linear infinite",
            filter: "brightness(0.7)",
          }}
        >
          {/* Stars */}
          <div
            className="absolute left-[-20px] w-1.5 h-1.5 bg-white rounded-full"
            style={{ animation: "twinkling 3s infinite" }}
          />
          <div
            className="absolute left-[40px] top-[80px] w-1.5 h-1.5 bg-white rounded-full"
            style={{ animation: "twinkling-slow 2s infinite" }}
          />
          <div
            className="absolute left-[350px] top-[90px] w-1 h-1 bg-white rounded-full"
            style={{ animation: "twinkling-long 4s infinite" }}
          />
          <div
            className="absolute left-[400px] top-[490px] w-1 h-1 bg-white rounded-full"
            style={{ animation: "twinkling 3s infinite" }}
          />
          <div
            className="absolute left-[150px] top-[270px] w-1.5 h-1.5 bg-white rounded-full"
            style={{ animation: "twinkling-fast 1.5s infinite" }}
          />
          <div
            className="absolute left-[250px] top-[50px] w-1 h-1 bg-white rounded-full"
            style={{ animation: "twinkling-long 4s infinite" }}
          />
          <div
            className="absolute left-[590px] top-[260px] w-1.5 h-1.5 bg-white rounded-full"
            style={{ animation: "twinkling-slow 2s infinite" }}
          />
        </div>
      </div>
    </>
  );
};

export default Globe;
