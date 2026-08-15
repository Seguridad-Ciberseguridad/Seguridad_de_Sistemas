# Herramientas — viabilidad para Seguridad de Sistemas

> Fichas de las herramientas del proyecto, evaluadas por lo que aportan **a la
> seguridad del sistema**, no por lo que aportan al flujo de trabajo.
>
> Bloque 1 — herramientas descritas en [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md)
> Bloque 2 — herramientas de seguridad de API y datos, añadidas después

---

## 1. Pipeline y despliegue

| Herramienta | Categoría | ¿Es seguridad? | Estado hoy | Veredicto |
|---|---|---|---|---|
| [SonarQube Cloud](./sonarqube-cloud.md) | SAST | **Sí, directa** | Cuenta creada, sin workflow | **Viable y prioritaria** |
| [OWASP ZAP](./owasp-zap.md) | DAST | **Sí, directa** | Sin empezar | **Viable, después del CI** |
| [GitHub Actions](./github-actions.md) | Orquestador CI/CD | No, pero es el habilitador | Solo `curl` al hook | **Viable — es el requisito previo** |
| [Docker y npm](./docker-y-npm.md) | Build / cadena de suministro | Indirecta, y hoy **en contra** | `npm install` en la web | **Viable con corrección pendiente** |
| [EasyPanel](./easypanel.md) | Despliegue | No — es superficie de ataque | En producción | **Viable, pero es el punto más expuesto** |
| [ESLint y VS Code](./eslint-y-vscode.md) | Calidad de código | Marginal | Configurado | **Viable, aporte bajo** |

De las seis, **dos son herramientas de seguridad propiamente dichas** (SonarQube
y ZAP), tres son infraestructura que *permite* o *estorba* a la seguridad, y una
es calidad de código.

---

## 2. Seguridad de API

| Herramienta | Qué verifica | Automatizable | Cuándo corre |
|---|---|---|---|
| [Spectral](./spectral.md) | El **contrato** OpenAPI está bien diseñado | Sí | Cada push, segundos |
| [Schemathesis](./schemathesis.md) | La implementación **cumple** el contrato | Sí | Nocturno, 5–20 min |
| [OWASP ZAP](./owasp-zap.md) | La aplicación **resiste** un ataque | Sí | Nocturno |
| [Burp Suite Community](./burp-suite.md) | Lo que ninguna automatiza: **BOLA** | **No** | Sesión manual |

Las tres primeras se solapan poco y se complementan bien. La cuarta no es
opcional: el fallo nº1 de las APIs es indetectable de forma automática — ver
[owasp-api-top-10.md](./owasp-api-top-10.md) §3.

---

## 3. Seguridad de datos

| Herramienta | Para qué | Veredicto |
|---|---|---|
| [Gitleaks](./gitleaks.md) | Secretos en el repositorio y su historial | **Viable, coste casi nulo** |
| [Prisma](./prisma.md) | Ya lo usas: seguro por defecto, con dos escapes | **Cerrar los escapes** |
| [Faker](./faker.md) | Datos de prueba sintéticos | **Viable, resuelve un problema abierto** |
| [pgcrypto](./pgcrypto.md) | Cifrado de columnas en reposo | **Viable, pero no es lo primero** |

---

## 4. Marcos de referencia

| | Responde a | Esfuerzo |
|---|---|---|
| [OWASP API Security Top 10](./owasp-api-top-10.md) | ¿Por dónde empiezo? | Media hora de lectura |
| [OWASP ASVS](./owasp-asvs.md) | ¿Cuándo he terminado? | Semanas, por capítulos |

Se usan juntos y en ese orden. El Top 10 cambia inmediatamente en qué trabajas
primero; ASVS te dice qué te falta.

---

## 5. La observación de fondo

El documento original está bien construido como bitácora de ingeniería, pero
ordena las prioridades por **coste de implementación**, no por **riesgo**. En la
tabla de pendientes aparecen como prioridad *baja*:

- renombrar los secrets de EasyPanel (heredados de otro proyecto),
- OWASP ZAP,

mientras que dentro de la sección 5 hay, en una frase de paso, esto:

> *"las contraseñas de prueba en una base accesible desde internet"*

Eso no es un pendiente de prioridad baja. Es, con diferencia, el hallazgo más
grave del documento, y está enterrado como justificación para posponer otra
cosa. Ver [easypanel.md](./easypanel.md).

---

## 6. Lo que sigue sin ficha

Con [Gitleaks](./gitleaks.md) ya cubierto, quedan dos frentes de cadena de
suministro sin documentar:

| Frente | Qué lo cubre | Coste |
|---|---|---|
| **Dependencias vulnerables** (SCA) | Dependabot + `npm audit` en CI | Minutos — Dependabot es un `.yml` |
| **Imagen de contenedor** | Trivy sobre la imagen construida | Una hora |

En un proyecto de este tamaño, **el SCA suele encontrar más que el SAST**: el
código propio son ~2.262 líneas, pero `node_modules` son decenas de miles de
líneas de terceros. SonarQube no las mira. Tratado de pasada en
[docker-y-npm.md](./docker-y-npm.md) §6.

Tampoco tienen ficha los **controles que se implementan en código** —guard global
de JWT, `ValidationPipe` con `whitelist`, CASL, `@nestjs/throttler`, helmet,
tabla de auditoría—, que no son herramientas pero pesan más que varias de las que
sí están aquí.

---

## 7. Orden recomendado

```
Fase 0  Cerrar Postgres, rotar credenciales, auditar qué datos hay
Fase 1  CI con lint+test+build y needs: · Dependabot · npm audit · Gitleaks
Fase 2  Guard global · ValidationPipe whitelist · throttler · helmet
        · regla ESLint anti-$queryRawUnsafe
Fase 3  CASL · tabla de auditoría append-only
Fase 4  Spectral · Schemathesis · SonarQube con Quality Gate bloqueante
Fase 5  CrowdSec · backups con restauración probada · ZAP nocturno
```

La fase 0 no depende de nada y no necesita ninguna herramienta nueva. Las fases
2 y 3 tampoco dependen del CI: se pueden avanzar en paralelo si el pipeline se
atasca.

Transversal a todo: una pasada de [Burp](./burp-suite.md) buscando BOLA, que no
encaja en ninguna fase porque no depende de ninguna.

---

## 8. Nota sobre los enlaces del documento original

`ci-cd-y-herramientas.md` enlaza a `./README.md` ("Modelo de datos") y a
`./historias-de-usuario.md` (backlog, donde vive HU-21). **Ninguno de los dos
existe en esta carpeta.** El archivo parece copiado desde el repositorio
`Modulo_Policial`, donde esos vecinos sí están. Conviene corregir los enlaces o
traer los archivos, o las referencias a HU-21 quedan sin destino.
