# ESLint y VS Code — entorno de desarrollo

> Categoría: calidad de código · **Veredicto: viable, aporte a seguridad bajo pero no nulo**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §7

---

## 1. Viabilidad para Seguridad de Sistemas

Con honestidad: **esto es calidad de código, no seguridad.** Un formateo
consistente y un linter no impiden una inyección SQL ni un endpoint sin guard.
Si el criterio es "qué aporta a la seguridad del sistema", esta es la entrada de
menor aporte del inventario.

Dicho eso, tiene dos conexiones reales con seguridad, y una de ellas es
relevante en este proyecto:

**a) Las reglas de tipos de TypeScript sí atrapan fallos con consecuencias.** Las
reglas `no-unsafe-*` que el documento menciona como "ruido" marcan valores de
tipo `any` fluyendo por el código. En un backend, un `any` viene casi siempre de
un `req.body`, de un `JSON.parse` o de una fila de base de datos: **entrada no
validada, sin tipar, moviéndose por la aplicación.** Ahí es donde empiezan las
inyecciones y los *mass assignment*. No es ruido; es un mapa de por dónde entran
los datos sin verificar.

**b) Se le pueden añadir reglas de seguridad, y sale casi gratis.** Ver §5.

---

## 2. VS Code y el formateo

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
por separado aparecen peleas cuando una regla no coincide. Con esta configuración
hay una sola fuente de verdad, y lo que se ve al formatear es exactamente lo que
valida `npm run lint`.

`eslint.workingDirectories` es necesario porque hay tres proyectos con
configuraciones de ESLint distintas en el mismo workspace.

**La decisión es correcta.** Y el "lo que se ve al formatear es lo que valida
`npm run lint`" es justo la propiedad que hace que meter `lint` en el CI no
genere fricción: nadie va a ver fallar el pipeline por algo que su editor daba
por bueno.

---

## 3. Versiones de Node

```
Máquina de desarrollo   Node 24 · npm 11.6.2
Dockerfile              node:20-alpine · npm 10.8.2
```

Tratado en detalle en [docker-y-npm.md](./docker-y-npm.md) §5, porque las
consecuencias caen del lado del build.

---

## 4. Errores del editor que no son errores

- **`Property 'X' does not exist`** → error real de TypeScript, el código no
  compila
- **`Unsafe call` / `Unsafe assignment`** → reglas de ESLint, suelen ser
  *consecuencia* en cascada de un error de TypeScript
- **Subrayados que persisten tras instalar dependencias** → caché del servidor de
  TypeScript. `Ctrl+Shift+P` → `TypeScript: Restart TS Server`

Regla práctica: ante muchos errores rojos, ejecutar `npx tsc --noEmit`. Suele
haber dos o tres causas reales y el resto es ruido derivado.

> Matiz sobre el segundo punto: los `Unsafe *` son a menudo cascada, pero no
> siempre. Cuando `npx tsc --noEmit` sale limpio y el `Unsafe` sigue ahí, ya no es
> ruido — es un `any` real, y conviene mirar de dónde viene. Ver §1a.

---

## 5. Reglas de seguridad en el linter

Dos plugins que se instalan en minutos y corren en el mismo `npm run lint` que
ya existe:

```bash
npm i -D eslint-plugin-security eslint-plugin-no-secrets
```

| Plugin | Qué detecta |
|---|---|
| `eslint-plugin-security` | `eval`, `child_process` con entrada variable, regex vulnerables a ReDoS, rutas de fichero construidas con datos de usuario |
| `eslint-plugin-no-secrets` | Cadenas con entropía alta — tokens y claves pegados en el código |

No sustituyen a SonarQube: son un subconjunto pequeño de sus reglas. Pero corren
**en el editor mientras se escribe**, no tres minutos después en el pipeline, y
`no-secrets` en particular ataja el problema en el momento exacto en que se pega
una clave "temporalmente" en un archivo.

Advertencia: `eslint-plugin-security` es ruidoso con los *path traversal* y
marcará cosas legítimas. Merece la pena empezar con las reglas en `warn` y subir
a `error` solo las que resulten útiles.

---

## 6. `npm run lint` en el CI

El valor de todo esto se materializa cuando el linter deja de ser opcional:

```yaml
- run: npm run lint
```

Hoy `npm run lint` existe pero **no lo ejecuta nadie de forma automática**, igual
que los 22 tests. Es una línea del workflow de
[github-actions.md](./github-actions.md).

---

## 7. Pendientes

| | Estado | Prioridad |
|---|---|---|
| `npm run lint` en el CI | No corre | Alta (va con HU-21) |
| `eslint-plugin-no-secrets` | No instalado | Baja |
| `eslint-plugin-security` | No instalado | Baja |
| SonarQube for IDE en Connected Mode | Sin configurar | Baja |
| Revisar los `Unsafe *` que sobreviven a `tsc --noEmit` | Sin hacer | Baja |
