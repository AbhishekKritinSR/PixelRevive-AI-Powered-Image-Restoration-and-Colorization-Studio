# 🎨 PixelRevive – AI-Powered Image Restoration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)

**PixelRevive** is an end-to-end photo restoration and colorization application. It combines classical computer vision techniques (Non-Local Means denoising, CLAHE contrast enhancement, Laplacian sharpening) with a deep convolutional neural network (Zhang et al., ECCV 2016) to restore degraded historical photographs and synthesize plausible, vivid colors.

Built with a decoupled, high-performance architecture: a **FastAPI** asynchronous backend serving an interactive **React 18 + TypeScript** Single Page Application (SPA).

---

## Architecture Overview

```mermaid
flowchart TD
    Client["React 18 + TypeScript SPA<br/>(Vite @ http://localhost:5173)"]
    API["FastAPI REST API<br/>(Uvicorn @ http://127.0.0.1:8000)"]
    
    subgraph Engine ["Image Processing Core"]
        Pre["Upload Validation & 1600px Clamp"]
        Enhance["Classical Enhancement<br/>(Denoise, CLAHE, Sharpen)"]
        Colorize["Caffe DNN Colorization<br/>(Zhang et al. ECCV 2016)"]
        Metrics["Quality & Timing Metrics"]
    end

    Client -->|HTTP / FormData| API
    API --> Pre
    Pre --> Enhance
    Enhance --> Colorize
    Colorize --> Metrics
    Metrics -->|JSON + Image Payload| API
    API -->|REST Response| Client
```

### Decoupled Stack
- **Frontend SPA (`frontend/`)**: React 18, TypeScript, Tailwind CSS, Lucide icons, and an interactive before/after split slider.
- **Backend API (`backend/`)**: FastAPI, Starlette, Pydantic schemas, asynchronous file handling, and structured REST endpoints (`/api/v1/process`, `/api/v1/batch/process`, `/api/v1/health`, `/api/v1/models/status`).
- **Processing Engine (`src/` & `backend/src/processing/`)**: OpenCV (`opencv-python-headless`), NumPy, and Caffe deep learning model loaded via OpenCV's `dnn` module.

> **Note on Architecture Evolution:** Streamlit prototype (`app.py`) was formally retired in Phase 4. React + TypeScript with FastAPI is now the sole production interface.

---

## Key Features

- **Independently Configurable Pipeline**: Toggle classical restoration (denoising, contrast enhancement, sharpening) and deep learning colorization independently or execute them together.
- **Deep Learning Colorization**: Employs the Zhang et al. (2016) architecture via OpenCV `dnn`, predicting color distributions across 313 quantized $(a, b)$ bins conditioned exclusively on the CIE LAB lightness channel ($L$).
- **Interactive Split Comparison**: Full-featured drag-to-reveal comparison slider with dual-viewport alignment and real-time zoom.
- **Batch Processing**: Concurrently upload up to 10 images with individual progress tracking, individual downloads, and combined ZIP download.
- **Production Validation**: Strict validation for image format (`.jpg`, `.jpeg`, `.png`, `.webp`), mime-type, 25 MB payload limit, and automatic aspect-preserving downscaling for images exceeding 1600px.
- **Real-Time Quality Metrics**: Execution latency breakdown (ms), inference device detection (CPU/CUDA), and before/after heuristic contrast and sharpness deltas.
- **Archival Scratch Repair & Inpainting**: Multi-orientation morphological detection (horizontal, vertical, diagonal) and OpenCV inpainting (`INPAINT_TELEA`) with safety coverage guards and ridge vs step-edge false-positive rejection.
- **Exhaustive Automated Test Suite**: 165 automated unit, integration, and route validation tests with 100% pass rate.

---

## Computer Vision & Deep Learning Pipeline

1. **Preprocessing**: Validates upload headers and dimensions, normalizes orientations, and resizes images exceeding 1600px on the longest axis while preserving aspect ratio.
2. **Classical Restoration**:
   - **Archival Scratch Repair & Inpainting (Optional)**: When `repair=true`, detects thin localized scratches and emulsion cracks using directional morphological black-hat and white-hat operators (horizontal, vertical, ~45°, ~135°). Geometric connected-component analysis and neighborhood interquartile range (IQR) checks reject step edges, eyes, hair, and textured patterns. Reconstructs defects using OpenCV Telea Fast Marching Method (`cv2.INPAINT_TELEA`, radius 2–5 px). Disabled by default (`repair=false`) to preserve genuine image details. Includes a 5% coverage safety guard that skips inpainting if marked area exceeds safe limits.
   - **Adaptive Denoising**: Intelligently measures image noise variance ($\hat{\sigma}$) via an Immerkær Laplacian residual operator; skips/minimizes filtering on clean images to preserve micro-textures ($h=0$ to $3$), and applies adaptive Non-Local Means ($h=7$ to $16$) on noisy inputs.
   - **Contrast Enhancement**: Contrast Limited Adaptive Histogram Equalization (CLAHE) applied specifically to the lightness ($L$) channel in LAB color space, avoiding artificial color saturation.
   - **Sharpening**: Unity-gain Laplacian kernel restores fine micro-contrasts lost during denoising without introducing clipping or brightness drift.
3. **LAB Color Space Isolation**: Separates lightness ($L \in [0, 100]$) from chromatic channels ($a, b$).
4. **CNN Color Inference**: The lightness channel is scaled and fed into the 8-block convolutional architecture to predict chromatic distributions over 313 quantized bins.
5. **Reconstruction**: Quantized bins are mapped back to continuous $a, b$ values, fused with the original enhanced $L$ channel, and transformed back to BGR/RGB for display and download.

