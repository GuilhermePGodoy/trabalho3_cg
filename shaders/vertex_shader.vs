#version 330 core

layout (location = 0) in vec3 position;
layout (location = 1) in vec2 texture_coord;
layout (location = 2) in vec3 normals;

out vec2 out_texture;
out vec3 out_fragPos;
out vec3 out_normal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main(){
    gl_Position = projection * view * model * vec4(position, 1.0);
    out_texture = texture_coord;
    out_fragPos = vec3(model * vec4(position, 1.0));
    out_normal = mat3(transpose(inverse(model))) * normals;
}
