# pgcrypto — cifrado de columnas en PostgreSQL

> Categoría: protección de datos en reposo · **Veredicto: viable, pero no es la primera medida que toca**
> Índice: [README.md](./README.md) · Relacionadas: [easypanel.md](./easypanel.md) · [prisma.md](./prisma.md)

---

## 1. Qué hace

Es una extensión de PostgreSQL que añade funciones criptográficas al SQL: cifrar
y descifrar valores, generar hashes y HMAC. Sirve para que **columnas concretas
no estén en claro dentro de la base**, de modo que un volcado filtrado no revele
los datos sensibles.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## 2. Cómo funciona

Las funciones que importan son las de cifrado simétrico con PGP:

```sql
-- cifrar al insertar
INSERT INTO ciudadanos (nombre, dni_cifrado)
VALUES ('Ana Quispe', pgp_sym_encrypt('12345678', 'clave-maestra'));

-- descifrar al leer
SELECT nombre, pgp_sym_decrypt(dni_cifrado, 'clave-maestra') AS dni
FROM ciudadanos;
```

La columna se declara como `bytea`. Quien lea la tabla sin la clave ve bytes.

También trae `digest()` y `hmac()` para hashes, y `crypt()` con `gen_salt('bf')`
para contraseñas. **Para contraseñas no lo uses**: el sitio correcto es la capa de
aplicación con argon2. Hashear en la base implica que la contraseña en claro
viaja en la consulta y acaba en los logs de Postgres.

---

## 3. Contra qué protege, y contra qué no

Esta tabla es la ficha entera. pgcrypto se vende mal y conviene tenerlo claro
antes de invertir trabajo:

| Protege contra | **No** protege contra |
|---|---|
| Backup robado o filtrado | Aplicación comprometida |
| Disco o VPS robado | Alguien con acceso a la app *y* a la base |
| Volcado `pg_dump` que acaba donde no debe | Un `SELECT` desde la propia aplicación |
| Copia de la base en un entorno de pruebas | Logs de consultas con la clave dentro |

El razonamiento es simple: **la aplicación necesita la clave para descifrar.**
Quien comprometa la aplicación tiene la clave. Y si la clave viaja como literal
en la consulta, queda registrada en `pg_stat_activity` y, con `log_statement`
activo, en los logs en texto plano.

Por eso muchos equipos cifran en la capa de aplicación, donde Postgres nunca ve
la clave y esta vive en la configuración del proceso. Con pgcrypto, la clave pasa
por la base sí o sí.

---

## 4. Lo que cuesta

No es gratis, y el coste cae sobre el modelo de datos:

- **No puedes indexar la columna.** `WHERE dni = '12345678'` deja de funcionar:
  cada fila cifra distinto, así que no hay igualdad que comparar. Para buscar hay
  que descifrar toda la tabla, o guardar aparte un HMAC del valor y buscar por él.
- **No hay ordenación ni rangos.** `ORDER BY`, `LIKE`, `BETWEEN`: fuera.
- **Prisma no lo maneja.** Necesitas `$queryRaw` en cada acceso a esas columnas,
  perdiendo el tipado. Ver [prisma.md](./prisma.md).
- **Rotar la clave es re-cifrar toda la tabla.**

Traducción: solo es viable para columnas que se **guardan y se leen por ID**,
nunca para columnas por las que se busca o se filtra.

---

## 5. Mi recomendación para este proyecto

**No es la primera medida, ni la segunda.** Por orden de rendimiento real:

```
1. Cerrar el puerto público de Postgres        ← elimina el vector principal
2. Cifrado de disco del VPS                    ← cubre robo de disco, coste cero
3. Backups cifrados fuera del servidor         ← cubre backup filtrado
4. pgcrypto en dos o tres columnas concretas   ← solo entonces
```

Los pasos 1 a 3 protegen contra lo mismo que pgcrypto, con menos trabajo y sin
romper el modelo de datos. Cifrar columnas mientras la base sigue expuesta a
internet es poner una caja fuerte con la puerta de la casa abierta.

**Cuándo sí cobra sentido el paso 4:** cuando el sistema maneje datos reales de
ciudadanos y aparezca un requisito explícito de cifrado en reposo a nivel de
campo — plausible si la **Ley 29733** entra en el alcance. Ahí la columna
candidata es el identificador del ciudadano, no la tabla entera.

---

## 6. Si se implementa

Dos decisiones que hay que tomar antes de escribir nada:

**Dónde vive la clave.** No en la base, no en el código, no en el repositorio.
Variable de entorno de EasyPanel, igual que el resto de secretos. Y hay que
asumir que si alguien entra en el panel, tiene la clave.

**Cómo se busca.** Si hay que buscar por el valor cifrado, el patrón habitual es
guardar dos columnas: el valor cifrado (`pgp_sym_encrypt`) y un HMAC determinista
del mismo valor, indexable, sobre el que se hace la igualdad. Añade complejidad
real, y conviene decidirlo al principio y no después.

---

## 7. Extensión de VS Code

pgcrypto es una extensión **de PostgreSQL**, no de VS Code — no tiene una propia.
Lo que sí ayuda es un cliente de base de datos integrado para ejecutar el
`CREATE EXTENSION` y comprobar el contenido de las columnas cifradas:

| Extensión | ID | Nota |
|---|---|---|
| **PostgreSQL** (Microsoft) | `ms-ossdata.vscode-pgsql` | https://marketplace.visualstudio.com/items?itemName=ms-ossdata.vscode-pgsql |
| **PostgreSQL** (Chris Kolkman) | `ckolkman.vscode-postgres` | Alternativa veterana, más ligera |

| | |
|---|---|
| Documentación de pgcrypto | https://www.postgresql.org/docs/current/pgcrypto.html |

> **Aviso que conecta con la sección 3.** Si te conectas a la base desde el
> editor para probar `pgp_sym_decrypt`, la clave queda escrita en el historial de
> consultas de la extensión y, del lado del servidor, en los logs de Postgres. Es
> exactamente la fuga que describe la tabla de esa sección. Para pruebas usa una
> clave desechable, nunca la de producción.
>
> Y mientras el puerto de Postgres siga abierto a internet, conectarse desde el
> editor funciona precisamente por el motivo equivocado. Cuando esté cerrado
> —que es lo primero de la lista— harán falta un túnel SSH y la extensión
> `ms-vscode-remote.remote-ssh`.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Cerrar el puerto público de Postgres | Abierto | **Crítica** |
| Verificar cifrado de disco del VPS | Sin verificar | Media |
| Backups cifrados y externos | No existen | Media |
| Decidir si aplica cifrado a nivel de campo | Sin decidir | Baja |
| Confirmar que las contraseñas usan argon2 y no `crypt()` | Sin verificar | Media |
