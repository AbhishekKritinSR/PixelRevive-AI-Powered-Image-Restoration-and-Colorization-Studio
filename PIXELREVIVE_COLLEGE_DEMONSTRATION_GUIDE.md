# PIXELREVIVE – COLLEGE DEMONSTRATION & LIVE PRESENTATION GUIDE
## Step-by-Step Examiner Demonstration Script, Test Cases, Live UI Walkthrough and Troubleshooting Protocols

**Project:** PixelRevive – AI-Powered Image Restoration  
**Target Audience:** Final Project Review Committee, Academic Examiners, and Computer Vision Evaluators  
**Estimated Presentation Duration:** 12–15 Minutes  
**Demonstration Mode:** Live Web Application (React + Vite Frontend & FastAPI Backend)  
**Repository Location:** `C:\Users\abhis\Downloads\restoration_project`

---

## 1. Demonstration Setup & Pre-Flight Checklist

### Step 1: Start Backend Server
Open a PowerShell terminal in `C:\Users\abhis\Downloads\restoration_project`:
```powershell
# Activate virtual environment and start FastAPI ASGI application
.\.venv\Scripts\Activate.ps1
uvicorn backend.src.api.app:app --host 127.0.0.1 --port 8000 --reload
```
*Verification:* Confirm terminal displays `Application startup complete` and open `http://127.0.0.1:8000/docs` to verify OpenAPI documentation.

### Step 2: Start Frontend Development Server
Open a second PowerShell terminal:
```powershell
cd frontend
npm run dev
```
*Verification:* Confirm terminal displays `VITE v6.1.0 ready in ... Local: http://localhost:5173/`. Open `http://localhost:5173` in Google Chrome or Microsoft Edge.

### Step 3: Verify Preloaded Demonstration Assets
Confirm the demonstration cohort files are readily accessible in:
`C:\Users\abhis\Downloads\restoration_project\tests\real_world\inputs\`
1. `img_01_lincoln_cracked_plate.jpg` (Demo Case 1: Structural Fracture & Inpainting)
2. `img_08_migrant_mother_grain.jpg` (Demo Case 2: Film Grain & Neural Colourization)
3. `img_10_whitman_clean_archival.jpg` (Demo Case 3: Clean-Image Safeguard Bypass)

---

## 2. Live Presentation Script (12–15 Minute Timing)

```
[00:00 - 02:00]  Project Overview, Academic Motivation & BCSE403L Alignment
[02:00 - 06:00]  Demonstration 1: Heavily Damaged Portrait (Abraham Lincoln Cracked Plate)
[06:00 - 09:30]  Demonstration 2: Noisy Archival Photo & Colourization (Migrant Mother)
[09:30 - 12:00]  Demonstration 3: Clean-Image Protection (Walt Whitman Master Scan)
[12:00 - 14:00]  Architecture, Explainability & Automated Testing Evidence
[14:00 - 15:00]  Examiner Q&A & Technical Defense
```

---

## 3. Demonstration Case 1: Heavily Damaged B&W Portrait

### Photograph: Abraham Lincoln (1865 Alexander Gardner "Cracked Plate" Portrait)
- **File:** `tests/real_world/inputs/img_01_lincoln_cracked_plate.jpg`
- **Institution:** Library of Congress / National Portrait Gallery (Public Domain)

### What to Explain to Examiners:
> *"Respected examiners, our first case evaluates PixelRevive on one of the most famous damaged photographs in American history—the last formal portrait of Abraham Lincoln, taken by Alexander Gardner in February 1865. The glass plate cracked immediately after exposure, creating a catastrophic diagonal fissure across Lincoln's skull. Traditional interpolation algorithms like Telea or Navier-Stokes fail on broad structural cracks because they only diffuse border pixels inwards. PixelRevive deploys deep Large Mask Inpainting (LaMa) using Fast Fourier Convolutions to synthesize the missing cranium structure in the frequency domain."*

### Step-by-Step UI Action:
1. Navigate to **Single Restoration** tab on `http://localhost:5173`.
2. Drag and drop `img_01_lincoln_cracked_plate.jpg` into the upload zone.
3. Click **"Preview Damage Mask"** button.
   - *Point out to examiners:* Show how directional Top-Hat morphological filtering isolates the crack boundary without tagging Lincoln's facial features or eyes.
