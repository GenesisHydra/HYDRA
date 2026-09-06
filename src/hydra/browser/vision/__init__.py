"""
Vision Module - Análisis visual y OCR para HYDRA Browser.

Complementa el DOM con capacidades visuales:
- OCR (Tesseract / EasyOCR)
- Detección de textos no accesibles via DOM
- Análisis de screenshots
- Detección de estados visuales (loading, error, success)
- Combinación DOM + OCR para robustez
"""

import asyncio
import base64
import hashlib
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ===== OCR Backends =====

class OCRBackend(ABC):
    """Backend abstracto para OCR."""

    @abstractmethod
    async def extract_text(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Extrae texto con bounding boxes. Retorna lista de {text, bbox, confidence}."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el backend está disponible."""
        pass


class TesseractOCR(OCRBackend):
    """OCR usando Tesseract (requiere tesseract instalado)."""

    def __init__(self, lang: str = "eng", config: str = "--psm 6"):
        self.lang = lang
        self.config = config
        self._tesseract = None

    async def _import(self):
        if self._tesseract is None:
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                raise RuntimeError("pytesseract no instalado. pip install pytesseract")

    async def extract_text(self, image: Image.Image) -> List[Dict[str, Any]]:
        await self._import()
        # Convertir a RGB si es necesario
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Obtener datos detallados
        data = self._tesseract.image_to_data(
            image,
            lang=self.lang,
            config=self.config,
            output_type=self._tesseract.Output.DICT,
        )

        results = []
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if text:
                conf = float(data["conf"][i])
                if conf > 0:
                    results.append({
                        "text": text,
                        "bbox": {
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        },
                        "confidence": conf / 100.0,
                        "line_num": data["line_num"][i],
                        "block_num": data["block_num"][i],
                    })
        return results

    def is_available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False


class EasyOCRBackend(OCRBackend):
    """OCR usando EasyOCR (más preciso, soporta muchos idiomas)."""

    def __init__(self, languages: List[str] = None, gpu: bool = False):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader = None

    async def _import(self):
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
            except ImportError:
                raise RuntimeError("easyocr no instalado. pip install easyocr")

    async def extract_text(self, image: Image.Image) -> List[Dict[str, Any]]:
        await self._import()
        # Convertir a array numpy
        img_array = np.array(image)
        results = self._reader.readtext(img_array)

        formatted = []
        for (bbox, text, conf) in results:
            if text.strip():
                # bbox es lista de 4 puntos [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                formatted.append({
                    "text": text.strip(),
                    "bbox": {
                        "x": min(xs),
                        "y": min(ys),
                        "width": max(xs) - min(xs),
                        "height": max(ys) - min(ys),
                    },
                    "confidence": conf,
                })
        return formatted

    def is_available(self) -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False


class DummyOCR(OCRBackend):
    """OCR dummy para cuando no hay backend real."""

    async def extract_text(self, image: Image.Image) -> List[Dict[str, Any]]:
        logger.warning("Usando DummyOCR - no hay backend OCR real disponible")
        return []

    def is_available(self) -> bool:
        return True


# ===== Vision Analyzer =====

@dataclass
class VisualElement:
    """Elemento detectado visualmente."""
    text: str
    bbox: Dict[str, int]  # x, y, width, height
    confidence: float
    source: str  # "ocr" | "dom" | "combined"
    element_type: Optional[str] = None  # button, input, text, error, etc.
    dom_selector: Optional[str] = None


@dataclass
class VisualAnalysis:
    """Resultado de análisis visual completo."""
    screenshot_path: Path
    image_hash: str
    ocr_elements: List[VisualElement] = field(default_factory=list)
    dom_elements: List[VisualElement] = field(default_factory=list)
    combined_elements: List[VisualElement] = field(default_factory=list)
    detected_states: Dict[str, bool] = field(default_factory=dict)  # loading, error, success, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


