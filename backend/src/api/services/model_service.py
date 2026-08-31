"""
src/api/services/model_service.py
=================================
PyTorch model management, device allocation, and inference service for
Change Detection models.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from src.detection.siamese_unet import SiameseUNet
from src.detection.snunet_cd import SNUNetCD
from src.api.schemas import ModelInfo

logger = logging.getLogger(__name__)


class ModelService:
    """Singleton service for loading, caching, and running Change Detection models."""

    _instance: Optional["ModelService"] = None

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"ModelService initialized using device: {self.device}")

        self._models: Dict[str, torch.nn.Module] = {}
        self._load_default_models()

    @classmethod
    def get_instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_default_models(self) -> None:
        """Pre-instantiate standard model architectures for fast inference."""
        try:
            # SNUNet-CD SAR Model 3
            try:
                snunet_sar = SNUNetCD(in_channels=2, num_classes=1)
                ckpt_path = Path(__file__).resolve().parent.parent.parent.parent / "runs" / "2026-08-23_01-14-15_tum_oscd_sar_snunet_bce_tversky_scratch" / "checkpoints" / "best.pt"
                if ckpt_path.exists():
                    checkpoint = torch.load(str(ckpt_path), map_location=self.device, weights_only=False)
                    if isinstance(checkpoint, dict):
                        if "model_state_dict" in checkpoint:
                            state_dict = checkpoint["model_state_dict"]
                        elif "state_dict" in checkpoint:
                            state_dict = checkpoint["state_dict"]
                        else:
                            state_dict = checkpoint
                    else:
                        state_dict = checkpoint
                    snunet_sar.load_state_dict(state_dict)
                    logger.info(f"Loaded Model 3 SAR checkpoint from {ckpt_path}")
                else:
                    logger.error(f"CRITICAL: Model 3 SAR checkpoint not found at {ckpt_path}. Refusing to load random weights.")
                    raise FileNotFoundError(f"Missing required Model 3 checkpoint: {ckpt_path}")
                
                snunet_sar.eval().to(self.device)
                self._models["snunet_cd_sar"] = snunet_sar
            except Exception as e:
                logger.error(f"Failed to load snunet_cd_sar: {e}")

            logger.info(f"Successfully pre-loaded models: {list(self._models.keys())}")
        except Exception as e:
            logger.error(f"Error pre-loading models: {e}", exc_info=True)

    def get_available_models(self) -> List[ModelInfo]:
        """Return catalog of available model architectures."""
        catalog = []
        for name, model in self._models.items():
            num_params = sum(p.numel() for p in model.parameters())
            in_ch = 2 if "sar" in name else 3
            display_name = name.replace("_", " ").title()
            catalog.append(
                ModelInfo(
                    name=name,
                    display_name=display_name,
                    input_channels=in_ch,
                    parameters=num_params,
                    description=f"{display_name} with {in_ch} input channels and {num_params:,} parameters.",
                )
            )
        return catalog

    @torch.no_grad()
    def predict_change_sar(
        self,
        t1_tensor: torch.Tensor,
        t2_tensor: torch.Tensor,
        model_name: str = "siamese_unet",
        threshold: float = 0.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run inference on a pair of 2-channel SAR tensors (C=2, H, W).

        Returns:
            prob_map: np.ndarray (H, W) in [0.0, 1.0]
            binary_mask: np.ndarray (H, W) uint8 in {0, 1}
        """
        # Ensure batch dimension [1, 2, H, W]
        if t1_tensor.ndim == 3:
            t1_tensor = t1_tensor.unsqueeze(0)
        if t2_tensor.ndim == 3:
            t2_tensor = t2_tensor.unsqueeze(0)

        t1_tensor = t1_tensor.to(self.device, dtype=torch.float32)
        t2_tensor = t2_tensor.to(self.device, dtype=torch.float32)

        # Select model
        model = self._models.get(model_name)
        if model is None:
            raise ValueError(f"Model '{model_name}' is not loaded or has no valid trained checkpoint.")

        logits = model(t1_tensor, t2_tensor)
        probs = torch.sigmoid(logits)

        # Squeeze batch & channel dimensions -> (H, W)
        prob_map = probs.squeeze().detach().cpu().numpy().astype(np.float32)
        binary_mask = (prob_map >= threshold).astype(np.uint8)

        return prob_map, binary_mask

    @torch.no_grad()
    def predict_change_rgb(
        self,
        t1_tensor: torch.Tensor,
        t2_tensor: torch.Tensor,
        model_name: str = "siamese_unet",
        threshold: float = 0.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run inference on a pair of 3-channel RGB tensors (C=3, H, W).
        """
        if t1_tensor.ndim == 3:
            t1_tensor = t1_tensor.unsqueeze(0)
        if t2_tensor.ndim == 3:
            t2_tensor = t2_tensor.unsqueeze(0)

        t1_tensor = t1_tensor.to(self.device, dtype=torch.float32)
        t2_tensor = t2_tensor.to(self.device, dtype=torch.float32)

        model = self._models.get(model_name)
        if model is None:
            raise ValueError(f"Model '{model_name}' is not loaded or has no valid trained checkpoint.")

        logits = model(t1_tensor, t2_tensor)
        probs = torch.sigmoid(logits)

        prob_map = probs.squeeze().detach().cpu().numpy().astype(np.float32)
        binary_mask = (prob_map >= threshold).astype(np.uint8)

        return prob_map, binary_mask
