# OWASP API Security Top 10 — priorización

> Categoría: marco de referencia · **Veredicto: es el que dice por dónde empezar**
> Índice: [README.md](./README.md) · Relacionadas: [owasp-asvs.md](./owasp-asvs.md) · [burp-suite.md](./burp-suite.md)

---

## 1. Qué es

La lista de los diez riesgos que con más frecuencia y más impacto aparecen en
APIs reales. Es un documento de concienciación y priorización — **no** un
checklist que se verifica punto por punto. Eso es trabajo de
[ASVS](./owasp-asvs.md).

Es **distinto del Top 10 web clásico**, y la distinción no es burocrática: las
APIs fallan de otra forma. En una web tradicional el problema típico es la
inyección o el XSS. En una API son la **autorización** y los **límites**, porque
el cliente no es un navegador que renderiza lo que le mandas: es cualquiera con
`curl` y el endpoint.

---

## 2. La lista

| | Riesgo | Qué significaría aquí |
|---|---|---|
| **API1** | **Broken Object Level Authorization (BOLA)** | Cambiar el ID en `/partes/123` y leer el parte de otra comisaría |
| **API2** | Autenticación rota | Guard olvidado, JWT sin verificar firma o expiración, refresh eterno |
| **API3** | Autorización a nivel de propiedad | Mandar `{"rol":"admin"}` de más y que se escriba. O devolver la entidad entera con el `password_hash` |
| **API4** | Consumo sin restricciones | Login sin rate limit, `POST` con array de 100.000 elementos, paginación sin tope |
| **API5** | Autorización a nivel de función | Un usuario normal llamando a `/admin/usuarios` |
| **API6** | Acceso sin restricción a flujos sensibles | Automatizar la consulta masiva de ciudadanos |
| **API7** | SSRF | Un endpoint que descarga una URL que le pasa el cliente |
| **API8** | Mala configuración | CORS abierto, stack traces al cliente, cabeceras ausentes |
| **API9** | Inventario mal gestionado | Un `/api/v1` viejo que sigue publicado y sin mantener |
| **API10** | Consumo inseguro de APIs de terceros | Confiar en la respuesta de un servicio externo sin validarla |

---

## 3. El que domina todos los demás

**API1 es el nº1 por frecuencia, por impacto, y por una tercera razón que no
suele decirse: ninguna herramienta automática lo encuentra.**

El motivo es estructural, no una limitación temporal de las herramientas. Ante
`GET /partes/123` con el token de un usuario que no debería verlo, la respuesta
es un **200 correctamente formado**:

- ZAP ve un 200. Correcto.
- Schemathesis ve un 200 que cumple el esquema. Correcto.
- SonarQube ve código que compila y no concatena SQL. Correcto.
- Spectral ve una operación con seguridad declarada. Correcto.

**Todas tienen razón.** El fallo no está en la forma de la respuesta, está en que
ese dato no le correspondía a esa persona — y eso solo lo sabe quien conozca las
reglas del negocio.

De ahí dos consecuencias que atraviesan el resto de las fichas:

1. Se prueba **a mano**, con [Burp](./burp-suite.md), y el procedimiento está
   escrito ahí.
2. Se previene **por diseño**, filtrando siempre por el ámbito del usuario en la
   consulta —no solo por el ID— y centralizando la política con CASL en vez de
   repartir `if` por los controladores.

En un sistema policial, además, API1 no describe a un atacante externo. Describe
el **abuso interno**: alguien con credenciales legítimas consultando el
expediente de un conocido. Es el escenario más probable de todos, y sin registro
de auditoría no es ni detectable ni demostrable.

---

## 4. Cómo se usa

No se "cumple" el Top 10. Se usa para **ordenar el trabajo** cuando hay más cosas
que hacer que tiempo:

```
1. Leer la lista con tu sistema en la cabeza
2. Marcar los que aplican de verdad          → aquí: API1, API2, API3, API4, API5
3. Para cada uno, decidir prevención y verificación
4. Lo que quede sin verificación, es riesgo aceptado — escríbelo
```

Aplicado a este proyecto, la asignación queda así:

| | Se previene con | Se verifica con |
|---|---|---|
| API1 | Filtrar por ámbito + CASL | Burp, manual |
| API2 | Guard global + `@Public()` | Spectral, ZAP |
| API3 | `whitelist: true` + DTOs de salida | Schemathesis, Spectral |
| API4 | `@nestjs/throttler` + `maxItems` | Spectral, ZAP |
| API5 | CASL con roles | Burp, manual |
| API8 | helmet + CORS explícito | ZAP |
| API9 | Inventario de endpoints publicados | Revisión del OpenAPI |

Las dos filas con "manual" en la columna derecha son las que más pesan. No es
casualidad, y es el argumento de por qué Burp está en la lista pese a no ser
automatizable.

---

## 5. Los que aquí no aplican

Vale la pena decirlo explícitamente, porque descartar con criterio también es
trabajo:

- **API7 (SSRF)** — solo aplica si algún endpoint acepta una URL del cliente y la
  descarga. Merece una comprobación rápida; si no existe ese patrón, se descarta.
- **API10** — aplica si el backend consume APIs externas. Habría que confirmarlo.

---

## 6. Relación con ASVS

Se usan juntos y responden a preguntas distintas:

```
Top 10 API   ¿por dónde empiezo?     →  10 riesgos, priorizados
ASVS         ¿cuándo he terminado?   →  ~270 requisitos, verificables
```

El Top 10 se lee en media hora y cambia inmediatamente en qué trabajas primero.
ASVS se recorre en semanas y te dice qué te falta. Empezar por el Top 10 y pasar
después a ASVS es el orden natural.

---

## 7. Dónde está

Es un documento, no una herramienta: no hay extensión.

| | |
|---|---|
| Página del proyecto | https://owasp.org/API-Security/ |
| Edición vigente | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ |
| Repositorio | https://github.com/OWASP/API-Security |

Hay traducción al castellano en el repositorio. Se lee entero en media hora, y es
la media hora con mejor retorno de todo lo documentado en esta carpeta.

---

## 8. Pendientes

| | Estado |
|---|---|
| Leer la lista con el sistema delante | Sin hacer |
| Confirmar cuáles aplican y cuáles no, por escrito | Sin hacer |
| Sesión manual de BOLA (API1) sobre partes | Sin hacer |
| Sesión manual de escalada vertical (API5) | Sin hacer |
| Comprobar si existe algún endpoint que descargue URLs (API7) | Sin verificar |
| Inventariar endpoints publicados y versiones vivas (API9) | Sin hacer |
