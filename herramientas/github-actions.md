# GitHub Actions — orquestador CI/CD

> Categoría: automatización · **Veredicto: viable — es el requisito previo de todo lo demás**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §1–3

---

## 1. Estado actual

```
push a main  →  GitHub Actions  →  curl al deploy hook  →  EasyPanel reconstruye
```

Eso es **CD puro**. No hay CI: si se rompe el build o fallan los tests, **se
despliega igual**, y el equipo se entera cuando la aplicación se cae.

| Repositorio | Workflow | Qué hace |
|---|---|---|
| `modulo_policia_backend` | `.github/workflows/main.yml` | `curl` al deploy hook |
| `modulo_policial_web` | `.github/workflows/main.yml` | `curl` al deploy hook |
| `modulo_policia_app` | — | nada |

---

## 2. Viabilidad para Seguridad de Sistemas

Actions **no es una herramienta de seguridad**. Es el plano de control donde se
ejecutan las que sí lo son. Su viabilidad se juzga por dos cosas:

**Como habilitador: es el requisito previo.** SonarQube, ZAP, Dependabot, Trivy y
Gitleaks son todos jobs de un pipeline. Sin pipeline, cada uno es un comando que
alguien debe acordarse de ejecutar a mano, y eso no ocurre. Que hoy exista un
workflow que solo hace `curl` significa que **la infraestructura está montada y
falta un solo job**; es el cambio con mejor relación valor/esfuerzo del proyecto.

**Como superficie de ataque: es de las más jugosas del sistema.** El runner tiene
acceso a los secrets, al código y al hook que despliega a producción. Un
compromiso del pipeline no compromete un servidor: compromete **todo lo que el
pipeline puede desplegar**. Los ataques de cadena de suministro de los últimos
años han ido justo aquí. La sección 5 lo trata en detalle.

---

## 3. Por qué Actions y no GitLab CI

Decisión ya tomada: **GitHub Actions**.

| | GitHub Actions | GitLab CI |
|---|---|---|
| Configuración | `.github/workflows/*.yml` (varios) | `.gitlab-ci.yml` (uno) |
| Sintaxis | Verbosa, basada en *steps* | Compacta, basada en *stages* |
| Reutilización | Marketplace enorme | Catálogo menor |
| Minutos gratis | Ilimitados en repos públicos · 2000/mes privados | 400/mes |
| Entornos y rollback | Correcto | Superior |
| Autohospedado | Posible | Es su punto fuerte |

**El razonamiento se sostiene.** Los tres repos ya están en GitHub, el pipeline es
simple (lint → test → build → hook) y el despliegue real lo hace EasyPanel, así
que da igual quién dispare el `curl`. Migrar cuesta días y no aporta nada.

**Cuándo reconsiderarlo:** si el proyecto exigiera GitLab autohospedado por
política de datos —plausible en un sistema de la EPI si aparece un requisito de
que el código no salga de infraestructura propia—, o si el pipeline creciera a
multi-stage con rollback.

---

## 4. El CI que falta

Un job que ejecute `lint`, `test` y `build`, y que el deploy **dependa de él**.
El backend ya tiene **22 tests que hoy no ejecuta nadie de forma automática**, y
el parser del Excel es exactamente el tipo de código donde una regresión pasa
desapercibida hasta que un parte real falla.

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:                    # debe correr también en PR

permissions:
  contents: read                   # ver sección 5

