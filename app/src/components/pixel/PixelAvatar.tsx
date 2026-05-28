import React from 'react';

interface PixelAvatarProps {
  type: 'theme' | 'world' | 'role' | 'plot' | 'chapter' | 'writer' | 'publish' |
         'allen' | 'liya' | 'kael' | 'morin' | 'rocket' | 'gpt';
  size?: number;
  className?: string;
}

// 12x16 pixel art character avatars - each has hair, face, body, clothes
// Colors: . = transparent, H = hair, S = skin, E = eye, B = body/clothes, D = dark detail, O = outline

const AgentAvatars: Record<string, string[]> = {
  theme: [
    "....HHHH....",
    "...HHHHHH...",
    "...HHSSHH...",
    "...HSEESH...",
    "...HSEESH...",
    "...SSSSSS...",
    "....SSSS....",
    "...BBBBBB...",
    "...BBBBBB...",
    "...BBBBBB...",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "....BB.BB...",
    "....BB.BB...",
    "...BBB.BBB..",
  ],
  world: [
    "....DDDD....",
    "..DDDDDDDD..",
    "..DDSSSSDD..",
    "..DSEEEESD..",
    "..DSEEEESD..",
    "...SSSSSS...",
    "....SSSS....",
    "...GGGGGG...",
    "...GGGGGG...",
    "...GGGGGG...",
    "..GGGGGGGG..",
    "..GGGGGGGG..",
    "..GGGGGGGG..",
    "....GG.GG...",
    "....GG.GG...",
    "...GGG.GGG..",
  ],
  role: [
    ".....HH.....",
    "...HHHHHH...",
    "..HHHHHHHH..",
    "..HHSSSSHH..",
    "..HSEEEESH..",
    "...SEEEES...",
    "....SSSS....",
    "...BBBBBB...",
    "...BBBBBB...",
    "...BBBBBB...",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "....BB.BB...",
    "....BB.BB...",
    "...BBB.BBB..",
  ],
  plot: [
    "....PPPP....",
    "...PPPPPP...",
    "..PPPPPPPP..",
    "..PPSSSSPP..",
    "..PSEEEESP..",
    "...SEEEES...",
    "....SSSS....",
    "...MMMMMM...",
    "...MMMMMM...",
    "...MMMMMM...",
    "..MMMMMMMM..",
    "..MMMMMMMM..",
    "..MMMMMMMM..",
    "....MM.MM...",
    "....MM.MM...",
    "...MMM.MMM..",
  ],
  chapter: [
    "....GGGG....",
    "...GGGGGG...",
    "..GGGGGGGG..",
    "..GGSSSSGG..",
    "..GSEEEESG..",
    "...SEEEES...",
    "....SSSS....",
    "...CCCCCC...",
    "...CCCCCC...",
    "...CCCCCC...",
    "..CCCCCCCC..",
    "..CCCCCCCC..",
    "..CCCCCCCC..",
    "....CC.CC...",
    "....CC.CC...",
    "...CCC.CCC..",
  ],
  writer: [
    "....BBBB....",
    "...BBBBBB...",
    "..BBBBBBBB..",
    "..BBSSSSBB..",
    "..BSEEEESB..",
    "...SEEEES...",
    "....SSSS....",
    "...OOOOOO...",
    "...OOOOOO...",
    "...OOOOOO...",
    "..OOOOOOOO..",
    "..OOOOOOOO..",
    "..OOOOOOOO..",
    "....OO.OO...",
    "....OO.OO...",
    "...OOO.OOO..",
  ],
  publish: [
    "....OOOO....",
    "...OOOOOO...",
    "..OOOOOOOO..",
    "..OOSSSSOO..",
    "..OSEEEESO..",
    "...SEEEES...",
    "....SSSS....",
    "...BBBBBB...",
    "...BBBBBB...",
    "...BBBBBB...",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "....BB.BB...",
    "....BB.BB...",
    "...BBB.BBB..",
  ],
};

