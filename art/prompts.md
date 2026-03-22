# ERSim Art Prompts
## Generated 2026-03-20 | Photorealistic style, locked via --sref

Style reference: https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png

Visual direction: Cinematic editorial photography. Cool neutral color grade
with blue-green cast. Dark purple-tinted backgrounds. Harsh direct lighting,
deep shadows. Hyper-detailed skin, no retouching. Matches game UI palette
(#1a0f1e bg, #c084fc accent, cyan/amber highlights).

KEY STYLE RULES:
- NO "painterly", "digital art", "illustration", "stylized", "painting"
- YES camera/lens language, "cinematic photograph", "editorial portrait"
- Midjourney: always use --style raw --s 250 --v 7 --sref [URL above]
- --sw 100 is default style weight. Bump to --sw 150 if a gen drifts.
  Drop to --sw 50 if a character's unique features get overridden by the ref.

---

## MIDJOURNEY PROMPTS (copy-paste ready)

### ANDRE OKAFOR — PGY3, Cowboy

```
Cinematic editorial photograph of a confident Nigerian man in his early 30s, medical scrubs with sleeves pushed up, close-cropped hair, strong jaw, slight smirk, sharp direct gaze, chin slightly raised. Harsh overhead key light, deep facial shadows under cheekbones and jaw, cool neutral color grade with slight blue-green cast. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

### MAYA CHEN — PGY2, Overcalibrated

```
Cinematic editorial photograph of a young East Asian woman in her late 20s, navy medical scrubs, stethoscope around neck, short black hair tucked behind one ear. Alert but slightly uncertain expression, brow furrowed, about to ask a question. Harsh side key light from the left, deep shadows on right side of face, cool neutral color grade with blue-green cast. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

### PRIYA PATEL — PGY1, Academic

```
Cinematic editorial photograph of a young South Asian woman in her mid 20s, white coat over medical scrubs, thin-framed glasses, long dark hair pulled back tight, pen in breast pocket. Intensely focused analytical expression, slight squint, studying something off-camera. Faint blue monitor glow reflecting in glasses. Cool overhead key light, blue-green color cast, deep shadows. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

### JORDAN RIVERS — PGY2, Burning Out

```
Cinematic editorial photograph of a young man in his late 20s, wrinkled dark medical scrubs. Slight stubble, dark circles under eyes, hair slightly unkempt. Flat distant expression, thousand-yard stare, emotionally checked out. Harsh direct key light from above, deep shadows under eyes and jaw, cool neutral color grade with blue-green cast. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

### SARAH ADEYEMI — PGY3, Steady

```
Cinematic editorial photograph of a Black woman in her early 30s, neat medical scrubs, natural hair in a low professional style. Calm measured expression, quiet confidence, slight knowing look, steady eyes, relaxed jaw. Balanced warm key light with cool fill, golden undertones in skin, slight blue-green ambient cast. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

### DANNY KOWALSKI — PGY1, Cowboy

```
Cinematic editorial photograph of a young white man in his late 20s, slightly worn medical scrubs, short dirty blond hair, small scar on brow, broad shoulders. Casual confident expression, slight grin, eyebrows raised, cocky but likeable. Warm overhead key light, cool shadows, neutral color grade with slight blue-green cast. Dark purple-tinted background out of focus. Hyper-detailed skin texture, no retouching. Shot on 85mm f/1.4, shallow depth of field. --ar 1:1 --s 250 --v 7 --style raw --no text,words,letters --sref https://cdn.midjourney.com/6524515c-b3d8-4a0b-ad64-a6fc7dcbae98/0_1.png
```

---

## SPLASH / TITLE SCREEN (no --sref, different composition)

```
Cinematic photograph of an empty hospital emergency room bay at night. Curtain half-drawn, vital signs monitor glowing purple and cyan, empty gurney with crumpled white sheets, harsh fluorescent pools of light in a dark corridor. Tense quiet calm-before-the-storm atmosphere. Three empty plastic chairs against wall. Whiteboard with illegible writing. Cool neutral color grade, deep purple and violet tones with cyan and amber accent lighting. Negative space in upper third. Shot on 16-35mm f/2.8, wide angle. --ar 16:9 --s 250 --v 7 --style raw --no text,words,letters
```

---

## TROUBLESHOOTING

If a character looks too similar to the --sref source face:
  Lower style weight: --sw 50
  The sref should transfer mood/lighting/grade, not facial features.

If a gen drifts back toward painterly/cartoon:
  Bump style weight: --sw 150
  Double-check --style raw is present.

If skin looks too smooth/airbrushed:
  Add "visible pores, imperfections, no beauty retouching" to prompt.

If backgrounds are too bright:
  Add "underexposed background, low ambient" to prompt.

Run order:
1. Andre first — judge the style lock
2. If good, batch the rest
3. Splash screen last (different composition, no sref)
