"""Animacao coesa do enxame de vagalumes da area externa."""

from dataclasses import dataclass, field

import numpy as np

from .scene import SceneObject


@dataclass
class FireflySwarm:
    """Move varios insetos em trajetorias independentes ao redor de um centroide."""

    members: list[SceneObject]
    origin: tuple[float, float, float] = (-0.5, 1.25, -16.0)
    seed: int = 2026
    elapsed: float = 0.0
    _base_offsets: np.ndarray = field(init=False, repr=False)
    _amplitudes: np.ndarray = field(init=False, repr=False)
    _frequencies: np.ndarray = field(init=False, repr=False)
    _phases: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        count = len(self.members)

        self._base_offsets = rng.uniform(
            low=(-2.2, -0.55, -1.4),
            high=(2.2, 0.65, 1.4),
            size=(count, 3),
        )
        self._amplitudes = rng.uniform(
            low=(0.18, 0.12, 0.18),
            high=(0.55, 0.38, 0.55),
            size=(count, 3),
        )
        self._frequencies = rng.uniform(0.55, 1.65, size=(count, 3))
        self._phases = rng.uniform(0.0, 2.0 * np.pi, size=(count, 3))
        self.update(0.0)

    @property
    def centroid(self) -> np.ndarray:
        """Retorna o centro movel em torno do qual o enxame permanece unido."""

        origin = np.asarray(self.origin, dtype=np.float32)
        drift = np.array(
            [
                0.9 * np.sin(self.elapsed * 0.23),
                0.2 * np.sin(self.elapsed * 0.31 + 0.8),
                0.7 * np.sin(self.elapsed * 0.19 + 1.4),
            ],
            dtype=np.float32,
        )
        return origin + drift

    def update(self, delta_time: float) -> None:
        """Atualiza posicoes e orientacoes sem deixar membros escaparem."""

        self.elapsed += max(0.0, min(delta_time, 0.1))
        oscillation = self._amplitudes * np.sin(
            self.elapsed * self._frequencies + self._phases
        )
        offsets = self._base_offsets + oscillation

        for index, (member, offset) in enumerate(zip(self.members, offsets)):
            member.transform.translation = tuple(self.centroid + offset)
            member.transform.angle = (self.elapsed * (35.0 + index * 7.0)) % 360.0
