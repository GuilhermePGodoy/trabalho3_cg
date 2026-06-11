"""Definicao dos objetos, transformacoes, materiais e luzes da cena."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# Os grupos impedem que uma fonte interna ilumine o exterior e vice-versa.
INTERIOR = 1
EXTERIOR = 2

# Regioes usadas para dividir a mesma malha da casa em duas passagens.
ALL_SURFACES = 0
ENTRANCE_SURFACES = 1
OTHER_SURFACES = 2
CHIMNEY_PART = "rocks.002:component_1"
FIREFLY_GLOW_PART = "firefly_glow"
STAR_PART = "Gold"

# Cinco pontos do Cruzeiro do Sul sobre o frontao da fachada.
SOUTHERN_CROSS = (
    (( 0.00, 11.925, -21.12), -8.0),
    (( 0.00,  8.250, -21.12), 10.0),
    ((-1.650, 10.4625, -21.12), -18.0),
    (( 1.650, 10.3875, -21.12), 14.0),
    (( 0.450,  9.8625, -21.12), 4.0),
)

@dataclass(frozen=True)
class Material:
    """Coeficientes do modelo de iluminacao Phong de um objeto."""

    ka: float
    kd: float
    ks: float
    ns: float
    opacity: float = 1.0


@dataclass
class Transform:
    """Transformacao local de um objeto no mundo."""

    angle: float = 0.0
    axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def matrix(self) -> np.ndarray:
        """Monta a matriz de modelo na ordem translacao, rotacao e escala."""

        angle = np.radians(self.angle)
        x, y, z = self.axis
        axis_length = np.linalg.norm(self.axis)

        # Formula de Rodrigues para rotacao em torno de um eixo arbitrario.
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
        """Converte um ponto local para coordenadas de mundo."""

        local_point = np.array([*point, 1.0], dtype=np.float32)
        return (self.matrix() @ local_point)[:3]


@dataclass
class SceneObject:
    """Objeto desenhavel com malha, material e grupo de iluminacao."""

    name: str
    mesh: Any
    transform: Transform
    material: Material
    group_id: int
    emissive_parts: set[str] = field(default_factory=set)
    part_tints: dict[str, tuple[float, float, float]] = field(
        default_factory=dict
    )
    included_parts: set[str] = field(default_factory=set)
    excluded_parts: set[str] = field(default_factory=set)
    surface_region: int = ALL_SURFACES
    surface_boundary_z: float = 0.0


@dataclass
class PointLight:
    """Fonte pontual presa a uma posicao local de um objeto da cena."""

    name: str
    color: tuple[float, float, float]
    group_id: int
    source_object: str
    local_position: tuple[float, float, float]
    attenuation: tuple[float, float, float] = (1.0, 0.0, 0.0)
    enabled: bool = True


@dataclass
class LightingState:
    """Estado global controlado pelo teclado durante a execucao."""

    ambient_enabled: bool = True
    ambient_intensity: float = 0.25
    diffuse_scale: float = 1.0
    specular_scale: float = 1.0

    def change_ambient(self, amount: float) -> None:
        """Altera a intensidade ambiente mantendo-a no intervalo aceito."""

        self.ambient_intensity = float(
            np.clip(self.ambient_intensity + amount, 0.0, 1.0)
        )

    def change_diffuse(self, amount: float) -> None:
        """Altera o multiplicador difuso sem substituir o kd dos objetos."""

        self.diffuse_scale = float(np.clip(self.diffuse_scale + amount, 0.0, 2.0))

    def change_specular(self, amount: float) -> None:
        """Altera o multiplicador especular sem substituir o ks dos objetos."""

        self.specular_scale = float(
            np.clip(self.specular_scale + amount, 0.0, 2.0)
        )


# Parametros definidos no codigo; valores de iluminacao dos MTL nao sao usados.
MATERIALS = {
    "grama": Material(0.25, 0.85, 0.02, 4.0),
    "raposa": Material(0.20, 0.75, 0.10, 12.0),
    "arvore": Material(0.20, 0.80, 0.05, 8.0),
    "casa": Material(0.18, 0.70, 0.15, 24.0),
    "porta": Material(0.18, 0.65, 0.20, 24.0),
    "frango": Material(0.20, 0.70, 0.12, 16.0),
    "fogueira": Material(0.22, 0.70, 0.18, 24.0),
    "vagalume": Material(0.45, 0.75, 0.30, 32.0),
    "brilho_vagalume": Material(0.0, 0.0, 0.0, 1.0),
    "estrela": Material(0.10, 0.45, 0.85, 96.0),
    "cama": Material(0.20, 0.75, 0.08, 12.0),
    "comoda": Material(0.18, 0.65, 0.25, 32.0),
    "taca": Material(0.12, 0.55, 0.95, 128.0),
    "lampada": Material(0.25, 0.60, 0.45, 64.0),
    "lampada_parede": Material(0.18, 0.55, 0.70, 80.0),
}


def create_scene(meshes: dict[str, Any]) -> list[SceneObject]:
    """Associa as malhas carregadas aos objetos e posicionamentos da cena."""

    objects = [
        SceneObject(
            "grama",
            meshes["grama"],
            Transform(translation=(0.0, -1.0, 0.0), scale=(1000.0, 1.0, 1000.0)),
            MATERIALS["grama"],
            EXTERIOR,
        ),
        SceneObject(
            "raposa",
            meshes["raposa"],
            Transform(
                angle=-90.0,
                axis=(1.0, 0.0, 0.0),
                translation=(6.0, -1.1, -16.0),
                scale=(0.05, 0.05, 0.05),
            ),
            MATERIALS["raposa"],
            EXTERIOR,
        ),
        SceneObject(
            "arvore",
            meshes["arvore"],
            Transform(
                translation=(15.0, -1.0, -20.0),
                scale=(5.0, 5.0, 5.0),
            ),
            MATERIALS["arvore"],
            EXTERIOR,
        ),
        SceneObject(
            "casa_externa",
            meshes["casa"],
            Transform(
                angle=270.0,
                axis=(0.0, 1.0, 0.0),
                translation=(0.0, -1.0, -30.0),
                scale=(1.5, 1.5, 1.5),
            ),
            MATERIALS["casa"],
            EXTERIOR,
            surface_region=ENTRANCE_SURFACES,
            surface_boundary_z=-23.5,
        ),
        SceneObject(
            "casa_interna",
            meshes["casa"],
            Transform(
                angle=270.0,
                axis=(0.0, 1.0, 0.0),
                translation=(0.0, -1.0, -30.0),
                scale=(1.5, 1.5, 1.5),
            ),
            MATERIALS["casa"],
            INTERIOR,
            excluded_parts={CHIMNEY_PART},
            surface_region=OTHER_SURFACES,
            surface_boundary_z=-23.5,
        ),
        SceneObject(
            "casa_chamine",
            meshes["casa"],
            Transform(
                angle=270.0,
                axis=(0.0, 1.0, 0.0),
                translation=(0.0, -1.0, -30.0),
                scale=(1.5, 1.5, 1.5),
            ),
            MATERIALS["casa"],
            EXTERIOR,
            included_parts={CHIMNEY_PART},
        ),
        SceneObject(
            "fogueira",
            meshes["fogueira"],
            Transform(
                translation=(-6.0, -1.0, -16.0),
                scale=(0.05, 0.05, 0.05),
            ),
            MATERIALS["fogueira"],
            EXTERIOR,
        ),
        SceneObject(
            "frango",
            meshes["frango"],
            Transform(
                angle=90.0,
                axis=(0.0, 0.0, 1.0),
                translation=(3.3, -0.6, -14.0),
                scale=(0.005, 0.005, -0.005),
            ),
            MATERIALS["frango"],
            EXTERIOR,
        ),
        SceneObject(
            "porta",
            meshes["porta"],
            Transform(
                angle=270.0,
                axis=(0.0, 1.0, 0.0),
                translation=(1.4, 1.8, -22.7),
                scale=(1.5, 1.5, 1.5),
            ),
            MATERIALS["porta"],
            EXTERIOR,
        ),
        SceneObject(
            "cama",
            meshes["cama"],
            Transform(
                translation=(4.0, 2.03, -31.0),
                scale=(2.0, 2.0, 2.0),
            ),
            MATERIALS["cama"],
            INTERIOR,
        ),
        SceneObject(
            "comoda",
            meshes["comoda"],
            Transform(
                angle=90.0,
                axis=(0.0, 1.0, 0.0),
                translation=(-6.7, 2.03, -25.0),
                scale=(0.02, 0.02, 0.02),
            ),
            MATERIALS["comoda"],
            INTERIOR,
        ),
        SceneObject(
            "taca_1",
            meshes["taca"],
            Transform(
                translation=(-5.6, 3.98, -24.2),
                scale=(0.2, 0.2, 0.2),
            ),
            MATERIALS["taca"],
            INTERIOR,
        ),
        SceneObject(
            "taca_2",
            meshes["taca"],
            Transform(
                translation=(-5.6, 3.98, -25.8),
                scale=(0.2, 0.2, 0.2),
            ),
            MATERIALS["taca"],
            INTERIOR,
        ),
        SceneObject(
            "lampada_amarela",
            meshes["lampada"],
            Transform(
                translation=(1.8, 3.15, -36.0),
                scale=(1.5, 1.5, 1.5),
            ),
            MATERIALS["lampada"],
            INTERIOR,
            {"Lamp"},
        ),
        SceneObject(
            "lampada_parede",
            meshes["lampada_parede"],
            Transform(
                angle=-90.0,
                axis=(0.0, 1.0, 0.0),
                translation=(-6.8, 5.2, -25.0),
                scale=(0.05, 0.05, 0.05),
            ),
            MATERIALS["lampada_parede"],
            INTERIOR,
            {"Brass_Color_Wall_Sconce_Art_Deco_Lamp polySurface1"},
            {
                "Brass_Color_Wall_Sconce_Art_Deco_Lamp polySurface1": (
                    0.12,
                    0.30,
                    1.0,
                )
            },
        ),
    ]

    for index, (position, angle) in enumerate(SOUTHERN_CROSS, start=1):
        objects.append(
            SceneObject(
                f"estrela_{index}",
                meshes["estrela"],
                Transform(
                    angle=angle,
                    axis=(0.0, 0.0, 1.0),
                    translation=position,
                    scale=(0.90, 0.90, 0.45),
                ),
                MATERIALS["estrela"],
                EXTERIOR,
                emissive_parts={STAR_PART},
                part_tints={STAR_PART: (0.10, 0.22, 1.0)},
            )
        )

    for index in range(9):
        objects.append(
            SceneObject(
                f"vagalume_{index + 1}",
                meshes["vagalume"],
                Transform(
                    axis=(0.0, 1.0, 0.0),
                    scale=(12.0, 12.0, 12.0),
                ),
                MATERIALS["vagalume"],
                EXTERIOR,
            )
        )
        objects.append(
            SceneObject(
                f"brilho_vagalume_{index + 1}",
                meshes["brilho_vagalume"],
                Transform(scale=(0.018, 0.015, 0.022)),
                MATERIALS["brilho_vagalume"],
                EXTERIOR,
                emissive_parts={FIREFLY_GLOW_PART},
            )
        )

    return objects


def create_lights() -> list[PointLight]:
    """Cria as fontes da fogueira, luminarias, vagalumes e estrelas."""

    lights = [
        PointLight(
            "fogueira",
            (1.0, 0.32, 0.05),
            EXTERIOR,
            "fogueira",
            (0.0, 30.0, 0.0),
        ),
        PointLight(
            "luz_amarela",
            (1.0, 0.45, 0.15),
            INTERIOR,
            "lampada_amarela",
            (0.0, 0.4, 0.0),
        ),
        PointLight(
            "luz_azul",
            (0.2, 0.4, 1.0),
            INTERIOR,
            "lampada_parede",
            (0.0, 20.5, -3.1),
        ),
    ]

    for index in range(9):
        lights.append(
            PointLight(
                f"luz_vagalume_{index + 1}",
                (0.8, 1, 0),
                EXTERIOR,
                f"brilho_vagalume_{index + 1}",
                (0.0, 0.0, 0.0),
                attenuation=(1.0, 0.35, 0.44),
            )
        )

    for index in range(5):
        lights.append(
            PointLight(
                f"luz_estrela_{index + 1}",
                (0.12, 0.32, 1.0),
                EXTERIOR,
                f"estrela_{index + 1}",
                (0.0, 0.0, 0.0),
                attenuation=(1.0, 0.28, 0.22),
            )
        )

    return lights
