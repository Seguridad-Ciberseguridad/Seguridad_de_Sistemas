# DevSecOps — plan de 3 meses

> Ritmo: **3 sesiones/semana, 1 hora mínimo por sesión** (ej. lun/mié/vie). ~36 sesiones en total.
> No usa fechas fijas de calendario a propósito — corre en paralelo al diplomado de Ciberseguridad y al camino HTB, con el hueco que quede en la semana. Si una semana solo da para 2 sesiones, se sigue: no se acumula.
>
> **Por qué este plan existe:** ya trabajas como desarrollador en Tigo Bolivia y ya tienes, en este mismo repositorio, un proyecto real (`Modulo_Policial`) con una hoja de ruta de seguridad sin ejecutar — ver el "Orden recomendado" en [herramientas/README.md §9](herramientas/README.md#9-orden-recomendado). Este plan no es teoría genérica: es la forma de **estudiar DevSecOps ejecutando esa hoja de ruta real**, fase por fase. Cada semana tiene una lectura corta + una acción concreta sobre el proyecto.
>
> Creado: **2026-08-24**.

---

## Qué es DevSecOps, en una frase

Meter seguridad **dentro** del pipeline (CI/CD) en vez de revisarla al final: cada push pasa por SAST, SCA y lint antes de poder llegar a producción — "shift-left", mover el control de detección lo más temprano posible en el ciclo.

```
Sin DevSecOps:  código → deploy → (algún día) alguien revisa seguridad
Con DevSecOps:  código → CI (lint+test+SAST+SCA) → deploy solo si pasa
```

Este repositorio ya tiene el diagnóstico hecho (ver [ci-cd-y-herramientas.md](ci-cd-y-herramientas.md) y [herramientas/README.md](herramientas/README.md)): hay CD sin CI, y las herramientas de seguridad (SonarQube, ZAP, Gitleaks, Trivy) están evaluadas pero casi ninguna está corriendo todavía. Este plan es cerrar esa brecha.

---

## Mes 1 — Fundamentos + Fase 0 y Fase 1 (lo urgente)

**Objetivo del mes:** que el pipeline tenga CI real (no solo CD) y que el hallazgo más grave del proyecto (Postgres expuesto con contraseñas de prueba, ver [herramientas/README.md §7](herramientas/README.md#7-la-observación-de-fondo)) quede cerrado.

### Semana 1 — CI vs CD, y por qué el proyecto no tiene CI

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 1 | Leer [ci-cd-y-herramientas.md §2](ci-cd-y-herramientas.md) (CI vs CD) + [github-actions.md](herramientas/github-actions.md). Diferencia real: sin CI, el error se detecta en producción | Confirmar en los 3 repos qué workflow existe hoy y qué le falta (`needs:`, tests, lint) |
| 2 | **Fase 0** — auditar qué datos hay en la base expuesta, rotar credenciales | Ejecutar la Fase 0 completa del "Orden recomendado" — es la prioridad real, no un ejercicio |
| 3 | Diseñar el job de CI: `lint → test → build`, con Postgres como servicio en el runner (el backend necesita BBDD para sus 22 tests) | Escribir el YAML del workflow (aunque no se mergee todavía) |

### Semana 2 — Implementar el CI

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 4 | GitHub Actions a fondo: *services* (Postgres en el runner), *matrix*, *needs* | Levantar el servicio Postgres en el workflow y correr los 22 tests existentes en CI |
| 5 | Hacer que el **deploy dependa del CI** (`needs: build-and-test`) | Conectar el job nuevo con el `curl` al deploy hook existente |
| 6 | Probar en un PR: romper un test a propósito y confirmar que el deploy no se dispara | Merge del CI real a los 3 repos |

### Semana 3 — Gitleaks + Dependabot (SCA barato)

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 7 | Leer [gitleaks.md](herramientas/gitleaks.md). Secretos en el repo y su **historial**, no solo el commit actual | Correr Gitleaks contra los 3 repos en local, revisar el historial completo |
| 8 | Añadir Gitleaks como paso del CI (falla el build si encuentra un secreto) | Merge del paso en el workflow |
| 9 | Dependabot: qué es, cómo se configura con un `.yml`, por qué el SCA suele encontrar más que el SAST en un proyecto chico (ver [herramientas/README.md §8](herramientas/README.md#8-lo-que-sigue-sin-ficha)) | Activar Dependabot en los 3 repos + correr `npm audit` una vez a mano |

### Semana 4 — Repaso y cierre de Fase 1

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 10 | Repasar sin mirar apuntes: dibujar el pipeline completo de memoria (CI + CD + dónde entra cada herramienta) | — |
| 11 | Corregir la deuda menor pendiente: renombrar los secrets de EasyPanel (`EASYPANEL_DEPLOY_HOOK_1` → nombres por proyecto) | Aplicar el cambio |
| 12 | **Checkpoint del mes:** ¿el CI bloquea un build roto? ¿Gitleaks y Dependabot están activos? Si algo falta, se arrastra a la semana 5 antes de seguir | Documentar el estado real en una nota corta |

---

## Mes 2 — Seguridad en el código (Fase 2 y 3)

**Objetivo del mes:** los controles que se implementan **en código**, no con herramientas externas — la parte que hoy no tiene ficha (ver [herramientas/README.md §2](herramientas/README.md#8-lo-que-sigue-sin-ficha)).

### Semana 5 — Controles base de NestJS

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 13 | Guard global de JWT: por qué "por ruta" no basta, cómo se aplica globalmente | Auditar qué endpoints del backend quedan sin guard hoy |
| 14 | `ValidationPipe` con `whitelist: true` — por qué rechaza campos no declarados en el DTO (previene *mass assignment*) | Confirmar que está activo globalmente, no solo en algunos controllers |
| 15 | `@nestjs/throttler` (rate limiting) + `helmet` (headers HTTP de seguridad) | Configurar ambos si faltan |

### Semana 6 — OWASP API Top 10 aplicado

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 16 | Leer [owasp-api-top-10.md](herramientas/owasp-api-top-10.md) completo | Recorrer la API real endpoint por endpoint contra la lista |
| 17 | **BOLA** (Broken Object Level Authorization) a fondo — el hallazgo #1 en APIs, el que ninguna herramienta automática detecta (ver [herramientas/README.md §2](herramientas/README.md#2-seguridad-de-api)) | Sesión manual con Burp ([burp-suite.md](herramientas/burp-suite.md)): probar si un usuario puede acceder a recursos de otro cambiando un ID |
| 18 | Repasar los hallazgos de BOLA con el equipo/contigo mismo; priorizar arreglos | Documentar los endpoints vulnerables encontrados |

### Semana 7 — Control de acceso y auditoría

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 19 | CASL: control de acceso basado en atributos/roles, más allá de un guard binario | Evaluar si el proyecto necesita CASL o si los roles actuales bastan |
| 20 | Tabla de auditoría **append-only**: qué se registra, por qué nunca se debe poder actualizar/borrar una fila de auditoría | Diseñar el esquema si no existe |
| 21 | Implementar el registro de auditoría en al menos 1 acción sensible (login, cambio de rol, borrado) | Merge de la migración + el código |

### Semana 8 — Repaso y cierre de Fase 2-3

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 22 | Repasar de memoria: los 4 controles de código (guard, ValidationPipe, throttler, helmet) + BOLA + auditoría | — |
| 23 | Cerrar cualquier hallazgo de BOLA que siga pendiente | — |
| 24 | **Checkpoint del mes** | Documentar qué quedó y qué no |

---

## Mes 3 — SAST/DAST en pipeline + cadena de suministro (Fase 4-5)

**Objetivo del mes:** que SonarQube y Spectral/Schemathesis corran en cada push, y que la imagen de contenedor y las dependencias de terceros queden auditadas — cerrando el "Orden recomendado" completo.

### Semana 9 — Contrato de API: Spectral y Schemathesis

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 25 | Leer [spectral.md](herramientas/spectral.md): valida que el contrato OpenAPI esté bien diseñado, corre en segundos | Añadir Spectral al CI |
| 26 | Leer [schemathesis.md](herramientas/schemathesis.md): valida que la implementación **cumpla** el contrato, corre en 5-20 min | Configurar Schemathesis como job nocturno |
| 27 | Revisar los primeros hallazgos de ambos | Corregir lo que aparezca |

### Semana 10 — SonarQube con Quality Gate bloqueante

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 28 | Leer [sonarqube-cloud.md](herramientas/sonarqube-cloud.md) completo, incluidas **las cinco trampas del montaje** ([ci-cd-y-herramientas.md §4](ci-cd-y-herramientas.md#4-sonarqube-cloud--análisis-estático-sast)) | Montar el workflow con `SonarSource/sonarqube-scan-action`, `fetch-depth: 0`, User Token |
| 29 | Configurar el Quality Gate para que **bloquee el merge**, no solo reporte | Activar el bloqueo real |
| 30 | Revisar los hallazgos iniciales de SonarQube sobre el código actual | Triaje: cuáles son reales, cuáles son ruido |

### Semana 11 — Cadena de suministro: Trivy y contenedores

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 31 | Leer [docker-y-npm.md §6](herramientas/docker-y-npm.md) sobre SCA. Por qué en un proyecto chico el SCA (dependencias de terceros) suele encontrar más que el SAST (código propio) | Instalar la extensión Trivy en VS Code, escanear la imagen construida |
| 32 | Corregir vulnerabilidades encontradas en la imagen base o en dependencias | Actualizar Dockerfile/`package.json` según corresponda |
| 33 | Decisión consciente: ¿se usa también Snyk? (envía código a su nube — ver el aviso en [herramientas/README.md §6](herramientas/README.md#6-extensiones-de-vs-code)) | Documentar la decisión tomada y por qué |

### Semana 12 — ZAP, cierre del plan y portfolio

| Sesión | Contenido | Acción sobre el proyecto real |
|---|---|---|
| 34 | Leer [owasp-zap.md](herramientas/owasp-zap.md). DAST: ataca la app **ya corriendo**, complementa a SonarQube (que solo lee código) | Configurar un escaneo ZAP nocturno contra un entorno de pruebas |
| 35 | Repaso general de las 3 fases completas: CI real, controles en código, SAST/DAST/SCA en pipeline | — |
| 36 | **Cierre del plan** — documentar el antes/después del pipeline como caso de estudio (portfolio) | Actualizar [herramientas/README.md §9](herramientas/README.md#9-orden-recomendado) marcando qué fases quedaron completas |

---

## Checklist de progreso

### Mes 1
- [ ] Semana 1 — CI vs CD + Fase 0 (auditoría/rotación de credenciales)
- [ ] Semana 2 — CI implementado, deploy depende de `needs:`
- [ ] Semana 3 — Gitleaks + Dependabot activos
- [ ] Semana 4 — Repaso + secrets de EasyPanel renombrados

### Mes 2
- [ ] Semana 5 — Guard global, ValidationPipe whitelist, throttler, helmet
- [ ] Semana 6 — OWASP API Top 10 recorrido + sesión BOLA con Burp
- [ ] Semana 7 — CASL evaluado + tabla de auditoría append-only implementada
- [ ] Semana 8 — Repaso + hallazgos de BOLA cerrados

### Mes 3
- [ ] Semana 9 — Spectral + Schemathesis en el pipeline
- [ ] Semana 10 — SonarQube con Quality Gate bloqueante
- [ ] Semana 11 — Trivy sobre la imagen + decisión sobre Snyk
- [ ] Semana 12 — ZAP nocturno + cierre + portfolio → **plan DevSecOps completo**

---

## Después de los 3 meses

Con las 5 fases del "Orden recomendado" ejecutadas, el proyecto real queda como pieza de portfolio verificable: no es "estudié DevSecOps", es "implementé CI/CD seguro, cerré BOLA, y monté SAST+DAST+SCA en un sistema real usado en producción". Eso es exactamente lo que un cambio de rol hacia DevSecOps/AppSec pide en una entrevista — más que cualquier certificación.

Si en ese punto se quiere una certificación formal, las opciones vendor-neutral más reconocidas son **Practical DevSecOps — Certified DevSecOps Professional (CDP)** y, del lado cloud, **AWS Certified DevOps Engineer** si el proyecto termina desplegado ahí. Ninguna es necesaria para este plan — son un paso posterior, opcional.
