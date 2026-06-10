// =============================================================
// depth_shader.vs
// Vertex shader do depth pass (geração do shadow map).
// Usado em uma render pass separada, uma vez por fonte de luz.
// =============================================================
#version 330 core

attribute vec3 position;

uniform mat4 model;
uniform mat4 lightSpaceMatrix;  // projection * view da luz

void main() {
    gl_Position = lightSpaceMatrix * model * vec4(position, 1.0);
}
