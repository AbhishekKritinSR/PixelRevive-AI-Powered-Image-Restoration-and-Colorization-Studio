"""Module: batch_service.py

Purpose:
Coordinates batch processing of multiple photographs with isolated error handling
and automated in-memory ZIP packaging.

Responsibilities:
- Enforce the maximum batch upload limit (MAX_BATCH_FILES = 10).
- Process each image sequentially through the RestorationService.
- Isolate per-file failures so corrupt or unsupported files do not abort the entire batch.
- Aggregate successful outputs and build an in-memory ZIP archive using `build_results_zip`.
- Return a structured BatchRestorationResponse with overall and per-item statistics.

Dependencies:
- base64, time
- backend.src.core.config.settings
- backend.src.core.exceptions.BatchSizeExceededError
- backend.src.processing.utils.zip_builder.build_results_zip
- backend.src.schemas.batch (BatchItemResult, BatchRestorationResponse)
- backend.src.schemas.restoration.RestorationOptions
- backend.src.services.restoration_service.RestorationService
"""

import base64
import time
from typing import List, Tuple

from backend.src.core.config import settings
from backend.src.core.exceptions import BatchSizeExceededError
from backend.src.processing.utils.zip_builder import build_results_zip
from backend.src.schemas.batch import (
    BatchItemResult,
    BatchRestorationResponse,
)
from backend.src.schemas.restoration import RestorationOptions
from backend.src.services.restoration_service import RestorationService


class BatchService:
    """Application service for orchestrating multi-image batch operations."""

    def __init__(self, restoration_service: RestorationService):
        self.restoration_service = restoration_service

    def process_batch(
        self,
        files: List[Tuple[str, bytes]],
        options: RestorationOptions,
    ) -> BatchRestorationResponse:
        """Process up to MAX_BATCH_FILES images with per-item failure isolation.

        Args:
            files:
                List of (filename, file_bytes) tuples.
            options:
                RestorationOptions specifying which stages to run.

        Returns:
            BatchRestorationResponse containing summary, per-item results, and ZIP.

        Raises:
            BatchSizeExceededError:
                If number of uploaded files exceeds settings.MAX_BATCH_FILES (10).
            ValueError:
                If files list is empty.
        """
        if not files:
            raise ValueError("No files provided for batch processing.")

        if len(files) > settings.MAX_BATCH_FILES:
            raise BatchSizeExceededError(
                f"Batch size of {len(files)} exceeds the maximum allowed limit of "
                f"{settings.MAX_BATCH_FILES} images."
            )

        start_time = time.perf_counter()
        item_results: List[BatchItemResult] = []
        succeeded_pngs: List[Tuple[str, bytes]] = []

        for filename, file_bytes in files:
            try:
                single_resp, png_bytes = self.restoration_service.process_image(
                    file_bytes=file_bytes,
                    filename=filename,
                    options=options,
                )
                item_results.append(
                    BatchItemResult(
                        filename=filename,
                        status="success",
                        original_width=single_resp.original_width,
                        original_height=single_resp.original_height,
                        processed_width=single_resp.processed_width,
                        processed_height=single_resp.processed_height,
                        elapsed_seconds=single_resp.elapsed_seconds,
                        metrics=single_resp.metrics,
                        image_base64=single_resp.image_base64,
                    )
                )
                # Prepare filename for ZIP bundling
                out_name = f"restored_{filename}"
                if not out_name.lower().endswith(".png"):
                    out_name = f"{out_name}.png"
                succeeded_pngs.append((out_name, png_bytes))

            except Exception as e:
                # Isolate failure to this single file
                item_results.append(
                    BatchItemResult(
                        filename=filename,
                        status="failed",
                        error=str(e),
                    )
                )

        total_elapsed = time.perf_counter() - start_time
        succeeded_count = sum(1 for item in item_results if item.status == "success")
        failed_count = sum(1 for item in item_results if item.status == "failed")

        # Bundle successful results into in-memory ZIP archive
        zip_base64 = None
        if succeeded_pngs:
            zip_bytes = build_results_zip(succeeded_pngs)
            b64_str = base64.b64encode(zip_bytes).decode("ascii")
            zip_base64 = f"data:application/zip;base64,{b64_str}"

        return BatchRestorationResponse(
            total_submitted=len(files),
            total_succeeded=succeeded_count,
            total_failed=failed_count,
            elapsed_seconds=round(total_elapsed, 3),
            items=item_results,
            zip_base64=zip_base64,
        )