jobs:
  ci:
    runs-on: ubuntu-latest

    services:                      # el backend necesita Postgres para sus tests
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
        ports: ['5432:5432']

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20         # la misma del Dockerfile, no la 24 local
          cache: npm

      - run: npm ci
      - run: npm run lint
      - run: npx prisma migrate deploy
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
      - run: npm test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
      - run: npm run build

  deploy:
    needs: ci                      # ← esto es lo que convierte CD en CI/CD
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: curl -fsSL -X POST "${{ secrets.EASYPANEL_HOOK_BACKEND }}"
```

Tres detalles que no son cosméticos:

- **`needs: ci`** es la línea entera del cambio. Sin ella el deploy sigue
  disparándose en paralelo y no se ha ganado nada.
- **`if: github.ref == 'refs/heads/main'`** evita desplegar desde un PR.
- **`curl -f`** hace que un hook que responda 500 falle el job. Sin `-f`, `curl`
  devuelve 0 aunque el servidor conteste un error, y el workflow sale verde
  habiendo fallado el despliegue.

---

## 5. Endurecer el propio pipeline

Cinco medidas, todas de coste bajo:

**1. `permissions:` explícito y mínimo.** Por defecto el `GITHUB_TOKEN` puede
tener permiso de escritura sobre el repositorio. Un `permissions: contents: read`
a nivel de workflow reduce el daño de cualquier paso comprometido. Se sube el
permiso solo en el job que lo necesite.

**2. Fijar las actions de terceros.** `uses: alguien/action@v3` ejecuta **código
arbitrario de un tercero con acceso a los secrets del job**, y una etiqueta se
puede mover. Para actions fuera de `actions/` y de proveedores de confianza,
fijar por SHA:

```yaml
- uses: zaproxy/action-api-scan@1b8e4f... # v0.9.0
```

**3. `pull_request_target` está prohibido salvo que se sepa exactamente lo que se
hace.** Ese disparador da acceso a los secrets a un workflow ejecutado desde el
código de un PR externo. Combinado con un `checkout` de la rama del PR, es
ejecución remota de código con las llaves del reino. Se usa `pull_request`.

**4. Los secrets no se imprimen.** Actions enmascara los que reconoce, pero no
sobrevive a una transformación (un `base64`, un troceado). Nada de `echo` sobre
un secret ni `set -x` en scripts que los manejen.

**5. Entornos protegidos.** Un `environment: production` con revisor obligatorio
convierte el despliegue en una acción deliberada. Cuando el sistema maneje datos
reales de la EPI, esto deja de ser opcional.

---

## 6. La deuda de los secrets

Los comentarios de ambos workflows dicen *"Deploy a la app de EasyPanel de la
Farmacia"* y el secret se llama `EASYPANEL_DEPLOY_HOOK_1`. Están **copiados de
otro proyecto**.

El documento original lo clasifica como prioridad baja, tratándolo como un
problema de nomenclatura: conviene renombrarlos a `EASYPANEL_HOOK_WEB` /
`EASYPANEL_HOOK_BACKEND` antes de tener tres.

**Como problema de nombres es menor. Como problema de seguridad no lo es tanto**,
y merece una comprobación de cinco minutos: si el valor se copió junto con el
nombre, hay un secret compartido entre dos proyectos no relacionados, y quien
tenga acceso al repositorio de la farmacia puede disparar despliegues aquí. El
sufijo `_1` sugiere además que hubo más de uno.

Lo que hay que verificar, en este orden:

1. ¿El valor de `EASYPANEL_DEPLOY_HOOK_1` apunta al servicio correcto?
2. ¿Existe el mismo secret en el repositorio de la farmacia?
3. Si la respuesta a (2) es sí: **regenerar el hook en EasyPanel**, no solo
   renombrar el secret. Renombrar no invalida la URL antigua.

---

## 7. Extensión de VS Code

| | |
|---|---|
| Extensión | **GitHub Actions** |
| ID | `github.vscode-github-actions` |
| Marketplace | https://marketplace.visualstudio.com/items?itemName=github.vscode-github-actions |
| Sitio | https://docs.github.com/actions |

Oficial de GitHub. Dos cosas útiles:

- **Validación del YAML mientras escribes.** Los workflows fallan a menudo por
  indentación o por un nombre de clave mal puesto, y descubrirlo en el editor
  ahorra el ciclo de commit → push → esperar → leer el error.
- **Las ejecuciones en la barra lateral**, con logs por paso, sin abrir el
  navegador.

Se autentica con la sesión de GitHub que VS Code ya tiene; no hace falta token.

Es especialmente oportuna ahora: vas a escribir el workflow de CI de la sección 4
desde cero, y es justo el momento en que más se nota.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Job de CI antes del deploy (`needs:`) | Nada — ver HU-21 | **Alta** |
| CI también en Pull Requests | Nada | **Alta** |
| Servicio Postgres en el runner | Nada | Alta |
| Verificar si el hook está compartido con otro proyecto | Nada | **Media** |
| `permissions:` explícito en los workflows | Nada | Media |
| Renombrar los secrets | Pendiente | Baja |
| Fijar actions de terceros por SHA | Nada | Baja |
| Workflow en `modulo_policia_app` | No existe | Baja |
