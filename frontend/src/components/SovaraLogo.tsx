import React from 'react';

interface SovaraLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
}

export const SovaraSparkleMark: React.FC<{ className?: string; size?: number }> = ({ 
  className = "text-[#7adfd4]", 
  size = 22 
}) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
    >
      {/* Delicate stylized cross/sparkle with curved arms matching Logo_sidebar.svg */}
      <path 
        d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z" 
        fill="currentColor"
        opacity="0.95"
      />
      <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.8" />
    </svg>
  );
};

export const SovaraSidebarLogo: React.FC<SovaraLogoProps> = ({ 
  className = "", 
  size = 'md',
  showText = true 
}) => {
  const iconSize = size === 'sm' ? 18 : size === 'lg' ? 26 : 22;
  const textSize = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : 'text-[15px]';

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* <SovaraSparkleMark size={iconSize} className="text-[#84e4d9]" /> */}
      <img src="/asset/fav_icon.svg" alt="Sovara" />
      <img src="/asset/Logo_sidebar.svg" alt="Sovara" />
    </div>
  );
};

// Animated teal looping ribbon glyph for loading / thinking states (from MainChat-1.svg)
export const SovaraRibbonLoader: React.FC<{ size?: number; className?: string }> = ({ 
  size = 36, 
  className = "" 
}) => {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <svg 
        width={485} 
        height={size} 
        viewBox="0 0 36 36" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className="animate-spin-slow text-[#7adfd4]"
      >
        <path 
          d="M18 4C13 4 8 9 8 16C8 23 15 25 18 28C21 31 24 32 28 32C31 32 32 29 32 26C32 20 23 18 18 14C15 11 15 7 18 4Z" 
          stroke="currentColor" 
          strokeWidth="1.75" 
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-75"
        />
        <path 
          d="M10 20C10 24 14 26 18 28C22 30 26 31 28 29" 
          stroke="url(#ribbon-gradient)" 
          strokeWidth="1.5" 
          strokeLinecap="round"
        />
        <defs>
          <linearGradient id="ribbon-gradient" x1="10" y1="20" x2="28" y2="30" gradientUnits="userSpaceOnUse">
            <stop stopColor="#7adfd4" />
            <stop offset="1" stopColor="#2dd4bf" stopOpacity="0.2" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};

// Large central metallic watermark logo for MainChat Hero section
export const SovaraHeroWatermark: React.FC<{ className?: string }> = ({ className = "" }) => {
  return (
    <div className={`relative flex flex-col items-center justify-center select-none pointer-events-none ${className}`}>
      <div 
        className="font-serif-brand text-[52px] sm:text-[76px] md:text-[92px] lg:text-[104px] font-bold tracking-[0.24em] uppercase leading-none metallic-text drop-shadow-[0_10px_30px_rgba(0,0,0,0.8)]"
      >
        {/* SOVARA */}
        <img src="/asset/HeroLogo_mainpage.svg" alt="Sovara" width={350}/>
      </div>
      {/* Subtle bottom specular flare */}
      <div className="w-48 sm:w-80 h-[1px] bg-gradient-to-r from-transparent via-[#7adfd4]/15 to-transparent mt-1" />
    </div>
  );
};