4. Set Pipeline Options:
   - **Scratch & Damage Repair:** `ON`
   - **Inpainting Engine:** Select **"LaMa (Deep Learning)"**
   - **Adaptive Denoise:** `ON`
   - **Adaptive Contrast:** `ON`
   - **Adaptive Sharpening:** `ON`
   - **Colourization:** `OFF`
5. Click **"Restore Image"**.

### What to Show in the Results:
- **Visual Output:** Show that the glass fracture running across Lincoln's hair and cranium is seamlessly inpainted. Zoom in to Lincoln's eyes, nose, and beard to prove that facial identity was 100% preserved.
- **Explainability Diagnostic:** Expand the **Operations Summary** card:
  - `scratch_repair`: *"Applied: 3,001 damaged pixels reconstructed (0.13%) using LAMA."*
  - `contrast`: *"Bypassed: image exhibits adequate natural contrast (std=64.6 >= 22.0)."*
- **Known Limitation to State Honestly:** Point out that on pure CPU execution, LaMa's global Fourier Convolutions require ~25–30 seconds. In production, localized Telea inpainting provides a 2ms fallback for narrow linear scratches.

---

## 4. Demonstration Case 2: Noisy Archival Photograph & Neural Colourization

### Photograph: Dorothea Lange's "Migrant Mother" (1936 Nipomo, California)
- **File:** `tests/real_world/inputs/img_08_migrant_mother_grain.jpg`
- **Institution:** Library of Congress Farm Security Administration Collection (Public Domain)

### What to Explain to Examiners:
> *"Our second demonstration evaluates two complementary challenges: heavy nitrate film grain and historical chrominance synthesis. Standard denoising algorithms create a 'plastic skin' effect by wiping away fine human textures. PixelRevive uses an adaptive Non-Local Means filter combined with texture-guided residual blending, which preserves gradient edges where Sobel magnitude exceeds threshold. Subsequently, our Zhang Caffe deep neural network predicts authentic chrominance distributions, guided by bilateral spatial constraints to avoid color bleeding."*

### Step-by-Step UI Action:
1. Upload `img_08_migrant_mother_grain.jpg`.
2. Set Pipeline Options:
   - **Scratch & Damage Repair:** `ON` (Engine: Telea)
   - **Adaptive Denoise:** `ON`
   - **Adaptive Contrast:** `ON`
   - **Adaptive Sharpening:** `ON`
   - **Deep Colourization:** `ON`
3. Click **"Restore Image"**.

### What to Show in the Results:
- **Visual Output:** Show the interactive before-and-after slider. Highlight the natural warmth added to the mother's face and children's skin.
- **Enlarged Detail:** Zoom into the eye wrinkles and infant's hair strands: demonstrate that fine textures were preserved rather than blurred into plastic.
- **Quantitative Metrics:**
  - Noise suppression: **44.2%** ($\sigma_{\text{noise}}: 2.51 \to 1.40$).
  - Colorfulness: Rose from **0.00** to **31.37** (natural photographic range; avoids neon oversaturation).
- **Academic Limitation to State Honestly:** Remind examiners that AI colourization predicts statistically plausible color distributions based on ImageNet luminance training; it does not scientifically reconstruct historical fabric dye chemistry.

---

## 5. Demonstration Case 3: Clean Archival Reference (Knowing When NOT to Restore)

### Photograph: Walt Whitman in Wide-Brimmed Hat (1887 George C. Cox)
- **File:** `tests/real_world/inputs/img_10_whitman_clean_archival.jpg`
- **Institution:** Library of Congress Feinberg-Whitman Collection (Public Domain)