const AgentColorMaps: Record<string, Record<string, string>> = {
  theme: {
    H: '#E8B84B',  // golden hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    B: '#4F8CFF',  // blue clothes
    D: '#3A7BEE',  // dark detail
    G: '#68D391',  // green (not used)
    P: '#D53F8C',  // purple (not used)
    M: '#9F7AEA',  // magenta (not used)
    C: '#4FD1C5',  // cyan (not used)
    O: '#DD6B20',  // orange (not used)
    '.': 'transparent',
  },
  world: {
    H: '#744210',  // brown hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    G: '#48BB78',  // green clothes
    D: '#2F855A',  // dark hair
    B: '#4F8CFF',  // blue
    P: '#D53F8C',
    M: '#9F7AEA',
    C: '#4FD1C5',
    O: '#DD6B20',
    '.': 'transparent',
  },
  role: {
    H: '#2D3748',  // dark hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    B: '#3182CE',  // blue clothes
    D: '#2C5282',
    G: '#48BB78',
    P: '#D53F8C',
    M: '#9F7AEA',
    C: '#4FD1C5',
    O: '#DD6B20',
    '.': 'transparent',
  },
  plot: {
    H: '#805AD5',  // purple hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    M: '#B794F6',  // magenta clothes
    D: '#553C9A',
    B: '#4F8CFF',
    G: '#48BB78',
    P: '#D53F8C',
    C: '#4FD1C5',
    O: '#DD6B20',
    '.': 'transparent',
  },
  chapter: {
    H: '#718096',  // gray hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    C: '#A0AEC0',  // gray clothes
    D: '#4A5568',
    B: '#4F8CFF',
    G: '#48BB78',
    P: '#D53F8C',
    M: '#9F7AEA',
    O: '#DD6B20',
    '.': 'transparent',
  },
  writer: {
    H: '#1A202C',  // black hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    O: '#C05621',  // orange/brown clothes
    D: '#7B341E',
    B: '#4F8CFF',
    G: '#48BB78',
    P: '#D53F8C',
    M: '#9F7AEA',
    C: '#4FD1C5',
    '.': 'transparent',
  },
  publish: {
    H: '#975A16',  // brown hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    B: '#38A169',  // teal/green clothes
    D: '#276749',
    G: '#48BB78',
    P: '#D53F8C',
    M: '#9F7AEA',
    C: '#4FD1C5',
    O: '#DD6B20',
    '.': 'transparent',
  },
};

// Character avatars with distinct looks
const CharacterAvatars: Record<string, string[]> = {
  allen: [
    "....DDDD....",
    "...DDDDDD...",
    "..DDDDDDDD..",
    "..DDSSSSDD..",
    "..DSEEEESD..",
    "...SEEEES...",
    "....SSSS....",
    "...BBBBBB...",
    "...BBBBBB...",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "...AAAAAA...",
    "....AA.AA...",
    "....AA.AA...",
    "...AAA.AAA..",
  ],
  liya: [
    "....SSSS....",
    "...SSSSSS...",
    "..SSSSSSSS..",
    "..SSSSSSSS..",
    "..SSEEEESS..",
    "...SEEEES...",
    "....SSSS....",
    "...FFFFFF...",
    "...FFFFFF...",
    "..FFFFFFFF..",
    "..FFFFFFFF..",
    "..FFFFFFFF..",
    "....FF.FF...",
    "....FF.FF...",
    "....FF.FF...",
    "...FFF.FFF..",
  ],
  kael: [
    "....BBBB....",
    "..BBBBBBBB..",
    "..BBBBBBBB..",
    "..BBSSSSBB..",
    "..BSEEEESB..",
    "..BSEEEESB..",
    "...SSSSSS...",
    "...HHHHHH...",
    "...HHHHHH...",
    "..HHHHHHHH..",
    "..HHHHHHHH..",
    "..HHHHHHHH..",
    "....HH.HH...",
    "....HH.HH...",
    "....HH.HH...",
    "...HHH.HHH..",
  ],
  morin: [
    "....KKKK....",
    "...KKKKKK...",
    "..KKSSSSKK..",
    "..KSSEEEESK.",
    "..KSSEEEESK.",
    "...SSEEEES..",
    "....SSSS....",
    "...PPPPPP...",
    "...PPPPPP...",
    "..PPPPPPPP..",
    "..PPPPPPPP..",
    "..PPPPPPPP..",
    "....PP.PP...",
    "....PP.PP...",
    "....PP.PP...",
    "...PPP.PPP..",
  ],
};

