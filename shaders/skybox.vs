#version 330 core
layout (location = 0) in vec3 aPos;

out vec3 TexCoords;

uniform mat4 projection;
uniform mat4 view;

void main()
{
    TexCoords = aPos;
    // Removendo a translação da matriz view para que o céu não se aproxime da câmera
    mat4 viewStatic = mat4(mat3(view)); 
    
    vec4 pos = projection * viewStatic * vec4(aPos, 1.0);
    
    // coloca a skybox na profundidade máxima do clipping space.
    gl_Position = pos.xyww;
}