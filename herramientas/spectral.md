# Spectral — lint del contrato OpenAPI

> Categoría: análisis estático de la especificación · **Veredicto: viable, alto valor por bajo coste**
> Índice: [README.md](./README.md) · Relacionadas: [schemathesis.md](./schemathesis.md) · [owasp-api-top-10.md](./owasp-api-top-10.md)

---

## 1. Qué hace

Lintea el **contrato** de la API —el documento OpenAPI que `@nestjs/swagger` ya
genera— buscando fallos de diseño antes de que existan como código.

Es el equivalente de ESLint, pero aplicado al `openapi.json` en vez de al
TypeScript. Y como el contrato se genera desde los decoradores de NestJS, un
hallazgo de Spectral apunta siempre a un decorador que falta o está mal puesto.

---

## 2. Cómo funciona

Un ruleset en YAML. Cada regla tiene dos partes: `given`, una expresión JSONPath
que selecciona nodos del documento, y `then`, la función que los evalúa.

```yaml
# .spectral.yaml
extends:
  - "spectral:oas"                        # reglas base de OpenAPI
  - "@stoplight/spectral-owasp-ruleset"   # reglas de seguridad

rules:
  operation-security-defined: error
  owasp:api2:2023-no-api-keys-in-url: error
  owasp:api4:2023-rate-limit: warn
```

```bash
npx @stoplight/spectral-cli lint openapi.json
```

Sale con código distinto de cero si hay violaciones de severidad `error`, así que
sirve directamente como puerta de CI.

---

## 3. Qué detecta

| Hallazgo | Qué significa en NestJS |
|---|---|
| Operación sin esquema de seguridad | Falta `@ApiBearerAuth()` — o falta el guard de verdad |
| Sin respuesta `401` documentada | El endpoint no contempla el caso no autenticado |
| Sin respuesta `429` | No hay rate limiting declarado |
| `additionalProperties` no está en `false` | El DTO acepta campos no declarados → *mass assignment* |
| Array sin `maxItems` | Un `POST` con 100.000 elementos es un DoS barato |
| Parámetro sin `maxLength` | Entrada sin acotar |
| API key en query string | Queda en logs, en el historial y en el `Referer` |

Las tres primeras filas son las que más rendimiento dan aquí: un endpoint que no
documenta `401` casi siempre es un endpoint que no comprueba nada.

---

## 4. El límite, y es importante

**Spectral lee el documento, no la aplicación.** Verifica el diseño, no la
implementación.

Si el spec declara que `/partes/{id}` exige bearer token y el controlador se
olvidó del guard, Spectral dice que todo está bien. La comprobación es de
coherencia interna del contrato, nada más.

Por eso no sustituye a nada: se combina.

```
Spectral       ¿el contrato está bien diseñado?
Schemathesis   ¿la implementación cumple el contrato?
ZAP            ¿la aplicación resiste un ataque?
```

Un corolario práctico: **cuanto mejor documentes con los decoradores de NestJS,
más encuentra Spectral.** Si los DTOs no llevan `@ApiProperty`, el spec sale
vacío y el lint pasa por no tener nada que mirar. Un informe limpio sobre un
contrato pobre no significa nada.

---

## 5. En el pipeline

Necesita el `openapi.json`, y NestJS lo genera en tiempo de ejecución. Hay dos
caminos, y el bueno es el primero:

**Generarlo sin levantar el servidor**, con un script que construya la aplicación
en memoria y vuelque el documento:

```ts
// scripts/generate-openapi.ts
const app = await NestFactory.create(AppModule, { logger: false })
const doc = SwaggerModule.createDocument(app, config)
writeFileSync('openapi.json', JSON.stringify(doc, null, 2))
await app.close()
```

```yaml
- run: npx ts-node scripts/generate-openapi.ts
- run: npx @stoplight/spectral-cli lint openapi.json
```

Rápido y determinista: no hace falta base de datos ni puerto. Es de los pocos
controles de seguridad que corren en segundos y pueden ir en cada push sin
molestar a nadie.

**Extra que sale gratis:** commitear el `openapi.json` generado hace que los
cambios de contrato aparezcan en el diff del PR. Un endpoint que deja de exigir
autenticación se convierte en una línea roja que alguien ve al revisar.

---

## 6. Montaje

```bash
npm i -D @stoplight/spectral-cli @stoplight/spectral-owasp-ruleset
```

Recomendación de arranque: todo el ruleset OWASP en `warn`, y subir a `error`
solo las reglas que resulten accionables. Al revés —todo en `error` desde el
primer día— el equipo desactiva el paso en una semana.

---

## 7. Extensión de VS Code

| | |
|---|---|
| Extensión | **Spectral** |
| ID | `stoplight.spectral` |
| Marketplace | https://marketplace.visualstudio.com/items?itemName=stoplight.spectral |
| Sitio | https://stoplight.io/open-source/spectral |
| Documentación | https://docs.stoplight.io/docs/spectral |

Marca las violaciones directamente sobre el `openapi.json` mientras lo tienes
abierto. No hay cuenta ni token: se "conecta" a un ruleset local.

```json
// .vscode/settings.json
"spectral.rulesetFile": ".spectral.yaml",
"spectral.validateFiles": ["**/openapi.json", "**/openapi.yaml"]
```

Sin `.spectral.yaml` la extensión aplica solo las reglas base de OpenAPI y no las
de seguridad — es decir, no hace lo que te interesa. Instálala **después** de
tener el ruleset y el documento generado, o parecerá que no funciona.

**Alternativa complementaria:** `42Crunch.vscode-openapi`
(https://marketplace.visualstudio.com/items?itemName=42Crunch.vscode-openapi)
audita el OpenAPI con una puntuación de seguridad y una vista más visual. Se
solapa con Spectral; conviene una de las dos, no las dos marcando lo mismo.

---

## 8. Pendientes

| | Estado |
|---|---|
| Script de generación del `openapi.json` | Falta |
| `.spectral.yaml` con el ruleset OWASP | Falta |
| Paso en el workflow de CI | Falta |
| Revisar cobertura de `@ApiProperty` en los DTOs | Sin verificar |
| Commitear el `openapi.json` para ver cambios en el diff | Sin decidir |
