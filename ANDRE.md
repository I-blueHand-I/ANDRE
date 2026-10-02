# SendPix3 — Cahier des charges & Blueprint technique

## Résumé du projet

SendPix3 est un logiciel d'édition d'animation pixel art et de VJing live conçu pour piloter des installations LED en temps réel. C'est la troisième itération de SendPix, reconstruit from scratch en **Python + PySide6** pour remplacer la version Godot (SendPix2) qui souffre de limitations techniques bloquantes en contexte de performance live.

Le logiciel a **deux modes d'utilisation** :
- **EDIT** : création et édition d'animations pixel art frame par frame
- **LIVE** : mix en temps réel de deux sources (animations pixel art ou vidéos MP4) avec crossfader, blend modes, et sortie vers matrices LED via UDP

Le tout est contrôlable via un contrôleur MIDI custom (mixette physique).

---

## Contexte & Problèmes à résoudre

### Problèmes critiques de SendPix2 (Godot)

1. **Pas de séparation de threads** : l'output LED et l'éditeur tournent sur le même thread. Charger une animation lourde freeze la sortie LED — inacceptable en live.
2. **Crash sur les animations longues** : au-delà de ~200 frames (séquences d'images PNG/JPG), le logiciel crash fréquemment.
3. **Pas de transitions** : le passage d'une animation à une autre est instantané, sans fondu ni mode de fusion. Pas de crossfade possible.
4. **Pas de support vidéo** : impossible de charger et mixer des MP4, uniquement des séquences d'images.
5. **MIDI fragile et hardcodé** : le mapping MIDI est codé en dur dans `mixette.gd`, ne fonctionne que sur Linux, et nécessite des manipulations manuelles.
6. **Résolution LED non dynamique** : la taille de la matrice (ex: 21×21, 14×6) est hardcodée et ne peut pas être changée sans modifier le code source.
7. **Outils d'édition limités** : pas de vrai onion skin, pas de taille de pinceau variable, pas de copier/coller de frames.
8. **Mapping LED obsolète** : le système multi-faces (`facestart`, `facex`, `facey`) est abandonné et ne doit PAS être reproduit.

### Ce que SendPix2 fait bien (à conserver)

- Interface responsive, utilisable sans formation (logique "borne d'arcade")
- Roue de couleur custom avec shader
- Palette de couleurs sauvegardables
- Mixette colorimétrique HSV/RGB
- Export/import de séquences d'images
- Système de ghost frame (pelure d'oignon basique)
- Feedback visuel immédiat (tweens, animations d'interface)

---

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.11+ |
| Framework UI | PySide6 (Qt6) |
| Manipulation d'images | NumPy (arrays RGB) |
| Chargement d'images | Pillow (PIL) |
| Décodage vidéo MP4 | OpenCV (cv2.VideoCapture) |
| MIDI | python-rtmidi |
| Réseau (UDP) | socket (stdlib) |
| Packaging | Nuitka ou PyInstaller |
| Configuration | JSON (stdlib) |

---

## Interface utilisateur — Système d'onglets

L'application a **3 onglets principaux** en haut de la fenêtre, comme des tabs. Un seul onglet est visible à la fois :

### Onglet EDIT — Éditeur d'animation pixel art
- Canvas de dessin pixel (centre)
- Timeline verticale de frames (côté)
- Outils de dessin : pinceau (tailles 1-5), pot de peinture, pipette
- Roue de couleur + palette
- Contrôles : NEW ANIM, EXPORT ANIM, FPS, THICK (taille pinceau)
- Onion skin activable

### Onglet LIVE — Mix en temps réel
- **Deck A** (moitié gauche) : preview en résolution native + slider vertical FPS
- **Deck B** (moitié droite) : preview en résolution native + slider vertical FPS
- **Crossfader OPACITY** (horizontal, entre A et B) : slider A↔B
- **Blend mode** (dropdown gauche) : Multiply, Normal, Addition, Subtract
- **Interpolation mode** (dropdown droite) : Nearest, Bicubic, Area, Linear — détermine la méthode de resize pour l'output LED
- **ANIMATIONS BANK** (bas gauche) : grille de thumbnails des animations du projet. Drag & drop vers Deck A ou B pour charger.
- **MP4 BANK** (bas droite) : grille de thumbnails des vidéos MP4 importées. Drag & drop vers Deck A ou B pour charger.
- **Settings** (accessible via bouton) : résolution LED (W × H), port UDP, adresse UDP, bouton "SEND PIX!" pour activer le broadcast

### Onglet MIXETTE — Configuration de la mixette couleur
- Sliders horizontaux : HUE, SATURATION, VELOCITY (Value), RED, GREEN, BLUE
- Chaque slider a un bouton **"midi bind"** à côté pour assigner un CC MIDI via learn mode
- Cet onglet sert à la **configuration** — en live, la mixette est contrôlée physiquement via le contrôleur MIDI, pas via cette UI

### Fenêtre OUTPUT (séparée)
- Fenêtre secondaire qui affiche le résultat final mixé, en plein écran ou fenêtré
- Affiche les pixels agrandis (nearest neighbor upscale pour la visualisation)
- Indique le mode d'interpolation actif (ex: "sampling ! BICUBIC")
- C'est ce qui est envoyé aux LEDs (après downscale à la résolution configurée)

---

## Architecture logicielle

### Threads séparés

```
┌─────────────────────────────────────────────────┐
│  THREAD PRINCIPAL — UI (PySide6 event loop)     │
│                                                 │
│  ┌─── ONGLET EDIT ──────────────────────────┐   │
│  │ Pixel canvas, timeline, color tools      │   │
│  └──────────────────────────────────────────┘   │
│  ┌─── ONGLET LIVE ──────────────────────────┐   │
│  │ Deck A/B (preview native), crossfader,   │   │
│  │ banks (anim + MP4), blend/interp mode    │   │
│  └──────────────────────────────────────────┘   │
│  ┌─── ONGLET MIXETTE ──────────────────────┐    │
│  │ Sliders HSV/RGB + MIDI bind buttons      │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ MIDI handler (réception, dispatch)       │   │
│  └──────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────┘
               │ Qt Signals (thread-safe)
               ▼
┌─────────────────────────────────────────────────┐
│  THREAD ENGINE — Render (QThread)               │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐│
│  │ Mixer    │ │ Frame    │ │ Media loader     ││
│  │ blend +  │ │ cache    │ │ (images + MP4,   ││
│  │ HSV/RGB  │ │ (NumPy)  │ │  async)          ││
│  └──────────┘ └──────────┘ └──────────────────┘│
│  ┌──────────────────────────────────────────────┐│
│  │ Video decoder (OpenCV, pour les MP4)        ││
│  └──────────────────────────────────────────────┘│
└──────────────┬──────────────────────────────────┘
               │ Queue (frame RGB prête, résolution native)
               ▼
┌─────────────────────────────────────────────────┐
│  THREAD OUTPUT — UDP broadcast (QThread)        │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐│
│  │ Downscale│ │ UDP      │ │ Preview window   ││
│  │ + interp │ │ sender   │ │ (output display) ││
│  └──────────┘ └──────────┘ └──────────────────┘│
└─────────────────────────────────────────────────┘
```

### Pipeline de rendu — flux de données

```
Deck A (anim ou MP4, résolution native)
    │
    ├──→ Previews LIVE (résolution native, affiché tel quel dans l'UI)
    │
    ▼
  MIXER (blend mode + crossfader alpha)  ←── Deck B (anim ou MP4, résolution native)
    │
    ▼
  COLOR CORRECTION (HSV/RGB, via mixette MIDI)
    │
    ▼
  Frame mixée (résolution native)
    │
    ├──→ Preview OUTPUT window (upscale nearest pour affichage)
    │
    ▼
  DOWNSCALE (resize vers résolution LED, interpolation configurable)
    │
    ▼
  CLIP [0, 254] + UDP broadcast → LED panels
```

**Point important** : le downscale vers la résolution LED (21×21, 14×6...) ne se fait qu'au tout dernier moment, dans le thread output. Les decks, le mixer, et la fenêtre output travaillent en résolution native. Cela permet d'afficher les vidéos MP4 en haute définition dans les previews des decks.

### Communication inter-threads

- **UI → Engine** : Qt Signals (thread-safe par défaut avec `Qt.QueuedConnection`)
- **Engine → Output** : `queue.Queue` Python (thread-safe) contenant la frame RGB finale en résolution native sous forme de `numpy.ndarray`
- **Engine → UI** : Qt Signals pour mettre à jour les previews des decks (frames en résolution native)
- **Output → UI** : Qt Signals pour le retour d'état (FPS réel, statut connexion)

### Représentation des données

- **Une frame pixel art** = `numpy.ndarray` de shape `(height, width, 3)`, dtype `uint8`, canaux RGB — taille petite (ex: 21×21)
- **Une frame vidéo MP4** = `numpy.ndarray` de shape `(height, width, 3)`, dtype `uint8`, canaux RGB — taille native de la vidéo (ex: 1920×1080)
- **Une animation** = liste de frames NumPy
- **Le crossfader** = opération NumPy vectorisée : `output = (1-alpha) * deck_a + alpha * deck_b` (les deux decks doivent être au même format/taille pour le blend — resize au plus grand commun si nécessaire)
- **Les corrections couleur** = opérations NumPy sur l'espace HSV (via conversion RGB→HSV→RGB)
- **Le downscale final** = `cv2.resize()` avec interpolation configurable (INTER_NEAREST, INTER_CUBIC, INTER_AREA, INTER_LINEAR)

---

## Structure des fichiers du projet (code source)

```
sendpix3/
├── main.py                  # Point d'entrée, lance la config puis la fenêtre principale
├── config.py                # Chargement/sauvegarde de la configuration JSON
├── config.json              # Fichier de configuration utilisateur
│
├── ui/
│   ├── main_window.py       # Fenêtre principale, système d'onglets EDIT/LIVE/MIXETTE
│   ├── config_dialog.py     # Dialog de configuration (résolution, UDP, interpolation)
│   │
│   ├── edit/                # --- Onglet EDIT ---
│   │   ├── edit_tab.py      # Layout de l'onglet EDIT
│   │   ├── pixel_canvas.py  # Widget canvas d'édition pixel (QWidget, paintEvent)
│   │   ├── timeline.py      # Widget timeline verticale (liste de frames, scroll)
│   │   ├── frame_thumbnail.py # Widget miniature d'une frame dans la timeline
│   │   ├── color_wheel.py   # Widget roue de couleur (custom paint)
│   │   ├── color_palette.py # Widget palette de couleurs sauvegardables
│   │   └── tool_bar.py      # Barre d'outils (pinceau, tailles, pot de peinture, pipette)
│   │
│   ├── live/                # --- Onglet LIVE ---
│   │   ├── live_tab.py      # Layout de l'onglet LIVE
│   │   ├── deck_widget.py   # Widget deck A ou B (preview native + contrôles FPS)
│   │   ├── crossfader.py    # Widget crossfader horizontal + label A/B
│   │   ├── anim_bank.py     # Grille de thumbnails animations (drag & drop source)
│   │   ├── mp4_bank.py      # Grille de thumbnails vidéos MP4 (drag & drop source)
│   │   └── settings_panel.py # Panel settings (résolution, UDP, bouton SEND PIX!)
│   │
│   ├── mixette/             # --- Onglet MIXETTE ---
│   │   └── mixette_tab.py   # Sliders HSV/RGB + boutons midi bind
│   │
│   └── output_window.py     # Fenêtre OUTPUT séparée (affichage résultat final)
│
├── engine/
│   ├── render_engine.py     # QThread engine : mixer, boucle de rendu
│   ├── image_loader.py      # Chargement async d'animations (images PNG)
│   ├── video_decoder.py     # Décodage MP4 via OpenCV (cv2.VideoCapture)
│   ├── frame_cache.py       # Cache de frames en NumPy arrays
│   ├── blending.py          # Fonctions de blend (normal, add, multiply, subtract)
│   └── color_correction.py  # Corrections HSV/RGB vectorisées (NumPy)
│
├── output/
│   ├── udp_output.py        # QThread : downscale + broadcast UDP
│   └── led_mapping.py       # Conversion frame → buffer LED bytes
│
├── midi/
│   ├── midi_handler.py      # Réception MIDI via python-rtmidi (QThread)
│   └── midi_config.py       # Modèle de données du mapping MIDI (sérialisé en JSON)
│
├── project/
│   └── export.py            # Export/sauvegarde d'animations en séquences PNG
│
└── utils/
    ├── undo_manager.py      # Système undo/redo global
    └── helpers.py           # Fonctions utilitaires diverses
```

---

## Stockage et données

**Pas de format projet** — le logiciel fonctionne avec des dossiers existants sur le disque, sans copie ni duplication.

### config.json (dossier de l'application)

Fichier unique de configuration, sauvegardé automatiquement. Contient :

```json
{
  "led_resolution": [21, 16],
  "udp_port": 37020,
  "udp_address": "255.255.255.255",
  "interpolation": "BICUBIC",
  "animations_folder": "/home/hugo/LED_animations",
  "mp4_folder": "/home/hugo/LED_videos",
  "midi_bindings": {
    "crossfader": {"channel": 0, "cc": 7},
    "hue": {"channel": 0, "cc": 1},
    "saturation": {"channel": 0, "cc": 2}
  },
  "palette": ["#FF0000", "#00FF00", "#0000FF"]
}
```

### Dossier d'animations (configurable)

Le chemin est configuré dans les settings. Le logiciel scanne ce dossier pour remplir l'ANIMATIONS BANK. Structure attendue :

```
LED_animations/
├── dragon_1/
│   ├── 000.png
│   ├── 001.png
│   └── ...
├── pyramide/
│   ├── 000.png
│   └── ...
└── crane_1/
    └── ...
```

Chaque sous-dossier = une animation. Les PNG sont numérotés séquentiellement. Le nom du dossier = le nom affiché dans la bank.

### Dossier MP4 (configurable)

Le chemin est configuré dans les settings. Le logiciel scanne ce dossier pour remplir la MP4 BANK.

```
LED_videos/
├── vj_loop_1.mp4
├── vj_loop_2.mp4
└── ...
```

### Sauvegarde des animations éditées

Quand l'utilisateur crée ou modifie une animation dans l'onglet EDIT :
- **Nouvelle animation** : l'utilisateur choisit un nom, un dossier est créé dans le dossier d'animations configuré, les frames sont sauvées en PNG
- **Sauvegarde (Ctrl+S)** : écrase les PNG existants dans le dossier de l'animation
- **Export (Ctrl+E)** : exporte vers un emplacement choisi par l'utilisateur (pour partager/archiver)

---

## Settings (dialog intégré à l'onglet LIVE)

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| Résolution LED W | int | 21 | Largeur de la matrice en pixels |
| Résolution LED H | int | 16 | Hauteur de la matrice en pixels |
| Port UDP | int | 37020 | Port de broadcast |
| Adresse UDP | string | 255.255.255.255 | Adresse de destination broadcast |
| Interpolation | enum | BICUBIC | Méthode de resize pour l'output (Nearest, Bicubic, Area, Linear) |
| Dossier animations | path | — | Chemin vers le dossier contenant les animations (sous-dossiers de PNG) |
| Dossier MP4 | path | — | Chemin vers le dossier contenant les vidéos MP4 |
| Bouton SEND PIX! | action | — | Valide les settings et lance la session (passe à l'onglet LIVE) |

Les settings sont accessibles depuis l'onglet LIVE via un bouton SETTINGS. Ils sont sauvegardés dans le `project.json` du projet.

---

## Modules fonctionnels détaillés

### 1. Éditeur pixel — onglet EDIT (pixel_canvas.py)

Un widget `QWidget` avec `paintEvent` custom qui dessine la grille de pixels.

**Outils disponibles :**
- **Pinceau (B)** : tailles 1×1, 2×2, 3×3, 4×4, 5×5 (raccourcis 1-5 ou slider THICK). Dessine en maintenant le clic gauche.
- **Gomme** : pinceau qui peint en noir (couleur de fond).
- **Pot de peinture (G)** : flood fill (algorithme BFS 4-connexe).
- **Pipette (I)** : clic pour récupérer la couleur d'un pixel.

**Onion skin :**
- Affiche la frame précédente (et optionnellement la suivante) en semi-transparent sous la frame courante.
- Opacité configurable via slider (0% à 50%).
- Activable/désactivable via bouton toggle (raccourci O).
- Implémentation : superposition de deux layers NumPy avec alpha blending, pas de hack sur les pixels noirs comme dans SendPix2.

**Contrôles de l'onglet EDIT :**
- NEW ANIM : crée une nouvelle animation vide dans le projet
- EXPORT ANIM : exporte l'animation courante en séquence PNG
- FPS : réglage de la vitesse de playback de l'animation
- Play/Pause de l'animation dans l'éditeur

**Interactions :**
- Clic gauche : dessiner avec l'outil sélectionné
- Clic droit : pipette (raccourci rapide)
- Molette : zoom (optionnel, stretch du canvas)

**Mode LIVE EDIT :**
Depuis l'onglet EDIT, l'utilisateur peut activer le mode LIVE EDIT pour dessiner en direct sur les LEDs pendant un set. Ce mode envoie l'animation en cours d'édition vers un des decks du mode LIVE :
- **F** : active le LIVE EDIT et envoie l'animation vers le **Deck A**
- **Shift+F** : active le LIVE EDIT et envoie l'animation vers le **Deck B**
- Appuyer de nouveau sur F (ou Shift+F) désactive le LIVE EDIT

Quand le LIVE EDIT est actif :
- Un indicateur visuel dans l'onglet EDIT montre quel deck est lié (ex: "LIVE → DECK A" en vert clignotant)
- Chaque modification sur le canvas (dessin, pot de peinture, etc.) est immédiatement reflétée dans le deck correspondant
- Le playback de l'animation dans l'éditeur est synchronisé avec le deck
- Le crossfader, les blend modes et la mixette couleur s'appliquent normalement — l'animation éditée en live est mixée avec l'autre deck

### 2. Timeline — onglet EDIT (timeline.py)

Liste scrollable **verticale** de miniatures de frames (comme SendPix2).

**Fonctionnalités :**
- Ajout de frame (bouton +, insère après la frame courante)
- Suppression de frame (bouton × sur chaque miniature)
- Sélection de frame (clic sur miniature → charge dans l'éditeur)
- **Copier/coller** : Ctrl+C copie la frame courante, Ctrl+V l'insère après la position courante
- **Dupliquer** : raccourci Ctrl+D = copier + coller en un geste
- Drag & drop pour réordonner (optionnel, phase ultérieure)
- Highlight de la frame sélectionnée
- Numérotation automatique des frames

### 3. Decks A/B — onglet LIVE (deck_widget.py)

Chaque deck occupe une moitié de l'onglet LIVE et peut charger une animation OU une vidéo MP4.

**Fonctionnalités :**
- Chargement par **drag & drop** depuis l'ANIMATIONS BANK ou la MP4 BANK
- Preview en **résolution native** (pas de downscale dans les previews)
- Play / Pause / Stop
- **Slider vertical FPS** (à gauche du Deck A, à droite du Deck B) — contrôle la vitesse de lecture. Pour les MP4 : multiplicateur de vitesse.
- Affichage de la frame courante
- Indication du nom du contenu chargé

**Gestion des résolutions différentes :**
Quand les deux decks n'ont pas la même résolution (ex: Deck A = animation 21×21, Deck B = vidéo 1920×1080), le mixer doit les ramener à une taille commune avant le blend. Stratégie : upscale le plus petit à la taille du plus grand (nearest neighbor pour garder le pixel art net).

### 4. ANIMATIONS BANK — onglet LIVE (anim_bank.py)

Grille scrollable de thumbnails en bas à gauche de l'onglet LIVE.

**Affichage :**
- Scanne le **dossier d'animations configuré** dans les settings
- Chaque sous-dossier contenant des PNG = une animation
- Chaque thumbnail montre la première frame + le nom du dossier
- Bouton refresh pour rescanner le dossier
- Actualisation automatique quand une animation est créée/sauvée dans l'onglet EDIT

**Drag & drop — deux directions :**
- **Sortant** : glisser une thumbnail vers Deck A ou Deck B pour charger l'animation dans le deck
- **Entrant** : glisser un ou plusieurs dossiers de séquences d'images depuis l'explorateur de fichiers vers la bank → les dossiers sont copiés dans le dossier d'animations configuré, la bank se rafraîchit automatiquement. Import multiple supporté.

**Bouton "Importer"** : ouvre un sélecteur de dossiers (sélection multiple) pour importer des animations sans drag & drop

### 5. MP4 BANK — onglet LIVE (mp4_bank.py)

Grille scrollable de thumbnails en bas à droite de l'onglet LIVE.

**Affichage :**
- Scanne le **dossier MP4 configuré** dans les settings
- Chaque fichier .mp4 du dossier est listé
- Chaque thumbnail montre la première frame + nom + durée + FPS natif
- Bouton refresh pour rescanner le dossier

**Drag & drop — deux directions :**
- **Sortant** : glisser une thumbnail vers Deck A ou Deck B pour charger la vidéo dans le deck
- **Entrant** : glisser un ou plusieurs fichiers .mp4 depuis l'explorateur de fichiers vers la bank → les fichiers sont copiés dans le dossier MP4 configuré, la bank se rafraîchit automatiquement. Import multiple supporté.

**Bouton "Importer"** : ouvre un sélecteur de fichiers (sélection multiple, filtre .mp4) pour importer des vidéos sans drag & drop

### 6. Crossfader & Blend modes — onglet LIVE (crossfader.py)

**Crossfader :**
- Slider horizontal entre les deux decks, labellé "A" à gauche et "B" à droite
- 0.0 = full Deck A, 1.0 = full Deck B
- Labellé "OPACITY" au-dessus
- Mappable sur un fader MIDI

**Blend modes (dropdown "FUSIONMODE" à gauche) :**
- Normal (alpha blend via crossfader)
- Multiply
- Addition (Add, clampé à 255)
- Subtract

**Interpolation mode (dropdown à droite) :**
- Nearest
- Bicubic
- Area
- Linear

Ce choix détermine la méthode d'interpolation utilisée pour le downscale vers la résolution LED dans le thread output.

Implémentation blend : opérations NumPy vectorisées dans `engine/blending.py`.

### 7. Mixette couleur — onglet MIXETTE (mixette_tab.py)

Sliders de correction appliqués à la sortie mixée finale (après le blend des decks).

**Sliders :**
- HUE : rotation de teinte
- SATURATION : multiplicateur
- VELOCITY (Value/Brightness) : multiplicateur
- RED : multiplicateur canal R
- GREEN : multiplicateur canal G
- BLUE : multiplicateur canal B

**Chaque slider a un bouton "midi bind"** à côté. Workflow de binding :
1. Cliquer sur "midi bind" → le bouton passe en mode "learn" (clignotant)
2. Bouger un fader/potard sur le contrôleur MIDI physique
3. Le CC reçu est automatiquement associé à ce slider
4. Le binding est sauvegardé dans la config

En performance live, cet onglet n'est pas utilisé — la mixette est contrôlée entièrement via le contrôleur MIDI physique.

### 8. Sortie LED (udp_output.py + led_mapping.py)

**Thread output (ne freeze jamais) :**
- Boucle à fréquence configurable (défaut 60Hz)
- Reçoit la frame mixée en résolution native depuis l'engine via queue
- **Downscale** vers la résolution LED configurée avec la méthode d'interpolation choisie (cv2.resize)
- Si pas de nouvelle frame, renvoie la dernière frame connue (jamais de freeze en live)

**Format UDP :**
- Buffer de bytes : pixels RGB séquentiels, row-major (ligne par ligne, gauche à droite, haut en bas)
- Chaque composante clippée à [0, 254] pour éviter le byte réservé 0xFF
- Broadcast sur l'adresse et le port configurés
- Activé/désactivé via le bouton ON/OFF dans la fenêtre OUTPUT

**Fenêtre OUTPUT :**
- Fenêtre séparée, déplaçable sur un second écran
- Affiche la frame downscalée upscalée en nearest neighbor pour visualiser les pixels LED
- Affiche le mode d'interpolation actif (ex: "sampling ! BICUBIC")
- **Bouton ON/OFF broadcast** : active ou désactive l'envoi UDP en temps réel (permet de couper la sortie LED sans fermer le logiciel)

### 9. MIDI (midi_handler.py + midi_config.py)

**Contrôles assignables via MIDI :**
- Crossfader (CC)
- FPS Deck A (CC)
- FPS Deck B (CC)
- HUE (CC)
- SATURATION (CC)
- VELOCITY (CC)
- RED (CC)
- GREEN (CC)
- BLUE (CC)
- Play/Pause Deck A (Note)
- Play/Pause Deck B (Note)
- Freeze/broadcast toggle (Note)

**Implémentation :**
- `python-rtmidi` dans un QThread dédié
- Les événements MIDI sont convertis en Qt Signals
- Support des CC (Control Change) pour les sliders et Note On/Off pour les boutons
- Learn mode : l'UI capte le prochain message MIDI reçu et l'associe au contrôle

### 10. Undo/Redo — onglet EDIT (undo_manager.py)

- Système global, pas limité à la frame courante (contrairement à SendPix2)
- Pile d'actions (pas de pile d'états complets, trop coûteux en mémoire)
- Supporte : dessin sur pixel, changement de frame picture, ajout/suppression de frame, copier/coller
- Raccourcis : Ctrl+Z (undo), Ctrl+Shift+Z ou Ctrl+Y (redo)

---

## Raccourcis clavier

| Raccourci | Action | Contexte |
|---|---|---|
| Ctrl+Z | Undo | EDIT |
| Ctrl+Shift+Z | Redo | EDIT |
| Ctrl+C | Copier la frame courante | EDIT |
| Ctrl+V | Coller la frame | EDIT |
| Ctrl+D | Dupliquer la frame courante | EDIT |
| Ctrl+S | Sauvegarder l'animation | EDIT |
| Ctrl+O | Ouvrir une animation | EDIT |
| Ctrl+E | Exporter la séquence | EDIT |
| Espace | Play/Pause | EDIT + LIVE |
| F | LIVE EDIT → Deck A (toggle) | EDIT |
| Shift+F | LIVE EDIT → Deck B (toggle) | EDIT |
| Flèche gauche | Frame précédente | EDIT |
| Flèche droite | Frame suivante | EDIT |
| 1-5 | Taille du pinceau (1×1 à 5×5) | EDIT |
| B | Outil pinceau | EDIT |
| G | Outil pot de peinture | EDIT |
| I | Outil pipette | EDIT |
| O | Toggle onion skin | EDIT |

---

## Priorités de développement

### Phase 1 — Squelette fonctionnel
- [ ] Structure du projet, config manager (config.json), point d'entrée
- [ ] Fenêtre principale avec système d'onglets EDIT / LIVE / MIXETTE
- [ ] Dialog de configuration (settings : résolution, UDP, chemins dossiers)
- [ ] Thread output UDP (boucle de broadcast basique)
- [ ] Fenêtre OUTPUT séparée

### Phase 2 — Onglet EDIT (éditeur pixel)
- [ ] Canvas pixel avec dessin au pinceau (taille 1×1)
- [ ] Timeline verticale (ajout, suppression, sélection de frames)
- [ ] Roue de couleur + palette
- [ ] Sauvegarde/chargement des frames dans la timeline
- [ ] Envoi de la frame éditée vers l'output UDP
- [ ] Tailles de pinceau variables (1-5)
- [ ] Pot de peinture (flood fill BFS)
- [ ] Pipette
- [ ] Onion skin (opacité configurable)
- [ ] Copier/coller de frames
- [ ] Undo/redo global
- [ ] Mode LIVE EDIT (F / Shift+F → envoi vers Deck A/B)

### Phase 3 — Onglet LIVE (animations uniquement)
- [ ] Deck A et Deck B avec preview en résolution native
- [ ] ANIMATIONS BANK : scan du dossier configuré, drag & drop vers les decks
- [ ] Sliders FPS verticaux pour chaque deck
- [ ] Crossfader horizontal avec blend modes (Normal, Multiply, Add, Subtract)
- [ ] Dropdown interpolation (Nearest, Bicubic, Area, Linear)
- [ ] Downscale dans le thread output avec interpolation configurable
- [ ] Settings panel (résolution LED, UDP, chemins dossiers, bouton SEND PIX!)
- [ ] Fenêtre OUTPUT avec affichage pixel agrandi

### Phase 4 — Support MP4
- [ ] Video decoder (OpenCV cv2.VideoCapture)
- [ ] MP4 BANK : scan du dossier configuré, thumbnails et drag & drop
- [ ] Lecture MP4 dans les decks (play, pause, FPS/vitesse)
- [ ] Gestion du blend entre résolutions différentes (anim pixel + vidéo MP4)

### Phase 5 — MIDI & polish
- [ ] MIDI handler (réception, thread dédié)
- [ ] MIDI learn mode dans l'onglet MIXETTE
- [ ] Binding de tous les contrôles (crossfader, FPS, HSV/RGB)
- [ ] Import/export d'animations
- [ ] Packaging (Nuitka)

---

## Contraintes techniques

- **Performances** : les opérations sur les pixels doivent utiliser NumPy (vectorisé), jamais de boucles Python pixel par pixel.
- **Thread safety** : toute communication entre threads passe par Qt Signals ou `queue.Queue`. Jamais d'accès direct à des données partagées.
- **Portabilité** : le logiciel doit fonctionner sur Windows, macOS et Linux.
- **Résolution native dans les decks** : les previews LIVE affichent le contenu en résolution native (pas de downscale). Le downscale vers la résolution LED se fait uniquement dans le thread output.
- **Interface sombre** : thème sombre par défaut, inspiré du prototype UI (fond gris foncé, textes clairs, accent rose/magenta pour les sliders, vert pour l'onglet LIVE actif, rouge pour les labels).
- **Le système multi-faces (facestart/facex/facey) est OBSOLÈTE — ne pas reproduire.**

---

## Référence SendPix2 — Code source

Le code source des fichiers clés de SendPix2 (Godot 4 / GDScript) est inclus ci-dessous comme référence pour la logique métier. **Ne pas reproduire l'architecture Godot** — s'en inspirer pour la logique (bucket fill, format UDP, MIDI) et la réécrire en Python/PySide6/NumPy.

### Mouse_cursor_logic.gd — Config globale (singleton autoload)

```gdscript
extends Node2D

@export var general_theme_color :Color = Color(1.0,.75,0.0)
@export var screen_rez : Vector2i = Vector2i(21,21)

var is_playing :bool = false
var mouse_clicked :bool = false
var broadcastFreq = 342
```

### main.gd — Logique principale (bucket fill, import/export, undo)

```gdscript
extends Control

var LED_screen_res :int = 5
var XYLED_screen_res : Vector2i = Vector2i(21,21)
var bucket_mode :bool = false
var selected_color :Color : get = get_selected_color
var selected_frame_index :int = 0 : set = set_selected_frame_index
var output_update :bool = false
var undo_cursor :int = -1

func get_selected_color() :
	return outils_node.selected_color

func set_selected_frame_index(value :int) :
	selected_frame_index = value
	main_frame_node.whipe_state_stack()

func _ready():
	XYLED_screen_res = mcl.screen_rez
	frame_margin_node.size_flags_stretch_ratio = 2 + float(XYLED_screen_res.x)/float(XYLED_screen_res.y)
	await get_tree().create_timer(0.1).timeout
	main_frame_node.set_pix_margin(false)
	main_frame_node.main = true

# ---- Bucket fill (flood fill 4-connexe, itératif) ----

func bucket_fill(to_color :Color, frame_picture :Array[Color], input_index :int) :
	var input_color :Color = frame_picture[input_index]
	var pix_filled :Array[int]= [input_index]
	frame_picture[input_index] = to_color
	var frame_picture_changed :bool = true
	while frame_picture_changed :
		frame_picture_changed = false
		for i in range(frame_picture.size()) :
			if !pix_filled.has(i) :
				if frame_picture[i] == input_color :
					if has_filled_neighboors(i,pix_filled) :
						frame_picture[i] = to_color
						pix_filled.append(i)
						frame_picture_changed = true
		main_frame_node.set_frame_picture(frame_picture)
	return frame_picture

func get_pix_neighboors_index(pix_index :int) -> Array[int] :
	var neighboors :Array[int]
	if (pix_index+1)%XYLED_screen_res.x != 0 :
		neighboors.append(pix_index+1)
	if (pix_index-1)%XYLED_screen_res.x != (XYLED_screen_res.x-1) :
		neighboors.append(pix_index-1)
	if (pix_index-XYLED_screen_res.x) > 0 :
		neighboors.append(pix_index-XYLED_screen_res.x)
	if (pix_index+XYLED_screen_res.x)/XYLED_screen_res.x < XYLED_screen_res.y:
		neighboors.append(pix_index+XYLED_screen_res.x)
	return neighboors

func has_filled_neighboors(index :int, pix_filled_array :Array[int]) -> bool :
	for neighboor_index in get_pix_neighboors_index(index) :
		if neighboor_index in pix_filled_array :
			return true
	return false

# ---- Export / Import ----

func export(user_name :String) :
	var animation_pictures = tl_node.get_frame_picture_sequence()
	var img = Image.create(XYLED_screen_res.x,XYLED_screen_res.y,false,Image.FORMAT_RGBA8)
	var frame_compte :int = 0
	var save_path = OS.get_system_dir(OS.SYSTEM_DIR_PICTURES) + '/LED_exports'
	for pic in animation_pictures :
		for i in range(len(pic)) :
			img.set_pixelv(index_to_coordinate(i),pic[i])
		img.save_png(save_path+"/"+user_name+"/"+str(frame_compte)+".png")
		frame_compte += 1

func index_to_coordinate(indx :int) :
	return Vector2i(indx%XYLED_screen_res.x,indx/XYLED_screen_res.x)

func resize_ext_img(ext_img : Image) -> Image :
	if ext_img.get_height() > XYLED_screen_res.y or ext_img.get_width() > XYLED_screen_res.x :
		var extratio :float = ext_img.get_width()/ext_img.get_height()
		var intratio : float = float(XYLED_screen_res.x)/float(XYLED_screen_res.y)
		if extratio >= intratio :
			ext_img.crop(ext_img.get_height()*intratio,ext_img.get_height())
		else :
			ext_img.crop(ext_img.get_width(),ext_img.get_width()/intratio)
		ext_img.resize(XYLED_screen_res.x,XYLED_screen_res.y,Image.INTERPOLATE_TRILINEAR)
	return ext_img

func img_picture_from_image(ext_img :Image) -> Array[Color] :
	var img_picture : Array[Color]
	for y in range(ext_img.get_height()) :
		for x in range(ext_img.get_width()) :
			img_picture.append(ext_img.get_pixel(x,y))
	return img_picture

# ---- Undo ----

func undo() :
	var frame_picture_to_restore
	if is_undoable() :
		frame_picture_to_restore = main_frame_node.state_stack[undo_cursor]
		main_frame_node.set_frame_picture(frame_picture_to_restore)
		tl_node.selected.set_frame_picture(frame_picture_to_restore)
		if selected_frame_index >0 :
			main_frame_node.set_ghost_frame(tl_node.get_frame(selected_frame_index-1).get_frame_picture())
		undo_cursor -= 1
```

### Output.gd — Broadcast UDP (le format de données est la référence clé)

```gdscript
extends Control

var playing :bool : set = set_playing
var speed :float : set = set_speed
var frame_time :float
var delta_buff :float = 0

var UDPbroadcast = PacketPeerUDP.new()
var UDPPORT = 37020
var broadcastImageArray : PackedByteArray
var broadcastFreq :int = 500

# OBSOLÈTE — ne pas reproduire
var facestart = [0,16,40]
var facex = [4,6,4]
var facey=[4,4,4]
var npix = 56

func set_playing(val :bool) :
	playing = val
	if val : delta_buff = 0

func set_speed(val :float) :
	speed = val
	frame_time = 1./val

func _ready():
	UDPbroadcast.set_broadcast_enabled(true)
	UDPbroadcast.set_dest_address('255.255.255.255',UDPPORT)
	$Timer.wait_time = 1./float(broadcastFreq)
	$Timer.start()

func _process(delta):
	if playing :
		delta_buff += delta
		if delta_buff >= frame_time :
			as_output.frame = (as_output.frame +1)%as_output.sprite_frames.get_frame_count('default')
			delta_buff = delta_buff - frame_time
	broadcastImageArray = get_frame_buffer()

func broadcast() :
	UDPbroadcast.put_packet(broadcastImageArray)

# Clé : le buffer est construit pixel par pixel, RGB, clippé à 254
func get_frame_buffer() -> PackedByteArray :
	var buff = PackedByteArray()
	var img :Image = as_output.sprite_frames.get_frame_texture("default",as_output.frame).get_image()
	img.convert(Image.FORMAT_RGB8)
	for y in range(img.get_height()):
		for x in range(img.get_width()):
			var c = img.get_pixel(x, y)
			buff.append(clampi(int(c.r * 255), 0, 254))
			buff.append(clampi(int(c.g * 255), 0, 254))
			buff.append(clampi(int(c.b * 255), 0, 254))
	return buff
```

### Frame.gd — Grille de pixels et dessin

```gdscript
extends Control

var frame_picture :Array[Color]
var ghost_frame :Array[Color]
var ghost :bool = false
var main :bool = false
var state_stack :Array = []
var max_stack = 50

func _ready():
	init_frame()

func init_frame() :
	frame_picture = []
	for i in range(mcl.screen_rez.x * mcl.screen_rez.y) :
		frame_picture.append(Color(0,0,0))

func set_pix_color(i :int, color :Color) :
	frame_picture[i] = color
	queue_redraw()

func set_frame_picture(fp :Array[Color]) :
	frame_picture = fp.duplicate()
	queue_redraw()

func set_ghost_frame(gfp :Array[Color]) :
	ghost_frame = gfp.duplicate()

func get_frame_picture() -> Array[Color] :
	return frame_picture.duplicate()

func whipe_state_stack() :
	state_stack.clear()

func _draw():
	for i in range(frame_picture.size()) :
		var x = i % mcl.screen_rez.x
		var y = i / mcl.screen_rez.x
		var color = frame_picture[i]
		# Ghost : si pixel noir et ghost actif, affiche le ghost à 30% d'opacité
		if ghost and color == Color(0,0,0) and ghost_frame.size() > i :
			color = ghost_frame[i] * Color(1,1,1,0.3)
		draw_rect(rect, color)
```

### mixette.gd — MIDI + sliders HSV/RGB

```gdscript
extends Control

var midi_on = false
var H_on = false
var H :float = 0.

func _ready():
	OS.open_midi_inputs()
	print(OS.get_connected_midi_inputs())

func _input(input_event):
	if input_event is InputEventMIDI:
		_process_midi_event(input_event)

func _process_midi_event(midi_event: InputEventMIDI):
	# Hardcodé pour un contrôleur spécifique — à remplacer par learn mode
	match midi_event.controller_number :
		1 : H = midi_event.controller_value
		2 : $sliders/saturation.value = midi_event.controller_value
		3 : $sliders/velocity.value = midi_event.controller_value
		4 : $sliders/red_slider.value = midi_event.controller_value
		5 : $sliders/green_slider.value = midi_event.controller_value
		6 : $sliders/blue_slider.value = midi_event.controller_value

# Logique de correction couleur — à réécrire en NumPy vectorisé
func get_mixette_correction(color :Color) -> Color :
	var output_color = color
	if H_on :
		output_color.h = fmod(output_color.h + H/127., 1.)
	output_color.s = clampf(output_color.s * ($sliders/saturation.value/64.), 0., 1.)
	output_color.v = clampf(output_color.v * ($sliders/velocity.value/64.), 0., 1.)
	output_color.r = clampf(output_color.r * ($sliders/red_slider.value/64.), 0., 1.)
	output_color.g = clampf(output_color.g * ($sliders/green_slider.value/64.), 0., 1.)
	output_color.b = clampf(output_color.b * ($sliders/blue_slider.value/64.), 0., 1.)
	return output_color
```

### color_selection.gd — Roue de couleur

```gdscript
extends Control

var selected_color :Color = Color.WHITE
var color_h :float = 0.0
var color_s :float = 0.0
var color_v :float = 1.0

func _on_color_wheel_input(event):
	if event is InputEventMouseButton or (event is InputEventMouseMotion and mcl.mouse_clicked):
		var center = size / 2
		var pos = event.position - center
		var angle = atan2(pos.y, pos.x)
		var dist = pos.length() / (size.x / 2)
		color_h = fmod(angle / (2 * PI) + 1.0, 1.0)
		color_s = clamp(dist, 0.0, 1.0)
		update_color()

func update_color():
	selected_color = Color.from_hsv(color_h, color_s, color_v)
	queue_redraw()
```
