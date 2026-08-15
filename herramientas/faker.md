# Faker — datos de prueba sintéticos

> Categoría: protección de datos · **Veredicto: viable, y resuelve un problema abierto**
> Índice: [README.md](./README.md) · Relacionadas: [easypanel.md](./easypanel.md) · [schemathesis.md](./schemathesis.md)

---

## 1. Por qué está en una lista de seguridad

Faker es una librería de datos falsos. Parece una herramienta de comodidad, y en
la mayoría de proyectos lo es.

Aquí no, porque **sustituye a la práctica que tiene el problema abierto**: copiar
la base de producción a un entorno de desarrollo o pruebas.

La diferencia es de categoría, no de grado:

```
Base de pruebas expuesta con datos de Faker    →  un susto
Base de pruebas expuesta con datos de la EPI   →  un incidente con
                                                  obligaciones legales
```

Es exactamente la situación descrita en [easypanel.md](./easypanel.md). La
pregunta de *qué hay dentro de esa base* decide cuál de las dos líneas aplica.

---

## 2. Cómo funciona

Una librería de generadores organizados por categoría. Cada llamada devuelve un
valor verosímil del tipo pedido:

```ts
import { faker } from '@faker-js/faker/locale/es'

faker.person.fullName()        // 'Lucía Ferrer Nieto'
faker.location.streetAddress() // 'Calle de Alcalá 42'
faker.phone.number()           // '+34 612 345 678'
faker.date.recent({ days: 30 })
faker.string.numeric(8)        // '48213907'
```

El locale importa: `/locale/es` genera nombres y direcciones plausibles en
castellano en vez de `John Smith` de Ohio. Para datos peruanos no hay locale
específico completo, así que los identificadores tipo DNI se generan con
`faker.string.numeric(8)` y las jurisdicciones con `faker.helpers.arrayElement()`
sobre una lista propia.

---

## 3. El `seed` es lo que lo hace utilizable en CI

```ts
faker.seed(42)
```

Fija la secuencia: la misma semilla produce exactamente los mismos datos en cada
ejecución. Sin esto, cada pasada de tests trabaja sobre datos distintos y un
fallo intermitente es imposible de reproducir.

Con semilla fija, los tests son deterministas y un fallo en CI se reproduce en
local ejecutando lo mismo. Es la diferencia entre una suite en la que se confía y
una que "a veces falla".

---

## 4. El script de seed

El patrón habitual es un script que puebla la base desde cero, y que se puede
ejecutar tantas veces como haga falta:

```ts
// prisma/seed.ts
import { PrismaClient } from '@prisma/client'
import { faker } from '@faker-js/faker/locale/es'

const prisma = new PrismaClient()
faker.seed(42)

async function main() {
  const comisarias = await Promise.all(
    ['Centro', 'Norte', 'Sur'].map((nombre) =>
      prisma.comisaria.create({ data: { nombre } }),
    ),
  )

  for (const comisaria of comisarias) {
    await prisma.parte.createMany({
      data: Array.from({ length: 50 }, () => ({
        comisariaId:  comisaria.id,
        denunciante:  faker.person.fullName(),
        documento:    faker.string.numeric(8),
        direccion:    faker.location.streetAddress(),
        descripcion:  faker.lorem.paragraph(),
        fecha:        faker.date.recent({ days: 90 }),
      })),
    })
  }
}

main().finally(() => prisma.$disconnect())
```

```json
// package.json
"prisma": { "seed": "ts-node prisma/seed.ts" }
```

`npx prisma db seed` lo ejecuta. Y con eso el entorno de pruebas se reconstruye
en segundos desde cero — que es además el requisito que
[schemathesis.md](./schemathesis.md) y [owasp-zap.md](./owasp-zap.md) daban por
bloqueante: ninguna de las dos se puede ejecutar contra datos que no se puedan
tirar y regenerar.

---

## 5. Generar datos que sirvan para probar

Un detalle que marca la diferencia entre un seed decorativo y uno útil: **generar
los casos límite a propósito**, no solo filas bonitas.

```ts
const nombres = [
  faker.person.fullName(),
  "O'Brien-Núñez",                    // apóstrofe y guion
  'José María de la Cruz Ñañez',      // tildes, eñe, nombre largo
  'X Æ A-12',                         // caracteres inesperados
  'a'.repeat(255),                    // límite de longitud
]
```

Si el parser del Excel o el generador de PDF se rompe con un apóstrofe, mejor
descubrirlo en el seed que con un parte real. Y esos mismos valores son los que
un atacante prueba primero.

---

## 6. Lo que no resuelve

Faker genera datos plausibles, no datos **representativos**. Dos limitaciones que
conviene tener presentes:

- **Los volúmenes y las distribuciones son artificiales.** Si en producción el
  90% de los partes son de un tipo, el seed no lo refleja salvo que se programe.
  Un problema de rendimiento que solo aparece con datos reales no se detecta así.
- **No es anonimización.** Son dos cosas distintas: anonimizar es transformar
  datos reales para que no identifiquen a nadie —y hacerlo bien es difícil, la
  reidentificación cruzando campos es un problema conocido—. Faker no anonimiza:
  **inventa**. Que es justamente por lo que es más seguro.

Cuando alguien pide "datos reales pero anonimizados" para pruebas, casi siempre
lo correcto es responder con datos generados. Sale mejor y no arrastra riesgo
legal.

---

## 7. Extensión de VS Code

**No hay, ni hace falta.** Es una librería npm: el autocompletado sale del
tipado de TypeScript, que ya funciona en cuanto la instalas como devDependency.

| | |
|---|---|
| Sitio | https://fakerjs.dev |
| Referencia de la API | https://fakerjs.dev/api/ |
| Repositorio | https://github.com/faker-js/faker |
| Instalación | `npm i -D @faker-js/faker` |

La referencia de la API es la página que vas a tener abierta mientras escribes el
seed: lista todos los generadores por categoría con ejemplos de salida.

> Cuidado con el paquete: el correcto es **`@faker-js/faker`**. El antiguo
> `faker` (sin ámbito) quedó abandonado tras el incidente de 2022 en que su autor
> saboteó sus propios paquetes, y sigue en npm. Es, de paso, un ejemplo de
> manual de lo que documenta [docker-y-npm.md](./docker-y-npm.md) sobre riesgo de
> cadena de suministro.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Auditar qué datos hay en la base de pruebas actual | Sin hacer | **Crítica** |
| `@faker-js/faker` como devDependency | Sin verificar | Alta |
| `prisma/seed.ts` con semilla fija | Sin escribir | Alta |
| Casos límite deliberados en el seed | Sin escribir | Media |
| Purgar y regenerar la base de pruebas | Pendiente | **Alta** |
