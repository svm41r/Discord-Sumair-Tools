# 🎬 SVM41R MASTER EDITOR TOOL — COMPLETE TECHNICAL MANUAL

> **Author**: Sumair Tools Engineering Architecture  
> **Platform**: Adobe After Effects CC 2020 – 2026+  
> **Interface**: Dark Industrial CEP & ExtendScript Engine (`0xFF0033`)  
> **Reference File**: `SVM41R Master Editor Tool.jsx`

---

## 📑 SECTION 1: CAPTION & TEXT HUB (`[Ｔ] TAB 0`)

### 1.1 Text Animation
* **`Ｔ TextOpac`**
  * 🎯 **What it does**: Applies instant smooth text opacity fade-in animation.
  * ⚙️ **Under the hood**: Loads `Opac text.ffx` from preset directories and executes `layer.applyPreset()`.
  * ⚡ **Ideal Use Case**: Quick typographic title reveals and subtitles.
  * ⚠️ **Prerequisites**: Selected layer must be a text layer inside an active composition.
* **`⏶ Textup`**
  * 🎯 **What it does**: Applies smooth vertical slide-up text entrance animation.
  * ⚙️ **Under the hood**: Loads `text up anim.ffx` and applies positional keyframe animators.
  * ⚡ **Ideal Use Case**: Kinetic typography and pop-in social media captions.
  * ⚠️ **Prerequisites**: Text layer selected; playhead at intended start frame.
* **`⏷ Textdown`**
  * 🎯 **What it does**: Applies smooth slide-down entrance animation.
  * ⚙️ **Under the hood**: Loads `text down.ffx` to animate position and opacity downward.
  * ⚡ **Ideal Use Case**: Header transitions and banner captions.
* **`📌 Sweap`**
  * 🎯 **What it does**: Generates a dynamic sweep shadow effect across letters.
  * ⚙️ **Under the hood**: Loads `Sweap.SShad.ffx` with range selectors.
  * ⚡ **Ideal Use Case**: Emphasizing punch words and high-energy motion design.

---

### 1.2 Text Utilities
* **`🔤 Capital`**
  * 🎯 **What it does**: Capitalizes the first letter of each word in the selected text.
  * ⚙️ **Under the hood**: Executes `CapitalizeFirstLetters.jsx`, parsing `Source Text` string via regex.
  * ⚡ **Ideal Use Case**: Instant title-casing for raw imported transcripts.
* **`— No !.,`**
  * 🎯 **What it does**: Strips out all punctuation marks (commas, periods, exclamation points).
  * ⚙️ **Under the hood**: Executes `RemoveCommasAndPeriods.jsx` to clean subtitles.
  * ⚡ **Ideal Use Case**: Short-form video captions (TikTok / Reels / Shorts aesthetic).
* **`👁 Cuss Hide`**
  * 🎯 **What it does**: Automatically censors and bleep-stars profane words.
  * ⚙️ **Under the hood**: Executes `CensorBadWords.jsx` using dictionary replacement.
  * ⚡ **Ideal Use Case**: Monetization compliance for YouTube / TikTok.
* **`🔥 Glow`**
  * 🎯 **What it does**: Applies high-end cinematic Deep Glow to text.
  * ⚙️ **Under the hood**: Loads `Deep glow.ffx` with optical falloff parameters.
  * ⚡ **Ideal Use Case**: High-contrast dark cyberpunk or neon subtitle styling.

---

### 1.3 Caption Tools
* **`🎬 Captions`**
  * 🎯 **What it does**: Automatically imports SRT subtitle files and converts them to AE text layers.
  * ⚙️ **Under the hood**: Executes `ImportSRT.jsx`, parsing timestamp chunks and building layers.
  * ⚡ **Ideal Use Case**: Importing transcribed voiceovers in seconds.
* **`≡ Lb 4x` & `≕ Lb 2x`**
  * 🎯 **What it does**: Formats multi-word subtitles into 4-word or 2-word rhythmic lines.
  * ⚙️ **Under the hood**: Runs `LB 4.jsx` and `LB 2.jsx` string tokenizers with line breaks `\r`.
  * ⚡ **Ideal Use Case**: Maximizing viewer retention on vertical reels.
* **`↗ Gradient`**
  * 🎯 **What it does**: Applies stylized background gradient styling.
  * ⚙️ **Under the hood**: Applies `cory bg.ffx` preset to selected background solids.

---

### 1.4 Explode Words & Typography Shifter
* **`💥 Explode Words`**
  * 🎯 **What it does**: Splits a text layer into individual single-word layers positioned identically.
  * ⚙️ **Under the hood**: Measures character bounds, duplicates layer per word, hides adjacent characters, and sets anchor points.
  * ⚡ **Ideal Use Case**: Word-by-word kinetic typography animation.