### What to Explain to Examiners:
> *"A critical design flaw in many consumer AI enhancement apps is that they unconditionally apply aggressive filters to every image, ruining clean historical scans with crushed contrast, ringing halos, and plastic smoothing. In Phase 3.5, we implemented adaptive clean-image safeguards based on luminance standard deviation, dynamic range percentiles, and noise variance. In this third demo, we show how PixelRevive intelligently evaluates a master archival photograph and bypasses destructive filters."*

### Step-by-Step UI Action:
1. Upload `img_10_whitman_clean_archival.jpg`.
2. Leave all default options active:
   - **Scratch Repair:** `OFF` (Default)
   - **Adaptive Denoise:** `ON`
   - **Adaptive Contrast:** `ON`
   - **Adaptive Sharpening:** `ON`
   - **Colourization:** `OFF`
3. Click **"Restore Image"**.

### What to Show in the Results:
- **Operations Summary (The Critical Evidence):**
  - `denoising`: *"Bypassed: measured noise variance is pristine (sigma=0.84 < 1.5). Filtering skipped to preserve photographic clarity."*
  - `contrast`: *"Bypassed: image exhibits adequate natural contrast (std=71.4 >= 22.0, dynamic range=234.0 >= 65.0). CLAHE skipped to prevent over-enhancement."*
- **Visual Output:** Show that the master photograph's rich tonal range, hat fibers, and crisp white beard whiskers are preserved with 100% fidelity.
- **Verification of Phase 3.5 Benchmark:** Mention that in the automated Category H clean-image benchmark, this protection guarantees **$\text{SSIM} = 1.000000$** and **$0$ modified pixels**.

---

## 6. Demonstration Case 4 (Bonus): Interactive Damage Mask Preview & Batch Processing

If examiners ask to see batch workflows or interactive masks:
1. Click **"Batch Restoration"** tab in navigation bar.
2. Select 3 files simultaneously (`img_03_mcrae`, `img_04_butler`, `img_05_vanderbilt`).
3. Set common options and click **"Process Batch"**.
4. Show how the batch API processes images sequentially with progress tracking and individual diagnostic reports.

---

## 7. Troubleshooting Protocols & Fallbacks During Live Presentation

| Potential Issue During Live Demo | Immediate Remediation / Fallback |
| :--- | :--- |
| **Port 8000 already in use** | Run `Get-Process python | Stop-Process` in PowerShell and restart uvicorn. |
| **Browser caching stale UI** | Press `Ctrl + Shift + R` (Hard Reload) in Chrome/Edge. |
| **LaMa CPU execution takes too long** | Explain: *"LaMa Fast Fourier Convolutions run on a 512x512 neural grid. While it finishes, let me show you the precomputed visual gallery composite."* Open [`tests/real_world/reports/visual_gallery/index.html`](file:///C:/Users/abhis/Downloads/restoration_project/tests/real_world/reports/visual_gallery/index.html). |
| **Offline demonstration environment** | All models (`colorization_release_v2.caffemodel`, `lama.onnx`, `RealESRGAN_x4plus.onnx`, `FSRCNN_x2.pb`) and test photographs reside locally on disk in `model/` and `tests/real_world/inputs/`. Zero internet access is required! |

---

## 8. Summary Checklist Before Entering Examination Room

- [x] Backend running on `http://127.0.0.1:8000` (FastAPI).
- [x] Frontend running on `http://localhost:5173` (Vite).
- [x] All 10 input photographs present in `tests/real_world/inputs/`.
- [x] Visual gallery accessible at `tests/real_world/reports/visual_gallery/index.html`.
- [x] Automated test suite verified (307 passed).
- [x] Printed or digital copies of `PIXELREVIVE_TECHNICAL_VIVA_REFERENCE.md` ready for reference.
