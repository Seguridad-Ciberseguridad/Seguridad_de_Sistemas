# Docker y npm — cadena de suministro

> Categoría: build y dependencias · **Veredicto: viable, con una corrección pendiente**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §6–7

---

## 1. Por qué esto es un tema de seguridad

En una aplicación Node, el código propio son ~2.262 líneas. Las dependencias son
decenas de miles de líneas escritas por gente desconocida, que se ejecutan con los
mismos privilegios que el código propio y pueden correr *scripts* durante la
instalación.

**El build es la frontera de confianza del sistema.** Todo lo que entra por ahí
acaba en producción. SonarQube no mira `node_modules`, y ZAP solo ve el resultado.
Este es el frente que no cubre ninguna de las dos.

---

## 2. El problema resuelto: `npm ci` fallaba en el build de la web

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

**Solución aplicada.** En el Dockerfile de la web, `npm ci` → `npm install`. Parte
del mismo lockfile pero resuelve los opcionales para la plataforma real del
contenedor. El backend ya usaba `npm install` desde el principio, por eso nunca
falló.

El diagnóstico es correcto y la solución desbloquea el build. Lo que sigue es lo
que el cambio cuesta.

---

## 3. Lo que se pierde con `npm install` no es solo reproducibilidad

El documento lo describe como *"se pierde reproducibilidad exacta (puede tomar
parches nuevos dentro del rango semver) a cambio de que el build funcione"*.

Eso es exacto, e incompleto. Reformulado desde seguridad: **el contenedor que
corre en producción se construye con paquetes que nadie ha revisado y que no
estaban en el lockfile cuando se aprobó el código.**

Concretamente:

| | `npm ci` | `npm install` |
|---|---|---|
| Versiones instaladas | Las del lockfile, exactas | Las más nuevas dentro del rango semver |
| Verifica integridad (hashes) | Sí, de todo | Solo de lo que ya estaba anclado |
| Modifica el lockfile | No | Sí, silenciosamente |
| Dos builds del mismo commit | Idénticos | Pueden diferir |
| Un `npm audit` en CI predice lo que va a producción | Sí | **No** |

La última fila es la que importa para el pipeline que se quiere montar: si el CI
audita un árbol de dependencias y el Dockerfile instala otro, **el resultado de la
auditoría no dice nada sobre lo desplegado**. Se está midiendo una cosa y
enviando otra.

Y es exactamente el vector de los ataques de cadena de suministro conocidos: se
compromete la cuenta de un mantenedor de un paquete transitivo pequeño, se
publica un parche malicioso (`1.2.3` → `1.2.4`), y todo build con rango abierto
lo recoge en la siguiente reconstrucción. Con `npm ci` haría falta que alguien
actualizara el lockfile y lo mezclara.

---

## 4. La alternativa correcta

El documento la nombra: **generar el lockfile dentro de una imagen
`node:20-alpine`**, lo que exige Docker en la máquina de desarrollo. Ese es el
arreglo bueno, y el requisito no es grave — Docker Desktop en Windows basta:

```bash
docker run --rm -v "$PWD":/app -w /app node:20-alpine \
  sh -c "npm install --package-lock-only"
```

El lockfile resultante incluye los binarios de musl, se commitea, y el Dockerfile
puede volver a `npm ci`. Se recupera todo lo de la columna izquierda de la tabla.

Alternativa sin Docker local: **generar el lockfile en un job de GitHub Actions**
que corra sobre `node:20-alpine` y abra un PR con el resultado. Más artificioso,
pero no necesita nada instalado.

Mientras tanto, `npm install` es un compromiso aceptable y consciente. Lo que no
conviene es olvidar que está ahí.

---

## 5. Alinear las versiones de Node

```
Máquina de desarrollo   Node 24 · npm 11.6.2
Dockerfile              node:20-alpine · npm 10.8.2
```

Generar el lockfile con una versión de npm y consumirlo con otra dos majors por
detrás es una fuente recurrente de problemas: el formato del lockfile ha cambiado
entre versiones y la resolución de opcionales no es idéntica. Parte del problema
de la sección 2 nace aquí.

Se arregla con un `.nvmrc` en la raíz de cada repo y usándolo también en el CI:

```
20
```
```yaml
- uses: actions/setup-node@v4
  with:
    node-version-file: '.nvmrc'
```

Tres entornos —local, CI y contenedor— con la misma versión. Baja prioridad, pero
elimina una clase entera de fallos difíciles de diagnosticar.

---

## 6. Lo que falta: mirar dentro de las dependencias

Nada del inventario actual revisa `node_modules`. Tres controles, por orden de
coste:

**1. Dependabot** — un archivo, y GitHub abre PRs con las actualizaciones de
seguridad:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: npm
    directory: /
    schedule: { interval: weekly }
    open-pull-requests-limit: 5
```

**2. `npm audit` en el CI** — un paso:

```yaml
- run: npm audit --audit-level=high
```

Se empieza por `high` a propósito. Con `moderate` el ruido en un proyecto Node es
tal que el paso acaba desactivado en dos semanas.

**3. Trivy sobre la imagen construida** — cubre lo que `npm audit` no ve: paquetes
del sistema operativo dentro de la imagen base.

```yaml
- uses: aquasecurity/trivy-action@master
  with:
    image-ref: modulo-policia-backend:${{ github.sha }}
    severity: HIGH,CRITICAL
    exit-code: '1'
```

---

## 7. Endurecer el Dockerfile

Cuatro cosas que se comprueban de una pasada:

- **Usuario no root.** Por defecto el proceso corre como root dentro del
  contenedor; una RCE en la aplicación pasa a ser root en el contenedor. Las
  imágenes de Node traen un usuario `node`: `USER node` antes del `CMD`.
- **Multi-stage.** Que la imagen final no lleve el compilador de TypeScript, las
  devDependencies ni el código fuente. Menos superficie y menos peso.
- **Etiqueta fija en la imagen base.** `node:20-alpine` se mueve; `node:20.18-alpine`
  no. Para reproducibilidad de verdad, por digest.
- **Nada de secretos en capas.** Un `ARG` con un token queda en el historial de la
  imagen aunque después se borre el archivo.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Dependabot en los tres repos | No existe | **Alta** |
| `npm audit --audit-level=high` en CI | No existe | **Alta** |
| Volver a `npm ci` con lockfile generado en Alpine | Pendiente | Media |
| `USER node` en los Dockerfiles | Sin verificar | Media |
| `.nvmrc` y versiones alineadas | Pendiente | Baja |
| Trivy sobre la imagen | No existe | Baja |
| Imagen base fijada por versión menor o digest | Sin verificar | Baja |
