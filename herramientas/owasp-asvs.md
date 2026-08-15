# OWASP ASVS — estándar de verificación

> Categoría: marco de referencia · **Veredicto: es el que dice cuándo has terminado**
> Índice: [README.md](./README.md) · Relacionadas: [owasp-api-top-10.md](./owasp-api-top-10.md)

---

## 1. Qué problema resuelve

"¿Estamos seguros?" no tiene respuesta. No es una pregunta mal formulada por
descuido: es que no existe un estado de "seguro" que se pueda comprobar.

ASVS —*Application Security Verification Standard*— convierte esa pregunta en
otra que sí tiene respuesta: **"¿cumplimos estos 280 requisitos concretos?"**.
Cada uno se responde sí, no, o no aplica.

Ese cambio es todo el valor. Sin un estándar, la cobertura de seguridad de un
proyecto es la que casualmente tengan las herramientas que alguien instaló. Con
ASVS, sabes qué has verificado y —más importante— **qué no**.

---

## 2. Cómo está construido

Un catálogo de requisitos organizados en capítulos temáticos:

| | Capítulo |
|---|---|
| V1 | Arquitectura y diseño |
| V2 | Autenticación |
| V3 | Gestión de sesión |
| V4 | Control de acceso |
| V5 | Validación, saneamiento y codificación |
| V6 | Criptografía |
| V7 | Manejo de errores y registro |
| V8 | Protección de datos |
| V9 | Comunicaciones |
| V11 | Lógica de negocio |
| V12 | Ficheros y recursos |
| V13 | API y servicios web |
| V14 | Configuración |

Lo que distingue a ASVS de una guía de buenas prácticas es la **redacción**. Cada
requisito está escrito para poder comprobarse, no como principio general:

> No: *"las contraseñas deben almacenarse de forma segura"*
>
> Sí: *"Verificar que las contraseñas se almacenan con una función de derivación
> de clave resistente a ataques offline, con un factor de trabajo suficiente."*

La primera no se puede auditar. La segunda se mira el código y se responde.

---

## 3. Los tres niveles

| Nivel | Para qué | Aproximado |
|---|---|---|
| **L1** | Mínimo. Verificable desde fuera, sin acceso al código | ~130 requisitos |
| **L2** | Aplicaciones que manejan datos sensibles | ~270 requisitos |
| **L3** | Sistemas críticos: banca, sanidad, defensa | ~290 requisitos |

**Para el módulo policial, L2.** Es el nivel que corresponde a un sistema con
datos personales de ciudadanos. L1 se queda corto —no exige control de acceso a
nivel de objeto con la profundidad necesaria— y L3 pide cosas como resistencia a
adversarios con recursos estatales, que no es el modelo de amenazas de aquí.

Elegir el nivel es una decisión de proyecto y conviene dejarla escrita. Es lo
primero que pregunta cualquiera que audite después.

---

## 4. Cómo se usa en la práctica

Se descarga como hoja de cálculo desde el repositorio del proyecto en GitHub.
Después:

```
1. Fijar el nivel objetivo             → L2
2. Recorrer los requisitos del nivel   → cumple / no cumple / no aplica
3. Anotar la evidencia                 → "guard global en app.module.ts:24"
4. Los "no cumple" pasan al backlog    → una historia por requisito
5. Revisar cada cierto tiempo          → por hitos, no por calendario
```

El paso 3 es el que la gente se salta y el que da todo el valor. Un "cumple" sin
evidencia es una opinión; con la referencia al fichero y la línea, es
verificable por otra persona seis meses después.

Y hay un efecto secundario útil: **los requisitos incumplidos son historias de
usuario ya redactadas.** No hay que traducir nada, el requisito ya está escrito
en términos de comportamiento comprobable.

---

## 5. Cómo se relaciona con lo demás

ASVS no reemplaza herramientas. Las ordena:

```
Top 10 API   qué te va a pasar         →  priorizar
ASVS         qué tienes que verificar  →  saber cuándo has acabado
Herramientas cómo lo verificas         →  automatizar parte del ASVS
```

Buena parte de los requisitos se pueden mapear a algo que ya tienes documentado:

| Capítulo ASVS | Qué lo cubre aquí |
|---|---|
| V2 Autenticación | argon2, guard global de JWT |
| V4 Control de acceso | CASL, pruebas manuales con [Burp](./burp-suite.md) |
| V5 Validación | `ValidationPipe` con `whitelist`, [Schemathesis](./schemathesis.md) |
| V7 Registro | Tabla de auditoría *append-only* |
| V8 Protección de datos | [pgcrypto](./pgcrypto.md), [Faker](./faker.md) en pruebas |
| V13 API | [Spectral](./spectral.md), [ZAP](./owasp-zap.md) |
| V14 Configuración | [Gitleaks](./gitleaks.md), Dependabot, Trivy |

Pero **la mayoría de los requisitos no los automatiza nada**. Se verifican leyendo
código y probando a mano. Ese es el mensaje incómodo de ASVS, y también el
honesto: las herramientas cubren una fracción, y sin un estándar no sabrías cuál.

---

## 6. Cómo no fracasar en el intento

Recorrer 270 requisitos de golpe no lo termina nadie. Lo que funciona:

- **Empezar por los capítulos donde ya sabes que hay deuda.** V4 (control de
  acceso) y V7 (registro) son, por lo visto en el resto de fichas, los que más
  van a doler aquí. Empieza donde vas a encontrar cosas.
- **Una sesión por capítulo**, no un maratón.
- **"No aplica" es una respuesta legítima**, pero se justifica en una línea. Sin
  justificación, es un "no cumple" disfrazado.
- **No aspirar al 100%.** El objetivo es saber dónde estás, no aprobar un examen.
  Un ASVS honesto con 40 incumplimientos documentados vale mucho más que uno
  verde y falso.

---

## 7. Nota sobre versiones

ASVS se revisa periódicamente y la numeración de los requisitos cambia entre
versiones mayores. Conviene **fijar la versión que se está usando** en el propio
documento de verificación, o dentro de un año nadie sabrá a qué requisito se
refería el "V4.1.3" de la hoja. Se descarga del repositorio oficial de OWASP en
GitHub, donde está la versión vigente.

---

## 8. Pendientes

| | Estado |
|---|---|
| Decidir y dejar escrito el nivel objetivo (L2) | Sin hacer |
| Descargar la hoja de verificación y fijar versión | Sin hacer |
| Primera pasada por V4 (control de acceso) | Sin hacer |
| Primera pasada por V7 (registro y auditoría) | Sin hacer |
| Convertir los incumplimientos en historias del backlog | Sin hacer |
