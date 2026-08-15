# Prisma — ORM, y por qué está en una lista de seguridad

> Categoría: acceso a datos · **Veredicto: seguro por defecto, con dos escapes que hay que cerrar**
> Índice: [README.md](./README.md) · Relacionadas: [pgcrypto.md](./pgcrypto.md) · [eslint-y-vscode.md](./eslint-y-vscode.md)

---

## 1. Por qué aparece aquí

Prisma **no es una herramienta de seguridad**. Es el ORM del backend. Está en la
lista por dos motivos:

1. Su comportamiento por defecto **elimina estructuralmente la inyección SQL**.
2. Tiene dos métodos que la reintroducen por completo, y se parecen mucho a dos
   que son seguros.

Saber cuál es cuál es toda la ficha.

---

## 2. Cómo funciona, y por qué eso importa

Defines el modelo en `schema.prisma` y Prisma genera un cliente tipado. Cuando
escribes:

```ts
await prisma.parte.findMany({ where: { comisariaId: id } })
```

no se construye una cadena de SQL con el valor dentro. Se envía una consulta
**parametrizada**: la sentencia viaja por un lado y el dato por otro.

```sql
-- lo que llega a Postgres
SELECT * FROM partes WHERE comisaria_id = $1
-- parámetros: ['abc']
```

La consecuencia es la que importa: **el dato del usuario nunca puede convertirse
en sintaxis SQL.** Da igual que mande `' OR 1=1 --`; llega como una cadena y se
compara como una cadena. La inyección no es que sea difícil de explotar — no
tiene por dónde ocurrir.

Esto significa que, si el proyecto usa exclusivamente la API de Prisma, SQLi
—histórico número uno de las listas de vulnerabilidades— sencillamente no está en
el mapa. Es una propiedad muy valiosa y conviene no perderla por accidente.

---

## 3. Los cuatro métodos raw

Aquí está el todo el riesgo, y la diferencia es de una palabra:

```ts
// SEGURO — template etiquetado: Prisma parametriza ${id}
await prisma.$queryRaw`SELECT * FROM partes WHERE id = ${id}`

// VULNERABLE — cadena ya construida, va tal cual a la base
await prisma.$queryRawUnsafe(`SELECT * FROM partes WHERE id = ${id}`)
```

| Método | Seguro | Nota |
|---|---|---|
| `$queryRaw` | **Sí** | Template etiquetado, parametriza las interpolaciones |
| `$executeRaw` | **Sí** | Igual, para sentencias sin resultado |
| `$queryRawUnsafe` | **No** | Recibe una cadena ya montada |
| `$executeRawUnsafe` | **No** | Igual |

El sufijo `Unsafe` no es decorativo: es la advertencia. Y las dos líneas del
ejemplo se ven casi idénticas en una revisión de código apresurada, que es
exactamente el problema.

Existe un matiz que confunde: `$queryRaw` **solo parametriza valores**, no
identificadores. No puedes interpolar un nombre de tabla o de columna, ni un
`ORDER BY` dinámico. Cuando alguien necesita eso, es cuando recurre a
`$queryRawUnsafe` — y ahí es donde nace la vulnerabilidad. Si te hace falta
ordenar por un campo que llega del cliente, la solución es una **lista blanca**:

```ts
const columnasPermitidas = { fecha: 'fecha', estado: 'estado' } as const
const col = columnasPermitidas[input] ?? 'fecha'
```

---

## 4. Prohibirlo mecánicamente

Confiar en que nadie escriba `Unsafe` no es un control. Se prohíbe en el linter,
que ya corre en el editor y —cuando exista el CI— en el pipeline:

```js
// eslint.config.js
rules: {
  'no-restricted-syntax': ['error', {
    selector: "MemberExpression[property.name=/RawUnsafe$/]",
    message: 'Prohibido: usa $queryRaw con template etiquetado, o una lista blanca.',
  }],
}
```

A partir de ahí, usarlo exige desactivar la regla con un comentario — que es
visible en el diff y obliga a justificarlo. De "hay que acordarse" a "hay que
argumentarlo".

**Comprobación inmediata**, antes de montar nada:

```bash
grep -rn "queryRawUnsafe\|executeRawUnsafe" modulo_policia_backend/src/
```

Cualquier resultado que interpole una variable es inyección SQL hoy.

---

## 5. Lo que Prisma no protege

Que no haya SQLi no significa que la capa de datos esté resuelta. Tres cosas
quedan enteramente en tus manos:

**Autorización.** `findUnique({ where: { id } })` devuelve el registro tanto si
le corresponde al usuario como si no. Prisma no sabe quién pregunta. Esto es
BOLA, el fallo nº1 de las APIs, y se resuelve en la capa de servicio —
normalmente añadiendo el ámbito del usuario a cada `where`:

```ts
where: { id, comisariaId: usuario.comisariaId }   // no solo { id }
```

**Exposición excesiva.** Devolver la entidad entera desde un controlador publica
todas sus columnas, incluidas las que se añadieron después y nadie revisó. Se
corta con `select` explícito o con DTOs de salida, nunca devolviendo el modelo
directamente.

**Borrado y retención.** Los `delete` son reales. Para un sistema con datos de
ciudadanos, decidir entre borrado físico y lógico es una decisión de cumplimiento,
no de arquitectura.

---

## 6. Migraciones

`prisma migrate deploy` aplica migraciones pendientes y es lo que corresponde en
CI y en el arranque del contenedor. `prisma migrate dev` **no** debe correr
nunca fuera de la máquina de desarrollo: puede reiniciar la base.

Merece la pena verificar cuál está en el `Dockerfile` o en el script de arranque.

En [sonarqube-cloud.md](./sonarqube-cloud.md) quedó excluir
`prisma/migrations/**` del análisis: es SQL generado, y solo aporta ruido y
consumo de cuota.

---

## 7. Pendientes

| | Estado | Prioridad |
|---|---|---|
| `grep` de `$queryRawUnsafe` / `$executeRawUnsafe` | Sin verificar | **Alta** |
| Regla de ESLint que los prohíba | No existe | Media |
| Revisar que los servicios filtren por ámbito del usuario | Sin verificar | **Alta** |
| Revisar que no se devuelvan entidades completas | Sin verificar | Media |
| Confirmar `migrate deploy` y no `migrate dev` en el contenedor | Sin verificar | Media |