const CharacterColorMaps: Record<string, Record<string, string>> = {
  allen: {
    D: '#2D3748',  // dark hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    B: '#2B6CB0',  // blue armor
    A: '#4A5568',  // armor detail
    H: '#744210',
    F: '#E2E8F0',
    K: '#553C9A',
    P: '#1A202C',
    '.': 'transparent',
  },
  liya: {
    S: '#E2E8F0',  // silver hair
    E: '#1F2329',  // eyes
    F: '#E6FFFA',  // white dress
    D: '#A0AEC0',
    B: '#2B6CB0',
    A: '#4A5568',
    H: '#744210',
    K: '#553C9A',
    P: '#1A202C',
    '.': 'transparent',
  },
  kael: {
    B: '#744210',  // brown hair
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    H: '#2F855A',  // green clothes
    D: '#276749',
    A: '#4A5568',
    F: '#E2E8F0',
    K: '#553C9A',
    P: '#1A202C',
    '.': 'transparent',
  },
  morin: {
    K: '#553C9A',  // purple hood
    S: '#F5D0A0',  // skin
    E: '#1F2329',  // eyes
    P: '#1A202C',  // dark clothes
    D: '#2D3748',
    B: '#2B6CB0',
    A: '#4A5568',
    F: '#E2E8F0',
    H: '#744210',
    '.': 'transparent',
  },
};

const PixelAvatar: React.FC<PixelAvatarProps> = ({ type, size = 48, className = '' }) => {
  if (type === 'rocket') {
    return (
      <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
        <div 
          className="w-full h-full rounded-full bg-gradient-to-br from-[#EBF4FF] to-[#DBEAFE] flex items-center justify-center shadow-inner"
        >
          <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none" className="text-primary-600">
            <path d="M12 2C12 2 8 6 8 10C8 12 9 13 10 14H14C15 13 16 12 16 10C16 6 12 2 12 2Z" fill="currentColor" opacity="0.9"/>
            <path d="M10 14V17C10 18 9 19 8 20L12 22L16 20C15 19 14 18 14 17V14" fill="currentColor" opacity="0.7"/>
            <circle cx="12" cy="9" r="1.5" fill="white"/>
          </svg>
        </div>
      </div>
    );
  }

  if (type === 'gpt') {
    return (
      <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
        <div className="w-full h-full rounded-2xl bg-gradient-to-br from-[#10A37F] to-[#0D8C6D] flex items-center justify-center shadow-md">
          <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24" fill="none">
            <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073z" fill="white"/>
          </svg>
        </div>
      </div>
    );
  }

  // Agent avatars
  if (AgentAvatars[type]) {
    const grid = AgentAvatars[type];
    const colors = AgentColorMaps[type];
    return (
      <svg
        width={size}
        height={size}
        viewBox={`0 0 12 16`}
        className={`pixelated ${className}`}
        shapeRendering="crispEdges"
      >
        {grid.map((row, y) =>
          row.split('').map((cell, x) => {
            if (cell === '.') return null;
            return (
              <rect
                key={`${x}-${y}`}
                x={x}
                y={y}
                width={1}
                height={1}
                fill={colors[cell] || '#1F2329'}
              />
            );
          })
        )}
      </svg>
    );
  }

  // Character avatars
  if (CharacterAvatars[type]) {
    const grid = CharacterAvatars[type];
    const colors = CharacterColorMaps[type];

    return (
      <svg
        width={size}
        height={size}
        viewBox={`0 0 12 16`}
        className={`pixelated ${className}`}
        shapeRendering="crispEdges"
      >
        {grid.map((row, y) =>
          row.split('').map((cell, x) => {
            if (cell === '.') return null;
            return (
              <rect
                key={`${x}-${y}`}
                x={x}
                y={y}
                width={1}
                height={1}
                fill={colors[cell] || '#1F2329'}
              />
            );
          })
        )}
      </svg>
    );
  }

  return null;
};

export default PixelAvatar;
