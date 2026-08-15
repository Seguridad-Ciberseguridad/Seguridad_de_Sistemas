# CI/CD, calidad y entorno de desarrollo

> Última actualización: 6 de agosto de 2026.
> Modelo de datos: [README.md](./README.md) · Backlog: [historias-de-usuario.md](./historias-de-usuario.md)

---

## 1. Estado actual del pipeline

```
push a main  →  GitHub Actions  →  curl al deploy hook  →  EasyPanel reconstruye
```

Eso es **CD puro**. No hay CI: si se rompe el build o fallan los tests, **se
despliega igual** y el equipo se entera cuando la aplicación se cae.

| Repositorio | Workflow | Qué hace |
|---|---|---|
| `modulo_policia_backend` | `.github/workflows/main.yml` | `curl` al deploy hook |
| `modulo_policial_web` | `.github/workflows/main.yml` | `curl` al deploy hook |
| `modulo_policia_app` | — | nada |

> **Deuda conocida:** los comentarios de ambos workflows dicen *"Deploy a la app
> de EasyPanel de la Farmacia"* y el secret se llama `EASYPANEL_DEPLOY_HOOK_1`.
> Están copiados de otro proyecto. Conviene renombrarlos a
> `EASYPANEL_HOOK_WEB` / `EASYPANEL_HOOK_BACKEND` antes de tener tres.

---

## 2. Los dos conceptos

```
CI  Integración Continua   en cada push: compilar, correr tests, lint
CD  Entrega Continua       si todo pasa: preparar o publicar el despliegue
```

La diferencia práctica: sin CI, un error se detecta en producción. Con CI, en
dos minutos y antes de mezclar.

---

## 3. GitHub Actions vs GitLab CI

Decisión tomada: **GitHub Actions**.

| | GitHub Actions | GitLab CI |
|---|---|---|
| Configuración | `.github/workflows/*.yml` (varios) | `.gitlab-ci.yml` (uno) |
| Sintaxis | Verbosa, basada en *steps* | Compacta, basada en *stages* |
| Reutilización | Marketplace enorme | Catálogo menor |
| Minutos gratis | Ilimitados en repos públicos · 2000/mes privados | 400/mes |
| Entornos y rollback | Correcto | Superior |
| Autohospedado | Posible | Es su punto fuerte |

**Por qué Actions:** los tres repos ya están en GitHub, el pipeline es simple
(lint → test → build → hook), y el despliegue real lo hace EasyPanel, así que da
igual quién dispare el `curl`. Migrar cuesta días y no aporta nada.

**Cuándo reconsiderarlo:** si el proyecto exigiera GitLab autohospedado por
política de datos, o si el pipeline creciera a multi-stage con rollback.

---

## 4. SonarQube Cloud — análisis estático (SAST)

Lee el código **sin ejecutarlo** buscando bugs, vulnerabilidades y *code smells*.

### Cuenta

```
Organización   paredes-work
Plan           Free
Código actual  ~2.262 líneas  →  ~4,5% del límite
```

### Límites del plan gratuito

| | Free |
|---|---|
| Líneas de código **privado** | 50.000 |
| Líneas de código **público** | Ilimitadas |
| Miembros | 5 |

Con 2.262 líneas hay margen de sobra. Un sistema terminado de este tipo suele
quedar entre 15.000 y 30.000 líneas, así que el plan gratuito basta.

Si algún día se acerca al techo: poner algún repo en público deja de consumir
cuota, y se pueden excluir las migraciones de Prisma en
`sonar-project.properties`. El límite que puede quedarse corto antes es el de
**5 miembros**, no el de líneas.

### Las cinco trampas del montaje

1. **Apagar el *Automatic Analysis*** en `Administration → Analysis Method`.
   Es la causa número uno de fallo: si queda encendido y además se ejecuta el
   scanner desde Actions, el análisis choca y falla.
2. **El token debe ser *User Token***. Con un *project token*, *global token* o
   *scoped organization token*, la conexión se guarda pero el binding falla
   después sin mensaje claro.
3. **`fetch-depth: 0`** en `actions/checkout`, o el análisis de código nuevo
   sale incorrecto por trabajar sobre un clon superficial.
4. **La action es `SonarSource/sonarqube-scan-action`**. La antigua
   `sonarcloud-github-action` está deprecada.
5. **El proyecto debe existir en SonarQube Cloud antes de analizarlo.** La
   action analiza, pero no crea el proyecto.

Desde el 20 de julio de 2026 los análisis requieren **Java 21 o superior**. La
versión 7 de la action ya lo trae embebido; los ejemplos antiguos fallan.

### SonarQube for IDE

Extensión de VS Code, distinta del análisis en CI. En *Connected Mode*
sincroniza las reglas del servidor con el editor. Requiere el mismo tipo de
*User Token*. Sin conectar también funciona, con las reglas por defecto.

---

## 5. OWASP ZAP — no implementado

Es **DAST**: en vez de leer el código, ataca la aplicación **ya corriendo**.

```
SonarQube (SAST)   lee el código      →  "esta función es vulnerable"
OWASP ZAP (DAST)   ataca la app viva  →  "este endpoint responde sin token"
```

