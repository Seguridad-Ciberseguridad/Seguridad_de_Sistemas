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

## 5. Extensiones de VS Code

De las quince herramientas documentadas, **seis tienen extensión** y **dos
conectan** a un servicio externo.

| Herramienta | Extensión | ID | Conecta |
|---|---|---|---|
| [SonarQube Cloud](./sonarqube-cloud.md) | SonarQube for IDE | `SonarSource.sonarlint-vscode` | **Sí** — `paredes-work`, User Token |
| [Spectral](./spectral.md) | Spectral | `stoplight.spectral` | No |
| [Prisma](./prisma.md) | Prisma | `Prisma.prisma` | No |
| [ESLint](./eslint-y-vscode.md) | ESLint | `dbaeumer.vscode-eslint` | No |
| [GitHub Actions](./github-actions.md) | GitHub Actions | `github.vscode-github-actions` | Sesión de GitHub |
| [Docker](./docker-y-npm.md) | Container Tools | `ms-azuretools.vscode-docker` | No |
| SCA — [Trivy](./docker-y-npm.md) | Aqua Trivy | `AquaSecurityOfficial.trivy-vulnerability-scanner` | No — *saltar Aqua Platform* |
| SCA — [Snyk](./docker-y-npm.md) | Snyk Security | `snyk-security.snyk-vulnerability-scanner` | **Sí** — envía código a su nube |

URL de cualquiera: `https://marketplace.visualstudio.com/items?itemName=<ID>`

**Sin extensión** (y con motivo): [ZAP](./owasp-zap.md) y
[Burp](./burp-suite.md) son aplicaciones de escritorio ·
[Schemathesis](./schemathesis.md) es un CLI de Python ·
[Gitleaks](./gitleaks.md) no tiene oficial, va por hook y CI ·
[Faker](./faker.md) es una librería · [pgcrypto](./pgcrypto.md) es una extensión
de Postgres · [EasyPanel](./easypanel.md) es un panel web ·
[ASVS](./owasp-asvs.md) y [API Top 10](./owasp-api-top-10.md) son documentos.

Cada ficha lleva su sección con los enlaces al sitio oficial y a la
documentación. La lista operativa de qué instalar está en
[eslint-y-vscode.md](./eslint-y-vscode.md) §7.

> **Dos avisos que se repiten y conviene tener presentes:**
>
> **La raíz del workspace.** VS Code se abre en `Modulo_Policial`, no en las
> subcarpetas. Trivy y Snyk abiertos sobre la carpeta de documentación no
> encuentran nada porque no hay `package.json` que mirar — y un informe limpio
> ahí no significa nada.
>
> **Snyk envía código a sus servidores.** Aceptable aquí, porque el código fuente
> no contiene datos de ciudadanos, pero es una decisión que merece quedar
> escrita. Trivy hace un trabajo parecido en local.

---

## 6. La observación de fondo

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

## 7. Lo que sigue sin ficha

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

## 8. Orden recomendado

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

## 9. Nota sobre los enlaces del documento original

`ci-cd-y-herramientas.md` enlaza a `./README.md` ("Modelo de datos") y a
`./historias-de-usuario.md` (backlog, donde vive HU-21). **Ninguno de los dos
existe en esta carpeta.** El archivo parece copiado desde el repositorio
`Modulo_Policial`, donde esos vecinos sí están. Conviene corregir los enlaces o
traer los archivos, o las referencias a HU-21 quedan sin destino.
