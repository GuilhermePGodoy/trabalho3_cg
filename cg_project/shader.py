"""Compilacao de shaders GLSL e envio de uniforms ao programa OpenGL."""

from pathlib import Path

from OpenGL.GL import (
    GL_COMPILE_STATUS,
    GL_FRAGMENT_SHADER,
    GL_LINK_STATUS,
    GL_VERTEX_SHADER,
    glAttachShader,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteShader,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glUniform1f,
    glUniform1i,
    glUniform3f,
    glUniformMatrix4fv,
    glUseProgram,
)


class Shader:
    """Encapsula um programa formado por vertex e fragment shaders."""

    def __init__(self, vertex_path: str | Path, fragment_path: str | Path):
        vertex = self._compile(vertex_path, GL_VERTEX_SHADER)
        fragment = self._compile(fragment_path, GL_FRAGMENT_SHADER)

        self.id = glCreateProgram()
        glAttachShader(self.id, vertex)
        glAttachShader(self.id, fragment)
        glLinkProgram(self.id)

        if not glGetProgramiv(self.id, GL_LINK_STATUS):
            log = glGetProgramInfoLog(self.id).decode(errors="replace")
            raise RuntimeError(f"Erro ao vincular shaders:\n{log}")

        # Apos o link, o programa mantem o codigo e os shaders podem ser liberados.
        glDeleteShader(vertex)
        glDeleteShader(fragment)

    @staticmethod
    def _compile(path: str | Path, shader_type: int) -> int:
        """Compila um arquivo GLSL e apresenta o log em caso de erro."""

        path = Path(path)
        shader = glCreateShader(shader_type)
        glShaderSource(shader, path.read_text(encoding="utf-8"))
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            log = glGetShaderInfoLog(shader).decode(errors="replace")
            raise RuntimeError(f"Erro ao compilar {path}:\n{log}")
        return shader

    def use(self) -> None:
        glUseProgram(self.id)

    def location(self, name: str) -> int:
        return glGetUniformLocation(self.id, name)

    def set_int(self, name: str, value: int) -> None:
        glUniform1i(self.location(name), value)

    def set_float(self, name: str, value: float) -> None:
        glUniform1f(self.location(name), value)

    def set_vec3(self, name: str, value) -> None:
        glUniform3f(self.location(name), value[0], value[1], value[2])

    def set_mat4(self, name: str, matrix, transpose: bool = True) -> None:
        glUniformMatrix4fv(self.location(name), 1, transpose, matrix)
