// Fragment shader com modelo de iluminação Phong completo.
// Os parâmetros Ka, Kd, Ks e Ns vêm do arquivo .mtl de cada objeto
// e são enviados via uniform pelo draw_object() em objects_manager.py.

// -----------------------------------------------------------------
// Struct: fonte de luz
// -----------------------------------------------------------------
struct Light {
    vec3 position;
    vec3 ambient;   // intensidade ambiente  (Ia)
    vec3 diffuse;   // intensidade difusa    (Id)
    vec3 specular;  // intensidade especular (Is)
};

// -----------------------------------------------------------------
// Struct: material do objeto (valores vindos do .mtl)
// -----------------------------------------------------------------
struct Material {
    vec3  Ka;   // coeficiente de reflexão ambiente
    vec3  Kd;   // coeficiente de reflexão difusa
    vec3  Ks;   // coeficiente de reflexão especular
    float Ns;   // expoente especular (brilho)
    float d;    // opacidade (1.0 = totalmente opaco)
};

// -----------------------------------------------------------------
// Uniforms
// -----------------------------------------------------------------
#define MAX_LIGHTS 10
uniform int      numActiveLights;
uniform Light    lights[MAX_LIGHTS];

uniform Material material;      // parâmetros do .mtl do objeto atual
uniform vec3     viewPos;       // posição da câmera no espaço do mundo

// Recebidos do vertex shader
varying vec2 out_texture;
varying vec3 out_normal;
varying vec3 out_fragPos;

uniform sampler2D samplerTexture;


// -----------------------------------------------------------------
// Main
// -----------------------------------------------------------------
void main(){

    vec3 norm    = normalize(out_normal);
    vec3 viewDir = normalize(viewPos - out_fragPos);

    vec3 result = vec3(0.0);

    for (int i = 0; i < numActiveLights; i++) {

        // --- Ambiente ---
        // A cor ambiente é modulada pelo Ka do material e pela intensidade Ia da luz.
        vec3 ambient = lights[i].ambient * material.Ka;

        // --- Difusa (Lambertiana) ---
        vec3  lightDir = normalize(lights[i].position - out_fragPos);
        float diff     = max(dot(norm, lightDir), 0.0);
        vec3  diffuse  = lights[i].diffuse * (diff * material.Kd);

        // --- Especular (Phong) ---
        vec3  reflectDir = reflect(-lightDir, norm);
        float spec       = pow(max(dot(viewDir, reflectDir), 0.0), material.Ns);
        vec3  specular   = lights[i].specular * (spec * material.Ks);

        result += ambient + diffuse + specular;
    }

    // Textura modula a componente difusa/ambiente; especular não é afetada pela textura
    // para manter a aparência de brilho mesmo em superfícies escuras.
    vec4 texColor = texture2D(samplerTexture, out_texture);

    // Componente especular some separada para não ser "apagada" pela textura escura
    vec3 specularTotal = vec3(0.0);
    for (int i = 0; i < numActiveLights; i++) {
        vec3  lightDir   = normalize(lights[i].position - out_fragPos);
        vec3  reflectDir = reflect(-lightDir, norm);
        float spec       = pow(max(dot(viewDir, reflectDir), 0.0), material.Ns);
        specularTotal   += lights[i].specular * (spec * material.Ks);
    }

    // Cor final: iluminação * textura + especular puro
    vec3 lighting       = result - specularTotal; // ambiente + difusa
    vec3 finalRGB       = lighting * texColor.rgb + specularTotal;

    gl_FragColor = vec4(finalRGB, texColor.a * material.d);
}