---

## Project Structure

```text
restoration_project/
├── backend/                  # FastAPI Application
│   ├── src/
│   │   ├── api/routes/       # Health, status, processing, and batch endpoints
│   │   ├── core/             # App settings, CORS, and logging configuration
│   │   ├── models/           # Pydantic request/response schemas
│   │   ├── processing/       # Engine adapters and colorization bridges
│   │   └── main.py           # FastAPI entrypoint and lifespan handlers
│   └── tests/                # Backend unit and integration tests (31 tests)
│
├── frontend/                 # React 18 + TypeScript SPA
│   ├── src/
│   │   ├── components/       # UI components (Header, Dropzone, Viewer, Metrics, Batch)
│   │   ├── hooks/            # Custom hooks (useImageProcessing, useBatchProcessing)
│   │   ├── services/         # Axios API client and proxy routing
│   │   ├── types/            # TypeScript interfaces and API models
│   │   ├── App.tsx           # Application root
│   │   └── main.tsx          # React DOM entrypoint
│   ├── vite.config.ts        # Vite configuration with `/api` reverse proxy
│   └── package.json
│
├── src/                      # Core Classical CV & Model Download Engine
│   ├── colorizer.py          # Zhang et al. Caffe inference execution
│   ├── enhancer.py           # Denoising, CLAHE, and sharpening algorithms
│   ├── pipeline.py           # Pipeline orchestration and stage execution
│   ├── image_utils.py        # Image decoding, base64 encoding, ZIP bundling
│   ├── metrics.py            # Sharpness/contrast delta heuristics
│   ├── model_downloader.py   # Automated Caffe weights download utility
│   └── config.py             # Default paths, buffer limits, and model constants
│
├── model/                    # Caffe Model Assets
│   ├── colorization_deploy_v2.prototxt
│   ├── pts_in_hull.npy
│   └── colorization_release_v2.caffemodel  (123 MB weights file)
│
├── tests/                    # Core Engine Test Suite (53 tests)
├── pyproject.toml            # Project configuration and pytest settings
├── requirements.txt          # Python backend runtime dependencies
├── package.json              # Workspace root scripts
└── README.md
```

---

## Installation & Setup

### Prerequisites
- **Python**: 3.12+ installed
- **Node.js**: v18+ or v20+ with `npm`

### 1. Clone Repository & Setup Python Environment

```bash
git clone https://github.com/vishalkoripala/opencv-colorization-project.git
cd opencv-colorization-project

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell / Command Prompt):
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Model Weights Setup

The model architecture definition (`colorization_deploy_v2.prototxt`) and cluster centers (`pts_in_hull.npy`) are committed in `model/`.

The pretrained Caffe weights (`colorization_release_v2.caffemodel`, ~123 MB) can be downloaded automatically on first inference, or manually placed in `model/`:
- **Source**: [Zhang et al. Official Release](http://eecs.berkeley.edu/~rich.zhang/projects/2016_colorization/files/demo_v2/colorization_release_v2.caffemodel)
- **Destination Path**: `model/colorization_release_v2.caffemodel`

### 3. Setup Frontend

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### 1. Launch FastAPI Backend

With your virtual environment activated:

```bash
uvicorn backend.src.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs (Swagger UI): `http://127.0.0.1:8000/docs`
- Interactive ReDoc: `http://127.0.0.1:8000/redoc`
- Health Endpoint: `http://127.0.0.1:8000/api/v1/health`

### 2. Launch React Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

- Web UI: `http://localhost:5173`
- The Vite development server automatically proxies `/api/*` calls to `http://127.0.0.1:8000`.

---

## Testing & Quality Assurance

### Backend Test Suite (165 Tests)

Run all unit, pipeline, and API endpoint tests:

```bash
pytest -v

# Run scratch repair test suite specifically:
pytest tests/unit/test_scratch_repair.py -v
```

Test coverage includes:
- Archival scratch detection, directional morphology, ridge validation, and OpenCV inpainting (`INPAINT_TELEA` / `INPAINT_NS`).
- Adaptive Non-Local Means denoising, noise variance heuristics, and texture preservation.
- Classical enhancement filters (CLAHE contrast, Laplacian sharpening unity-gain invariant).
- Colorization model loading, fallback handling, and output tensor contracts.
- FastAPI REST endpoints: validation errors (400, 413, 422), health checks, model status, single and batch processing with `repair=true`/`repair=false`.

### Frontend Type-Check & Build Verification

```bash
cd frontend
npm run type-check
npm run build
```

---

## API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root API service identity and health link |
| `GET` | `/api/v1/health` | Comprehensive system health, uptime, and host details |
| `GET` | `/api/v1/models/status` | Model weights presence, download status, and readiness |
| `POST`| `/api/v1/restoration/analyze` | Image quality diagnosis and rule-based recommendations |
| `POST`| `/api/v1/restoration/process` | Single-image upload, pipeline execution, and metrics |
| `POST`| `/api/v1/restoration/batch` | Multi-image batch processing (up to 10 files) with ZIP |

---

## License & Attribution

- **Source Code**: Licensed under the [MIT License](LICENSE).
- **Pretrained Colorization Model**: Zhang, Isola, and Efros, *"Colorful Image Colorization"*, ECCV 2016 ([BSD-2-Clause](https://github.com/richzhang/colorization/blob/master/LICENSE)).

```bibtex
@inproceedings{zhang2016colorful,
  title={Colorful Image Colorization},
  author={Zhang, Richard and Isola, Phillip and Efros, Alexei A},
  booktitle={ECCV},
  year={2016}
}
```

---

## Author

**Vishal Koripala**  
AI & Computer Vision Practitioner
