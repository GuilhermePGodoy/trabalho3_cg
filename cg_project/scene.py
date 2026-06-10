from dataclasses import dataclass, field
from typing import Any

import numpy as np


INTERIOR = 1
EXTERIOR = 2


@dataclass(frozen=True)
class Material:
    ka: float
    kd: float
    ks: float
    ns: float
    opacity: float = 1.0


@dataclass
class Transform:
    angle: float = 0.0
    axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def matrix(self) -> np.ndarray:
        angle = np.radians(self.angle)
        x, y, z = self.axis
        axis_length = np.linalg.norm(self.axis)

        rotation = np.identity(4, dtype=np.float32)
        if angle != 0.0 and axis_length > 0.0:
            x, y, z = np.array(self.axis, dtype=np.float32) / axis_length
            c = np.cos(angle)
            s = np.sin(angle)
            one_minus_c = 1.0 - c
            rotation = np.array(
                [
                    [
                        c + x * x * one_minus_c,
                        x * y * one_minus_c - z * s,
                        x * z * one_minus_c + y * s,
                        0.0,
                    ],
                    [
                        y * x * one_minus_c + z * s,
                        c + y * y * one_minus_c,
                        y * z * one_minus_c - x * s,
                        0.0,
                    ],
                    [
                        z * x * one_minus_c - y * s,
                        z * y * one_minus_c + x * s,
                        c + z * z * one_minus_c,
                        0.0,
                    ],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=np.float32,
            )

        tx, ty, tz = self.translation
        translation = np.array(
            [
                [1.0, 0.0, 0.0, tx],
                [0.0, 1.0, 0.0, ty],
                [0.0, 0.0, 1.0, tz],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )

        sx, sy, sz = self.scale
        scale = np.diag([sx, sy, sz, 1.0]).astype(np.float32)
        return translation @ rotation @ scale

    def transform_point(self, point: tuple[float, float, float]) -> np.ndarray:
        local_point = np.array([*point, 1.0], dtype=np.float32)
        return (self.matrix() @ local_point)[:3]


@dataclass
class SceneObject:
    name: str
    mesh: Any
    transform: Transform
    material: Material
    group_id: int
    emissive_parts: set[str] = field(default_factory=set)


@dataclass
class PointLight:
    name: str
    color: tuple[float, float, float]
    group_id: int
    source_object: str
    local_position: tuple[float, float, float]
    enabled: bool = True


@dataclass
class LightingState:
    ambient_enabled: bool = True
    ambient_intensity: float = 0.25
    diffuse_scale: float = 1.0
    specular_scale: float = 1.0

    def change_ambient(self, amount: float) -> None:
        self.ambient_intensity = float(
            np.clip(self.ambient_intensity + amount, 0.0, 1.0)
        )

    def change_diffuse(self, amount: float) -> None:
        self.diffuse_scale = float(np.clip(self.diffuse_scale + amount, 0.0, 2.0))

    def change_specular(self, amount: float) -> None:
        self.specular_scale = float(
            np.clip(self.specular_scale + amount, 0.0, 2.0)
        )


MATERIALS = {
    "grama": Material(0.25, 0.85, 0.02, 4.0),
    "raposa": Material(0.20, 0.75, 0.10, 12.0),
    "arvore": Material(0.20, 0.80, 0.05, 8.0),
    "casa": Material(0.18, 0.70, 0.15, 24.0),
    "porta": Material(0.18, 0.65, 0.20, 24.0),
    "frango": Material(0.20, 0.70, 0.12, 16.0),
    "carro": Material(0.15, 0.65, 0.75, 96.0),
    "cama": Material(0.20, 0.75, 0.08, 12.0),
    "comoda": Material(0.18, 0.65, 0.25, 32.0),
    "taca": Material(0.12, 0.55, 0.95, 128.0),
    "lampada": Material(0.25, 0.60, 0.45, 64.0),
}
