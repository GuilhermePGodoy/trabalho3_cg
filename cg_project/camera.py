from dataclasses import dataclass, field

import glm
import numpy as np


@dataclass
class Camera:
    position: glm.vec3 = field(
        default_factory=lambda: glm.vec3(0.0, 8.0, 3.0)
    )
    front: glm.vec3 = field(
        default_factory=lambda: glm.vec3(0.0, 0.0, -1.0)
    )
    up: glm.vec3 = field(default_factory=lambda: glm.vec3(0.0, 1.0, 0.0))
    yaw: float = -90.0
    pitch: float = 0.0
    fov: float = 45.0
    first_mouse: bool = True
    last_x: float = 640.0
    last_y: float = 360.0

    def view_matrix(self) -> np.ndarray:
        return np.array(
            glm.lookAt(self.position, self.position + self.front, self.up),
            dtype=np.float32,
        )

    def projection_matrix(self, width: int, height: int) -> np.ndarray:
        aspect = width / max(height, 1)
        return np.array(
            glm.perspective(glm.radians(self.fov), aspect, 0.1, 100.0),
            dtype=np.float32,
        )

    def move(self, direction: str, amount: float) -> None:
        right = glm.normalize(glm.cross(self.front, self.up))
        if direction == "forward":
            self.position += amount * self.front
        elif direction == "backward":
            self.position -= amount * self.front
        elif direction == "left":
            self.position -= amount * right
        elif direction == "right":
            self.position += amount * right
        self.position.y = max(-0.8, self.position.y)

    def look(self, xpos: float, ypos: float, sensitivity: float = 0.1) -> None:
        if self.first_mouse:
            self.last_x = xpos
            self.last_y = ypos
            self.first_mouse = False

        xoffset = (xpos - self.last_x) * sensitivity
        yoffset = (self.last_y - ypos) * sensitivity
        self.last_x = xpos
        self.last_y = ypos

        self.yaw += xoffset
        self.pitch = float(np.clip(self.pitch + yoffset, -89.0, 89.0))

        front = glm.vec3()
        front.x = glm.cos(glm.radians(self.yaw)) * glm.cos(glm.radians(self.pitch))
        front.y = glm.sin(glm.radians(self.pitch))
        front.z = glm.sin(glm.radians(self.yaw)) * glm.cos(glm.radians(self.pitch))
        self.front = glm.normalize(front)

    def zoom(self, yoffset: float) -> None:
        self.fov = float(np.clip(self.fov - yoffset, 1.0, 45.0))