* **`⏶ Up Longer`**
  * 🎯 **What it does**: Shifts the first word of Layer 1 to the end of Layer 2.
  * ⚙️ **Under the hood**: Updates `Source Text` across consecutive caption layers.
  * ⚡ **Ideal Use Case**: Balancing caption reading pace when one line is too short.
* **`⏷ Down Longer`**
  * 🎯 **What it does**: Shifts the last word of Layer 2 to the start of Layer 1.
  * ⚙️ **Under the hood**: String manipulation across selected adjacent layers.

---

### 1.5 Signature Font Split & 4-Tier Palette
* **`Pick Font` & `Apply ALL`**
  * 🎯 **What it does**: Grabs the font family from the selected layer and can apply it to **every comp** in the project.
  * ⚙️ **Under the hood**: Recursively scans `app.project.items` for text layers and updates `SourceText.font`.
* **Signature Font Dropdown**
  * Features `TacticSans-BldIt`, `Coolvetica`, `Europa Grotesk SH Med`, plus all installed system fonts.
* **Color Palette Manager**
  * **Warm** (`#FF5454`), **Mint** (`#54FF8C`), **Sky** (`#54ABFF`), **Sun** (`#FFD154`) with interactive eyedropper.
* **`Split & Apply`**
  * 🎯 **What it does**: Splits 2-line captions: Line 1 receives signature font; Line 2 receives active palette color and animation presets.
* **`NUKE` Cleaner**
  * 🎯 **What it does**: Wipes all text animators, presets, and effects from selected layers to restore a clean state.

---

## 🛠️ SECTION 2: LAYER & TECHNICAL WORKFLOW (`[⧉] TAB 1`)

### 2.1 Layer Shortcuts & Zoom Presets
* **`☉ Null`**: Spawns an empty Null layer and immediately parents all selected layers to it.
* **`⬚ UnPrecomp`**: Executes `unpi.jsx`, unpacking precompositions into the root comp without losing layer alignment.
* **`⤾ Bounce`**: Executes `ApplyScaleBounce.jsx`, generating inertia-damped spring bounce expressions on Scale.
* **`💎 Zooms`**: Applies standard cinematic camera zoom preset (`zoom (1).ffx`).
* **`↔ Slow Z In` & `↕ Out Z`**: Smooth slow push-in or pull-out camera movement presets.
* **`⬚ Precomp`**: Instant precomposition wrapper for selected layers.

---

### 2.2 Layer Operations & Time Shifting
* **`✂ Split`**: Cuts the selected layer cleanly at the playhead time without moving selection.
* **`← Back`**: Snaps the layer's `outPoint` directly to the playhead time.
* **`→ Forward`**: Snaps the layer's `inPoint` directly to the playhead time.
* **`↓ Trim In` & `↑ Trim Out`**: Crops the layer boundaries without shifting layer position.
* **`Fit Comp`**: Proportionally fits the width of selected layers to match composition resolution.

---

### 2.3 9-Point Anchor Point Matrix
Instant one-click anchor point snapping without moving layer visuals in the viewport:
* `↖` Top-Left | `▲` Top-Center | `↗` Top-Right
* `←` Mid-Left | `☉` True Center | `→` Mid-Right
* `↙` Bottom-Left | `▼` Bottom-Center | `⤵` Bottom-Right

---

### 2.4 Batch Operations & Comp Reaper
* **`Sequence`**: Sequences selected layers head-to-tail starting from the playhead.
* **`To Work`**: Crops selected layers precisely to the active Work Area (`workAreaStart` to `workAreaDuration`).
* **`Auto Keys`**: Enables Time Remapping on layers and adds boundary keyframes at In and Out points.
* **`📌 Marker`**: Drops timeline markers across all selected layers at the current time.
* **`☄ MBlur` / `🙈 Shy` / `👤 Solo`**: Instant switches batch toggling across multiple layers.
* **`Swap Sel`**: Swaps the timeline positions and stacking index of two selected layers.
* **`30>60fps` & `60>30fps`**: Batch re-times all project compositions between 30 and 60 FPS.
* **`⏱️ Trim Comp`**: Snaps the active composition duration directly to current playhead time.

---

### 2.5 Quick Alignment Footer
One-click alignment commands directly in the bottom footer:
* `≡` Align Left | `⧓` Align H-Center | `☰` Align Right
* `⏶` Align Top | `⧓` Align V-Center | `⏷` Align Bottom | `☉` Center in View