Se complementan. Donde encajaría aquí: tras desplegar a un entorno de pruebas,
escaneando la API de NestJS. Detectaría endpoints sin `JwtAuthGuard` o URLs de
archivos accesibles sin firma.

**Prioridad: baja por ahora.** Antes conviene cerrar lo que ya se sabe que
falta: el CI que corra tests y lint, y las contraseñas de prueba en una base
accesible desde internet. ZAP cobra sentido cuando el sistema esté cerca de
manejar datos reales de la EPI.

---

## 6. Despliegue en EasyPanel

El `curl` al *deploy hook* dispara una reconstrucción del contenedor desde el
`Dockerfile` del repositorio. Las variables de entorno se configuran en el panel
de EasyPanel, **no en el `.env`** del repositorio.

Las `NEXT_PUBLIC_*` se incrustan en el bundle **durante el build**, así que
tienen que llegar como *build args*, no solo como variables de ejecución.

### Problema resuelto: `npm ci` fallaba en el build de la web

```
npm error `npm ci` can only install packages when your package.json
          and package-lock.json are in sync
npm error Missing: @emnapi/runtime@1.11.3 from lock file
```

**Causa.** El lockfile se genera en Windows y el contenedor compila en Alpine
Linux (musl). Paquetes como `sharp` y `@tailwindcss/oxide` traen binarios
opcionales distintos por plataforma: en Alpine hacen falta `@emnapi/core` y
`@emnapi/runtime`, que npm no escribe en el lockfile al resolver desde Windows
porque allí no se necesitan. `npm ci` exige coincidencia exacta y falla siempre.

Regenerar el lockfile desde Windows **no lo arregla**, ni siquiera con
`npm install --package-lock-only --os=linux --libc=musl --cpu=x64`.

**Solución aplicada.** En el Dockerfile de la web, `npm ci` → `npm install`.
Parte del mismo lockfile pero resuelve los opcionales para la plataforma real
del contenedor. Se pierde reproducibilidad exacta (puede tomar parches nuevos
dentro del rango semver) a cambio de que el build funcione. El backend ya usaba
`npm install` desde el principio, por eso nunca falló.

**La alternativa correcta** sería generar el lockfile dentro de una imagen
`node:20-alpine`, lo que exige Docker en la máquina de desarrollo.

---

## 7. Entorno de desarrollo

### VS Code y el formateo

El workspace se abre en la carpeta **padre** `Modulo_Policial`, que contiene los
tres proyectos. VS Code solo lee `.vscode/settings.json` de la raíz del
workspace: uno dentro de `modulo_policia_backend/` se ignora.

La configuración vive en `Modulo_Policial/.vscode/settings.json` y usa **ESLint
como formateador**, no la extensión de Prettier:

```json
{
  "editor.tabSize": 2,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": { "source.fixAll.eslint": "explicit" },
  "eslint.format.enable": true,
  "eslint.workingDirectories": [{ "mode": "auto" }],
  "[typescript]": { "editor.defaultFormatter": "dbaeumer.vscode-eslint" }
}
```

**Por qué ESLint y no Prettier.** En el backend, Prettier ya corre *dentro* de
ESLint mediante `eslint-plugin-prettier`. Con las dos herramientas formateando
por separado aparecen peleas cuando una regla no coincide. Con esta
configuración hay una sola fuente de verdad, y lo que se ve al formatear es
exactamente lo que valida `npm run lint`.

`eslint.workingDirectories` es necesario porque hay tres proyectos con
configuraciones de ESLint distintas en el mismo workspace.

### Versiones de Node

```
Máquina de desarrollo   Node 24 · npm 11.6.2
Dockerfile              node:20-alpine · npm 10.8.2
```

Generar el lockfile con una versión de npm y consumirlo con otra dos majors por
detrás es una fuente recurrente de problemas. Conviene alinearlos.

### Errores del editor que no son errores

- **`Property 'X' does not exist`** → error real de TypeScript, el código no
  compila
- **`Unsafe call` / `Unsafe assignment`** → reglas de ESLint, suelen ser
  *consecuencia* en cascada de un error de TypeScript
- **Subrayados que persisten tras instalar dependencias** → caché del servidor
  de TypeScript. `Ctrl+Shift+P` → `TypeScript: Restart TS Server`

Regla práctica: ante muchos errores rojos, ejecutar `npx tsc --noEmit`. Suele
haber dos o tres causas reales y el resto es ruido derivado.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Job de CI antes del deploy | **Nada** — ver HU-21 | Alta |
| SonarQube en el pipeline | Cuenta creada, falta el workflow | Media |
| Renombrar los secrets de EasyPanel | Pendiente | Baja |
| Alinear versiones de Node | Pendiente | Baja |
| OWASP ZAP | Sin empezar | Baja |

### Lo que más valor aporta hoy

Un job que ejecute `lint`, `test` y `build`, y que el deploy dependa de él con
`needs:`. El backend ya tiene **22 tests** que hoy no ejecuta nadie de forma
automática, y el parser del Excel es exactamente el tipo de código donde una
regresión pasa desapercibida hasta que un parte real falla.

Debe correr también en Pull Requests, y el backend necesita un servicio Postgres
en el runner para sus tests.