class VisionAnalyzer:
    """
    Analizador visual que combina OCR + DOM.

    Flujo:
    1. Captura screenshot
    2. Ejecuta OCR
    3. Extrae elementos del DOM (via page.evaluate)
    4. Combina ambos (matching por posición/texto)
    5. Detecta estados visuales comunes
    """

    def __init__(
        self,
        ocr_backend: Optional[OCRBackend] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.ocr_backend = ocr_backend or self._get_default_ocr()
        self.cache_dir = cache_dir
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_ocr(self) -> OCRBackend:
        # Intentar backends en orden de preferencia
        for backend_cls in (EasyOCRBackend, TesseractOCR, DummyOCR):
            try:
                backend = backend_cls()
                if backend.is_available():
                    logger.info(f"OCR backend seleccionado: {backend_cls.__name__}")
                    return backend
            except Exception:
                continue
        return DummyOCR()

    async def analyze(
        self,
        page,
        screenshot_path: Optional[Path] = None,
        full_page: bool = True,
    ) -> VisualAnalysis:
        """
        Análisis visual completo de una página.

        Args:
            page: Página de Playwright
            screenshot_path: Ruta opcional para guardar screenshot
            full_page: Si capturar página completa o solo viewport

        Returns:
            VisualAnalysis con elementos OCR, DOM, combinados y estados detectados
        """
        # 1. Capturar screenshot
        if screenshot_path is None and self.cache_dir:
            screenshot_path = self.cache_dir / f"vision_{hashlib.md5(str(page.url).encode()).hexdigest()[:8]}.png"

        screenshot_bytes = await page.screenshot(
            path=screenshot_path,
            full_page=full_page,
            type="png",
        )

        # Cargar imagen
        image = Image.open(screenshot_path) if screenshot_path else Image.open(
            asyncio.BytesIO(screenshot_bytes)
        )

        # Hash de imagen para detección de cambios
        image_hash = hashlib.md5(screenshot_bytes).hexdigest()

        # 2. OCR
        ocr_results = await self.ocr_backend.extract_text(image)
        ocr_elements = [
            VisualElement(
                text=r["text"],
                bbox=r["bbox"],
                confidence=r["confidence"],
                source="ocr",
            )
            for r in ocr_results
        ]

        # 3. DOM elements
        dom_elements = await self._extract_dom_elements(page)

        # 4. Combinar
        combined = self._combine_elements(ocr_elements, dom_elements)

        # 5. Detectar estados
        states = self._detect_states(combined, image)

        return VisualAnalysis(
            screenshot_path=screenshot_path,
            image_hash=image_hash,
            ocr_elements=ocr_elements,
            dom_elements=dom_elements,
            combined_elements=combined,
            detected_states=states,
            metadata={
                "viewport": await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})"),
                "url": page.url,
                "title": await page.title(),
            }
        )

    async def _extract_dom_elements(self, page) -> List[VisualElement]:
        """Extrae elementos visibles del DOM con sus bounding boxes."""
        # Script que retorna elementos visibles con texto y bbox
        script = """
        () => {
            const elements = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let node;
            while (node = walker.nextNode()) {
                const parent = node.parentElement;
                if (!parent) continue;
                const style = window.getComputedStyle(parent);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                const text = node.textContent.trim();
                if (!text) continue;
                const rect = parent.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                elements.push({
                    text: text.substring(0, 200),
                    tag: parent.tagName.toLowerCase(),
                    class: parent.className,
                    id: parent.id,
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    selector: parent.tagName.toLowerCase() + (parent.id ? '#' + parent.id : '') + (parent.className ? '.' + parent.className.split(' ').join('.') : ''),
                });
            }
            return elements;
        }
        """
        try:
            raw_elements = await page.evaluate(script)
            dom_elements = []
            for el in raw_elements:
                dom_elements.append(VisualElement(
                    text=el["text"],
                    bbox={"x": el["x"], "y": el["y"], "width": el["width"], "height": el["height"]},
                    confidence=1.0,
                    source="dom",
                    element_type=el["tag"],
                    dom_selector=el["selector"],
                ))
            return dom_elements
        except Exception as e:
            logger.warning(f"Error extrayendo elementos DOM: {e}")
            return []

    def _combine_elements(
        self,
        ocr_elements: List[VisualElement],
        dom_elements: List[VisualElement],
        iou_threshold: float = 0.3,
    ) -> List[VisualElement]:
        """
        Combina elementos OCR y DOM usando IoU (Intersection over Union)
        y similitud de texto.
        """
        combined = []
        matched_ocr = set()
        matched_dom = set()

        # Matching por IoU
        for i, ocr_el in enumerate(ocr_elements):
            best_match = None
            best_iou = 0
            for j, dom_el in enumerate(dom_elements):
                if j in matched_dom:
                    continue
                iou = self._compute_iou(ocr_el.bbox, dom_el.bbox)
                if iou > best_iou and iou >= iou_threshold:
                    best_iou = iou
                    best_match = j

            if best_match is not None:
                matched_ocr.add(i)
                matched_dom.add(best_match)
                dom_el = dom_elements[best_match]
                combined.append(VisualElement(
                    text=ocr_el.text if len(ocr_el.text) > len(dom_el.text) else dom_el.text,
                    bbox=ocr_el.bbox,
                    confidence=max(ocr_el.confidence, dom_el.confidence),
                    source="combined",
                    element_type=dom_el.element_type,
                    dom_selector=dom_el.dom_selector,
                ))
            else:
                combined.append(ocr_el)

        # Añadir DOM no matcheados
        for j, dom_el in enumerate(dom_elements):
            if j not in matched_dom:
                combined.append(dom_el)

        return combined

    def _compute_iou(self, bbox1: Dict, bbox2: Dict) -> float:
        """Calcula Intersection over Union de dos bounding boxes."""
        x1 = max(bbox1["x"], bbox2["x"])
        y1 = max(bbox1["y"], bbox2["y"])
        x2 = min(bbox1["x"] + bbox1["width"], bbox2["x"] + bbox2["width"])
        y2 = min(bbox1["y"] + bbox1["height"], bbox2["y"] + bbox2["height"])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = bbox1["width"] * bbox1["height"]
        area2 = bbox2["width"] * bbox2["height"]
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _detect_states(
        self,
        elements: List[VisualElement],
        image: Image.Image,
    ) -> Dict[str, bool]:
        """Detecta estados visuales comunes."""
        states = {
            "loading": False,
            "error": False,
            "success": False,
            "warning": False,
            "modal_open": False,
            "toast_visible": False,
        }

        # Keywords por estado
        keywords = {
            "loading": ["loading", "cargando", "please wait", "espere", "spinner"],
            "error": ["error", "failed", "falló", "exception", "traceback"],
            "success": ["success", "éxito", "completed", "completado", "saved", "guardado"],
            "warning": ["warning", "advertencia", "caution", "precaución"],
        }

        all_text = " ".join(e.text.lower() for e in elements)

        for state, kws in keywords.items():
            states[state] = any(kw in all_text for kw in kws)

        # Detectar modales/toasts por elementos con posición fija o z-index alto
        # (requeriría info DOM adicional, simplificado aquí)

        return states

    async def find_text(
        self,
        page,
        text: str,
        threshold: float = 0.7,
    ) -> List[VisualElement]:
        """Busca texto específico en la página (OCR + DOM)."""
        analysis = await self.analyze(page)
        matches = []
        text_lower = text.lower()
        for el in analysis.combined_elements:
            if text_lower in el.text.lower():
                # Fuzzy match por ahora simple contains
                matches.append(el)
        return matches

    async def wait_for_text(
        self,
        page,
        text: str,
        timeout: float = 10000,
        poll_interval: float = 500,
    ) -> VisualElement:
        """Espera a que aparezca texto específico (visual, no solo DOM)."""
        import time
        start = time.time()
        max_wait = timeout / 1000

        while time.time() - start < max_wait:
            matches = await self.find_text(page, text)
            if matches:
                return matches[0]
            await asyncio.sleep(poll_interval / 1000)

        raise TimeoutError(f"Texto '{text}' no encontrado visualmente en {timeout}ms")

    async def click_by_text(
        self,
        page,
        text: str,
        timeout: float = 10000,
    ) -> bool:
        """Click en elemento encontrado por texto visual."""
        matches = await self.find_text(page, text)
        if not matches:
            return False

        # Click en el centro del bbox del primer match
        el = matches[0]
        x = el.bbox["x"] + el.bbox["width"] // 2
        y = el.bbox["y"] + el.bbox["height"] // 2
        await page.mouse.click(x, y)
        return True


# ===== Funciones de conveniencia =====

async def create_vision_analyzer(
    prefer_easyocr: bool = True,
    cache_dir: Optional[Path] = None,
) -> VisionAnalyzer:
    """Crea VisionAnalyzer con el mejor backend disponible."""
    backend = None
    if prefer_easyocr:
        backend = EasyOCRBackend()
        if not backend.is_available():
            backend = TesseractOCR()
            if not backend.is_available():
                backend = DummyOCR()
    else:
        backend = TesseractOCR()
        if not backend.is_available():
            backend = EasyOCRBackend()
            if not backend.is_available():
                backend = DummyOCR()

    return VisionAnalyzer(ocr_backend=backend, cache_dir=cache_dir)