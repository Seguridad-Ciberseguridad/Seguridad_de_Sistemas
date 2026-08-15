# Schemathesis — tests generados desde el OpenAPI

> Categoría: testing basado en propiedades / fuzzing de API · **Veredicto: viable, el mejor rendimiento por esfuerzo**
> Índice: [README.md](./README.md) · Relacionadas: [spectral.md](./spectral.md) · [owasp-zap.md](./owasp-zap.md)

---

## 1. Qué hace

Lee el OpenAPI y **genera cientos de peticiones por endpoint** sin que escribas
un solo test. Después comprueba que la aplicación responde de acuerdo con su
propio contrato.

No busca vulnerabilidades conocidas como ZAP. Busca **desacuerdos entre lo que la
API promete y lo que hace**, que es donde viven los fallos que nadie previó.

---

## 2. Cómo funciona

Está construido sobre Hypothesis, la librería de *property-based testing* de
Python. El mecanismo tiene tres partes:

**1. Generación.** Del esquema de cada operación deduce qué entradas son válidas
y genera valores que lo cumplen, sesgando hacia los casos límite: cadenas vacías,
unicode raro, números en los bordes del rango, arrays vacíos, campos opcionales
ausentes, nulls donde el tipo lo permite.

**2. Comprobación.** Cada respuesta pasa por una batería de *checks*:

| Check | Verifica |
|---|---|
| `not_a_server_error` | Que nunca devuelva 5xx |
| `status_code_conformance` | Que el código devuelto esté documentado |
| `response_schema_conformance` | Que el cuerpo cumpla el esquema declarado |
| `content_type_conformance` | Que el `Content-Type` sea el prometido |
| `response_headers_conformance` | Que estén las cabeceras declaradas |

**3. Reducción.** Al encontrar un fallo, no te entrega la petición monstruosa que
lo disparó: la *reduce* al caso mínimo que sigue fallando y te imprime el `curl`
exacto. Es la diferencia entre "algo falló" y un reproductor de una línea.

```bash
schemathesis run http://localhost:3000/api-json \
  --checks all \
  -H "Authorization: Bearer $TOKEN"
```

---

## 3. Por qué es seguridad y no solo calidad

Un 500 parece un problema de robustez. Casi siempre es más:

- **Filtración de información.** NestJS en modo desarrollo devuelve el stack
  trace: rutas del sistema de ficheros, versiones, nombres de tablas.
- **Validación que no llegó.** Si un `POST` con un campo raro produce 500 en vez
  de 400, ese valor alcanzó lógica que no lo esperaba. La excepción es la
  evidencia de que la validación no cubre ese camino.
- **DoS barato.** Un endpoint que revienta con una entrada concreta se puede
  llamar en bucle.

Y las violaciones de esquema tienen su propio ángulo: si la respuesta devuelve
campos que el contrato no declara, es **exposición excesiva de datos** — el
`password_hash` o el `dni` que se coló porque se serializó la entidad entera en
vez del DTO. Eso es API3 del [Top 10](./owasp-api-top-10.md).

---

## 4. Testing con estado

Además de operación por operación, sigue los `links` de OpenAPI para encadenar
llamadas: crear un recurso, usar el ID devuelto en la siguiente petición,
borrarlo.

```bash
schemathesis run ... --stateful=links
```

Aquí aparecen fallos de otra clase: recursos que siguen accesibles tras un
`DELETE`, IDs predecibles, endpoints que aceptan referencias a objetos ajenos.
Requiere que el spec declare los `links`, lo que en NestJS es trabajo manual — no
sale de los decoradores.

---

## 5. En el pipeline

**No va en cada push.** Una pasada completa contra una API mediana son entre 5 y
20 minutos, y necesita la aplicación levantada con base de datos. Va en un job
nocturno o manual:

```yaml
  fuzzing:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    services:
      postgres:
        image: postgres:16
        # ...
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npx prisma migrate deploy
      - run: npm run start:prod &
      - run: npx wait-on http://localhost:3000/health
      - run: pip install schemathesis
      - run: |
          schemathesis run http://localhost:3000/api-json \
            --checks all --hypothesis-max-examples=100 \
            -H "Authorization: Bearer ${{ secrets.TEST_JWT }}"
```

`--hypothesis-max-examples` controla el equilibrio entre cobertura y duración.
100 es un punto de partida razonable; en local se sube para investigar.

---

## 6. Expectativas

**La primera ejecución va a fallar mucho**, y una parte importante no serán
fallos reales sino contrato incompleto: DTOs sin `@ApiProperty`, respuestas de
error no declaradas, tipos mal anotados. Eso es información útil —el contrato es
la documentación de tu API— pero conviene saber que la primera sesión es de
arreglar el spec, no de arreglar la aplicación.

Igual que ZAP, necesita **autenticarse** o solo prueba la capa de 401. Y ojo con
la caducidad del JWT: una pasada de 20 minutos con un token de 15 sale a medias.

**Advertencia operativa:** genera datos. Contra una base de pruebas que se pueda
reconstruir, ningún problema. Nunca contra producción.

---

## 7. Extensión de VS Code

**No hay.** Es una herramienta de línea de comandos en Python; se ejecuta desde
la terminal integrada y su salida ya es legible ahí.

| | |
|---|---|
| Sitio | https://schemathesis.readthedocs.io |
| Repositorio | https://github.com/schemathesis/schemathesis |
| Instalación | `pip install schemathesis` |
| Action | https://github.com/schemathesis/action |

Sí conviene tener instalada la extensión de **Python**
(`ms-python.python`) si vas a ejecutarlo en local, para que VS Code gestione el
entorno virtual y no acabes instalándolo en el Python del sistema.

---

## 8. Pendientes

| | Estado |
|---|---|
| Entorno o job que levante la app con Postgres | Falta |
| Job nocturno con `schemathesis run` | Falta |
| Estrategia de token de larga duración para pruebas | Sin definir |
| Completar `@ApiProperty` en los DTOs | Sin verificar |
| `links` en el spec para testing con estado | Sin empezar |
