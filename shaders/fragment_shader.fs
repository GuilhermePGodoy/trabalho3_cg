#version 330 core

#define MAX_LIGHTS 12

struct PointLight {
    vec3 position;
    vec3 color;
    vec3 attenuation;
    int groupID;
    bool enabled;
};

struct Material {
    float ka;
    float kd;
    float ks;
    float ns;
    float opacity;
};

uniform int numLights;
uniform PointLight lights[MAX_LIGHTS];
uniform Material material;
uniform int objectGroupID;

uniform bool ambientEnabled;
uniform float ambientIntensity;
uniform float diffuseScale;
uniform float specularScale;
uniform vec3 emissiveColor;
uniform vec3 viewPos;
uniform sampler2D samplerTexture;

in vec2 out_texture;
in vec3 out_fragPos;
in vec3 out_normal;

out vec4 FragColor;

void main() {
    vec3 normal = normalize(out_normal);
    vec3 viewDir = normalize(viewPos - out_fragPos);
    vec3 ambient = vec3(0.0);
    vec3 diffuseTotal = vec3(0.0);
    vec3 specularTotal = vec3(0.0);

    if (ambientEnabled) {
        // A parcela ambiente independe das fontes pontuais.
        ambient = vec3(ambientIntensity * material.ka);
    }

    for (int i = 0; i < numLights; i++) {
        // O groupID isola as iluminacoes dos ambientes interno e externo.
        if (!lights[i].enabled || lights[i].groupID != objectGroupID) {
            continue;
        }

        // Reflexao difusa de Lambert.
        vec3 lightOffset = lights[i].position - out_fragPos;
        float lightDistance = length(lightOffset);
        vec3 lightDir = normalize(lightOffset);
        float attenuation = 1.0 / (
            lights[i].attenuation.x
            + lights[i].attenuation.y * lightDistance
            + lights[i].attenuation.z * lightDistance * lightDistance
        );
        float diffuseFactor = max(dot(normal, lightDir), 0.0);
        diffuseTotal += (
            lights[i].color
            * material.kd
            * diffuseScale
            * diffuseFactor
            * attenuation
        );

        // Reflexao especular de Phong.
        vec3 reflectDir = reflect(-lightDir, normal);
        float specularFactor = pow(
            max(dot(viewDir, reflectDir), 0.0),
            material.ns
        );
        specularTotal += (
            lights[i].color
            * material.ks
            * specularScale
            * specularFactor
            * attenuation
        );
    }

    // A textura modula ambiente e difusa; especular e emissao somam luz.
    vec4 textureColor = texture(samplerTexture, out_texture);
    vec3 finalColor = (
        (ambient + diffuseTotal) * textureColor.rgb
        + specularTotal
        + emissiveColor
    );
    FragColor = vec4(finalColor, textureColor.a * material.opacity);
}
