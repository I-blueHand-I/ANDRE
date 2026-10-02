# ANDRE (ex-SendPix3)

Logiciel d'edition d'animation pixel art et de VJing live pour piloter des installations LED en temps reel. Troisieme iteration de SendPix, reconstruit from scratch en Python + PySide6.

## Deux modes d'utilisation

- **EDIT** : creation et edition d'animations pixel art frame par frame (canvas, timeline, outils de dessin, roue de couleur)
- **LIVE** : mix en temps reel de deux sources (animations pixel art ou videos MP4) avec crossfader, blend modes, corrections couleur HSV/RGB, et sortie vers matrices LED via UDP

Controlable via un controleur MIDI physique (mixette custom).

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.11+ |
| Framework UI | PySide6 (Qt6) |
| Manipulation d'images | NumPy (arrays RGB uint8) |
| Chargement d'images | Pillow (PIL) |
| Decodage video MP4 | OpenCV (cv2.VideoCapture) |
| MIDI | python-rtmidi |
| Reseau (UDP) | socket (stdlib) |
| Configuration | JSON (config.json a la racine) |
| Theme | JSON (themes/default.json) |

## Architecture a 3 threads

```
THREAD PRINCIPAL (UI PySide6)
  - Onglets EDIT / LIVE / MIXETTE
  - MIDI handler
        |
        | Qt Signals (thread-safe)
        v
THREAD ENGINE (RenderEngine QThread)
  - Deck A + Deck B (Animation ou Video)
  - Mixer (blend modes + crossfader alpha)
  - Corrections couleur HSV/RGB
  - Strobe
        |
        | queue.Queue (frame RGB numpy)
        v
THREAD OUTPUT (UDPOutput QThread)
  - Downscale vers resolution LED (cv2.resize, interpolation configurable)
  - Clip [0, 254] + broadcast UDP
  - Fenetre OUTPUT (preview)
```

Communication inter-threads : Qt Signals + queue.Queue. Jamais d'acces direct a des donnees partagees.

## Structure du code

```
main.py                     # Point d'entree, charge fonts, config, lance MainWindow
config.py                   # Config JSON (led_resolution, udp, midi_bindings, palette...)
utils.py                    # Helpers (app_dir, etc.)

engine/
  render_engine.py          # QThread principal : boucle de rendu, mix, HSV/RGB, strobe
  deck.py                   # Deck A/B : lecture Animation ou Video a FPS configurable
  animation.py              # Animation pixel art (dossier de PNG -> liste numpy arrays)
  video.py                  # Video MP4/MOV via cv2 (lazy VideoCapture, preview preload)
  edit_animation.py         # Animation en cours d'edition (onglet EDIT)
  blend_modes.py            # Fonctions de blend NumPy (normal, screen, overlay, multiply, add, subtract, difference, lighten, darken)
  resize.py                 # Resize helpers (cv2.resize avec interpolation configurable)
  constants.py              # Constantes (ENGINE_FPS, SIDE_A, SIDE_B)

ui/
  main_window.py            # Fenetre principale, systeme d'onglets, orchestration MIDI
  config_dialog.py          # Dialog de configuration (resolution, UDP, chemins dossiers)
  output_window.py          # Fenetre OUTPUT separee (preview pixels agrandis)
  keybind.py                # Gestionnaire de raccourcis clavier configurables
  theme.py                  # Charge le theme depuis themes/default.json
  shared_styles.py          # Styles CSS partages
  shared_widgets.py         # Widgets reutilisables

  edit/                     # --- Onglet EDIT ---
    edit_tab.py             # Layout de l'onglet
    canvas.py               # Widget canvas d'edition pixel (paintEvent)
    timeline.py             # Timeline verticale de frames
    frame_thumb.py          # Miniature d'une frame
    colorwheel.py           # Roue de couleur custom
    palette.py              # Palette de couleurs sauvegardables
    tools.py                # Barre d'outils (pinceau, tailles, pot de peinture, pipette)
    history.py              # Undo/redo
    export_widget.py        # Export d'animations

  live/                     # --- Onglet LIVE ---
    live_tab.py             # Layout de l'onglet
    deck_preview.py         # Widget preview d'un deck
    crossfader.py           # Crossfader horizontal
    bank_widget.py          # Widget bank (grille de thumbnails)
    bank_items.py           # Scan des dossiers, chargement des items

  mixette/                  # --- Onglet MIXETTE ---
    mixette_tab.py          # Sliders HSV/RGB + boutons midi bind

output/
  udp_output.py             # QThread : downscale + broadcast UDP

midi/
  midi_manager.py           # Reception MIDI via python-rtmidi, dispatch Qt Signals
```

## Representation des donnees

- **Frame pixel art** : `np.ndarray` shape `(H, W, 3)` uint8 RGB -- petite taille (ex: 21x16)
- **Frame video MP4** : `np.ndarray` shape `(H, W, 3)` uint8 RGB -- taille native (ex: 1920x1080)
- **Animation** : liste de frames numpy (`Animation.frames`)
- **Video** : streaming sequentiel via `cv2.VideoCapture` (lazy open, ferme quand pas en lecture)
- **Crossfader** : `output = (1-alpha) * deck_a + alpha * deck_b` (NumPy vectorise)
- **Corrections couleur** : operations NumPy sur HSV (cv2.cvtColor RGB<->HSV)
- **Downscale LED** : `cv2.resize()` avec interpolation configurable (NEAREST, CUBIC, AREA, LINEAR)

## Format UDP (sortie LED)

Buffer de bytes : pixels RGB sequentiels, row-major (ligne par ligne, gauche a droite, haut en bas). Chaque composante clippee a [0, 254] (0xFF reserve). Broadcast sur adresse/port configurables (defaut: 255.255.255.255:37020).

## Configuration (config.json)

- `led_resolution` : [W, H] de la matrice LED
- `udp_port`, `udp_address` : parametres broadcast
- `animations_folder` : chemin vers le dossier d'animations (sous-dossiers de PNG numerotes)
- `mp4_folder` : chemin vers le dossier de videos MP4
- `midi_device`, `midi_bindings` : config MIDI (learn mode, CC/Note bindings)
- `key_bindings` : raccourcis clavier configurables
- `palette` : couleurs sauvegardees

## Conventions de code

- Performances : operations pixel en NumPy vectorise, jamais de boucles Python pixel par pixel
- Thread safety : Qt Signals ou queue.Queue pour la communication inter-threads
- Frames toujours en RGB (pas BGR), dtype uint8
- Le downscale vers resolution LED se fait uniquement dans le thread output, jamais dans les previews
- Les previews LIVE affichent le contenu en resolution native
- Theme sombre (fond gris fonce, textes clairs, accent rose #e0156b)
- Font : "terminal grotesque"

## Lancer le projet

```bash
cd /Users/hugobijaoui/Desktop/ANDRE-main
source venv/bin/activate
python main.py
```

## Dependances

```
PySide6>=6.5.0
numpy>=1.24.0
Pillow>=10.0.0
opencv-python>=4.8.0
python-rtmidi>=1.5.0
```
