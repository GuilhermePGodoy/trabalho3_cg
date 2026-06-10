#version 330 core
out vec4 FragColor;

in vec3 TexCoords;

uniform samplerCube skybox;

void main()
{
    // A direcao interpolada seleciona a face e o ponto do cubemap.
    FragColor = texture(skybox, TexCoords);
}
