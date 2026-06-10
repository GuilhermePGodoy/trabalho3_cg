"""Animacao coesa do enxame de vagalumes da area externa."""

from dataclasses import dataclass, field

import numpy as np

from .scene import PointLight, SceneObject


@dataclass
class FireflySwarm:
    """Move varios insetos em trajetorias independentes ao redor de um centroide."""

    members: list[SceneObject]
    glows: list[SceneObject]
    lights: list[PointLight]
    origin: tuple[float, float, float] = (-0.5, 1.25, -16.0)
    seed: int = 2026
    elapsed: float = 0.0
    lights_enabled: bool = True
    _base_offsets: np.ndarray = field(init=False, repr=False)
    _amplitudes: np.ndarray = field(init=False, repr=False)
    _frequencies: np.ndarray = field(init=False, repr=False)
    _phases: np.ndarray = field(init=False, repr=False)
    _rng: np.random.Generator = field(init=False, repr=False)
    _blink_is_on: np.ndarray = field(init=False, repr=False)
    _blink_remaining: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not (len(self.members) == len(self.glows) == len(self.lights)):
            raise ValueError(
                "Cada vagalume deve possuir barriga luminosa e fonte pontual"
            )

        self._rng = np.random.default_rng(self.seed)
        count = len(self.members)

        self._base_offsets = self._rng.uniform(
            low=(-2.2, -0.55, -1.4),
            high=(2.2, 0.65, 1.4),
            size=(count, 3),
        )
        self._amplitudes = self._rng.uniform(
            low=(0.18, 0.12, 0.18),
            high=(0.55, 0.38, 0.55),
            size=(count, 3),
        )
        self._frequencies = self._rng.uniform(
            0.55, 1.65, size=(count, 3)
        )
        self._phases = self._rng.uniform(
            0.0, 2.0 * np.pi, size=(count, 3)
        )
        self._blink_is_on = np.ones(count, dtype=bool)
        self._blink_remaining = self._rng.uniform(0.7, 2.4, size=count)
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

        step = max(0.0, min(delta_time, 0.1))
        self.elapsed += step
        oscillation = self._amplitudes * np.sin(
            self.elapsed * self._frequencies + self._phases
        )
        offsets = self._base_offsets + oscillation

        for index, (member, offset) in enumerate(zip(self.members, offsets)):
            member.transform.translation = tuple(self.centroid + offset)
            member.transform.angle = (self.elapsed * (35.0 + index * 7.0)) % 360.0

            glow = self.glows[index]
            # O eixo -Z aponta para o abdomen traseiro do modelo do inseto.
            glow.transform.translation = tuple(
                member.transform.transform_point((0.0, 0.0022, -0.00355))
            )
            glow.transform.angle = member.transform.angle

        self._update_blinks(step)

    def toggle_lights(self) -> bool:
        """Alterna o interruptor geral e retorna o novo estado."""

        self.set_lights_enabled(not self.lights_enabled)
        return self.lights_enabled

    def set_lights_enabled(self, enabled: bool) -> None:
        """Liga ou desliga o enxame sem confundir piscadas com o interruptor."""

        self.lights_enabled = enabled
        if enabled:
            self._blink_is_on.fill(True)
            self._blink_remaining = self._rng.uniform(
                0.7, 2.4, size=len(self.lights)
            )
        self._apply_light_states()

    def _update_blinks(self, delta_time: float) -> None:
        """Produz apagadas curtas e assincronas para cada vagalume."""

        self._blink_remaining -= delta_time
        for index in range(len(self.lights)):
            while self._blink_remaining[index] <= 0.0:
                self._blink_is_on[index] = not self._blink_is_on[index]
                if self._blink_is_on[index]:
                    duration = self._rng.uniform(0.7, 2.4)
                else:
                    duration = self._rng.uniform(0.10, 0.32)
                self._blink_remaining[index] += duration

        self._apply_light_states()

    def _apply_light_states(self) -> None:
        """Sincroniza a emissao visual com a fonte que ilumina a cena."""

        for index, light in enumerate(self.lights):
            light.enabled = (
                self.lights_enabled and bool(self._blink_is_on[index])
            )
