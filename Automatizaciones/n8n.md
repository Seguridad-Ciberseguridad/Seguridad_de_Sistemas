# n8n — automatización alrededor del pipeline

> Categoría: orquestación y notificación · **Veredicto: viable como complemento, no como CI/CD**
> Índice: [README.md](./README.md) · Relacionadas: [github-actions.md](./github-actions.md) · [easypanel.md](./easypanel.md)

---

## 1. El límite: qué hace n8n aquí y qué no

Técnicamente n8n puede construir, testear y desplegar: tiene nodo Webhook,
Execute Command, SSH y HTTP Request. **No debe hacerlo**, por cinco razones y una
que pesa más que las otras cuatro juntas:

| | Motivo |
|---|---|
| **1** | **El nodo Execute Command corre en el host de n8n, no en un contenedor efímero.** Quien alcance el webhook ejecuta comandos en tu servidor de automatización — que además guarda las credenciales de todo lo demás conectado. Actions te da un runner limpio que se destruye al terminar |
| 2 | Sin *checks* en Pull Requests: no puede bloquear un merge, que es el objetivo de HU-21 |
| 3 | Sin aislamiento, el estado se filtra entre ejecuciones |
| 4 | Sin caché, sin matriz, sin artefactos |
| 5 | Los logs de ejecución no sirven para leer la salida de 22 tests |

El reparto correcto:

```
GitHub Actions   construir, testear, escanear, desplegar    ← el pipeline
n8n              agregar, avisar, vigilar, escalar          ← alrededor
```

En la capa de arriba n8n es **mejor** herramienta que Actions, no peor: agregar
tres APIs con formatos distintos, mantener estado entre ejecuciones y escalar a
personas es exactamente para lo que está hecha.

---

## 2. Los seis workflows

| | Workflow | Patrón | Valor | ¿Bloqueado hoy? |
|---|---|---|---|---|
| 1 | [Monitor de salud](#3-monitor-de-salud-del-despliegue) | Scheduled | Medio | Casi no — falta `/health` |
| 2 | [Caducidad de certificados](#4-caducidad-de-certificados-y-credenciales) | Scheduled | Medio | **No** |
| 3 | [Cambios en la superficie de la API](#5-cambios-en-la-superficie-de-la-api) | Scheduled | Alto | No, si se genera el `openapi.json` |
| 4 | [Watchdog del backup](#6-watchdog-del-backup) | Scheduled | Alto | Sí — no hay backups |
| 5 | [Digest semanal de seguridad](#7-digest-semanal-de-seguridad) | Scheduled | Alto | Sí — Sonar y Snyk no corren |
| 6 | [Alerta enriquecida de fallo de CI](#8-alerta-enriquecida-de-fallo-de-ci) | Webhook | Medio | Sí — no hay CI |

Están ordenados por **qué se puede montar hoy**, no por valor. Los tres de más
abajo dependen de cosas que no son de n8n.

> **No incluido: vigilancia del log de auditoría.** Detectaría el abuso interno
> —un usuario legítimo consultando expedientes que no le corresponden—, que es el
> escenario más probable en un sistema policial y el que no cubre ninguna
> herramienta de esta carpeta. Queda fuera porque la tabla de auditoría no
> existe. Merece volver a mirarlo cuando exista.

---

## 3. Monitor de salud del despliegue

**Objetivo.** Enterarse de que la aplicación se ha caído **antes** que el usuario
que llama por teléfono. Hoy, según [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md)
§1, *"el equipo se entera cuando la aplicación se cae"*.

| Herramientas | |
|---|---|
| Nodos n8n | Schedule Trigger · HTTP Request · IF · Code · Telegram |
| Servicios | El propio backend · un bot de Telegram (o Gmail) |
| Credenciales | Token del bot de Telegram |
| Requiere en el proyecto | Un endpoint `/health` — `@nestjs/terminus` |

```
Schedule Trigger (cada 5 min)
   │
   ▼
HTTP Request  GET https://.../health
              On Error: Continue          ← imprescindible
              Timeout: 10s
   │
   ▼
IF   ¿error, status ≠ 200, o tiempo > 3s?
   │
   ├─ sí →  Code: ¿es el 2º fallo consecutivo? →  Telegram 🔴 caído
   └─ no →  Code: ¿veníamos de un fallo?       →  Telegram 🟢 recuperado
```

**Detalles críticos:**

- **`On Error: Continue` en el nodo HTTP.** Sin esto, cuando la app se cae el
  nodo lanza error y el workflow muere *antes* de avisarte. Es el fallo más común
  de este patrón, y especialmente irónico.
- **Umbral de 2 o 3 fallos consecutivos** antes de alertar. Con umbral 1 llegan
  avisos por cada microcorte y en dos semanas están silenciados. El contador vive
  en `$getWorkflowStaticData('global')`.
- **Avisar también de la recuperación.** Sin eso no sabes si sigue caído.
- Con `@nestjs/terminus` el `/health` comprueba además la conexión a Postgres, así
  que detecta "la app responde pero la base no" — que es la caída silenciosa.

**Es el que hay que montar primero:** media hora, sin dependencias reales, y te
enseña n8n para los demás.

---

## 4. Caducidad de certificados y credenciales

**Objetivo.** Evitar la caída tonta de un domingo. Let's Encrypt renueva solo,
hasta el día que falla; y los tokens de CI caducan sin avisar.

| Herramientas | |
|---|---|
| Nodos n8n | Schedule Trigger · Execute Command *(o HTTP Request)* · HTTP Request · Code · IF · Telegram |
| Servicios | El dominio en producción · API de GitHub · bot de Telegram |
| Credenciales | PAT de GitHub · token del bot |
| Requiere en el proyecto | Nada |

```
Schedule Trigger (semanal, lunes)
   │
   ├─→ Execute Command   openssl s_client → fecha de expiración del TLS
   └─→ HTTP Request      GitHub /user → antigüedad de los tokens
   │
   ▼
Code   días restantes de cada uno
   │
   ▼
IF   ¿alguno por debajo de 21 días?  →  Telegram recordatorio
```

**Detalles críticos:**

- **El Code node de n8n no permite `require('tls')`** salvo que el host tenga
  `NODE_FUNCTION_ALLOW_EXTERNAL` configurado. Dos alternativas: Execute Command
  con `openssl`, o un servicio HTTP de comprobación de SSL. La primera no depende
  de terceros y es la recomendada.

  ```bash
  echo | openssl s_client -servername DOMINIO -connect DOMINIO:443 2>/dev/null \
    | openssl x509 -noout -enddate
  ```

- 21 días de margen no es capricho: da tiempo a dos ciclos de renovación
  automática fallidos antes de que sea urgente.
- Si tu n8n es gestionado, Execute Command puede estar deshabilitado — por el
  mismo motivo de la sección 1. En ese caso, la vía HTTP.

**El segundo a montar:** no depende de nada y es barato.

---

## 5. Cambios en la superficie de la API

**Objetivo.** Detectar que un endpoint apareció, desapareció o **dejó de estar
protegido**, sin que nadie se diera cuenta. Es **API9 — inventario mal
gestionado** del [Top 10](./owasp-api-top-10.md), automatizado.

| Herramientas | |
|---|---|
| Nodos n8n | Schedule Trigger · HTTP Request · Code · IF · Telegram |
| Servicios | El `/api-json` del backend · bot de Telegram |
| Credenciales | Token del bot |
| Requiere en el proyecto | Que `@nestjs/swagger` exponga el OpenAPI |

```
Schedule Trigger (diario)
   │
   ▼
HTTP Request  GET /api-json
   │
   ▼
Code   comparar con la versión guardada en $getWorkflowStaticData('global')
         · endpoints nuevos
         · endpoints eliminados
         · operaciones que perdieron su security scheme      ← lo importante
         · parámetros nuevos sin validación declarada
   │
   ▼
IF → Telegram   ⚠️ POST /partes/exportar ahora responde sin autenticación
   │
   ▼
Code   guardar el estado actual como referencia
```

**Detalles críticos:**

- **La tercera comprobación es la que justifica el workflow.** Un endpoint que
  deja de exigir token es el fallo más caro que existe, y es invisible en una
  revisión de código si el cambio está en un decorador de otra clase.
- Complementa a [Spectral](./spectral.md), que valida el contrato **contra las
  reglas** pero no **contra el de ayer**. Son comprobaciones distintas.
- El estado inicial hay que sembrarlo: la primera ejecución guarda y no compara.
- Si el `openapi.json` se commitea al repositorio (recomendado en
  [spectral.md](./spectral.md) §5), este workflow es redundante con el diff del
  PR — pero sigue cubriendo el caso de un cambio que llegó a producción sin PR.

**El tercero, y el de más valor entre los no bloqueados.**

---

## 6. Watchdog del backup

**Objetivo.** Detectar el modo de fallo clásico: el backup deja de ejecutarse en
silencio y nadie se entera hasta que hace falta restaurar. Un backup de 0 bytes
pasa desapercibido durante meses.

| Herramientas | |
|---|---|
| Nodos n8n | Schedule Trigger · AWS S3 *(o HTTP Request)* · Code · IF · Telegram |
| Servicios | El almacenamiento de backups (S3, Backblaze B2, cualquier compatible) |
| Credenciales | Claves del almacenamiento · token del bot |
| Requiere en el proyecto | **Que existan backups.** Hoy no existen |

```
Schedule Trigger (diario 09:00)
   │
   ▼
AWS S3  listar objetos del bucket de backups
   │
   ▼
Code   del más reciente:
         · ¿tiene menos de 24 h?
         · ¿el tamaño está dentro del ±30% del anterior?
         · ¿hay al menos N copias retenidas?
   │
   ▼
IF → Telegram alerta
```

**Detalles críticos:**

- **La comprobación de tamaño importa tanto como la de fecha.** Un `pg_dump`
  que falla a media escritura deja un fichero reciente y truncado: pasa el
  control de fecha y no sirve para restaurar.
- El nodo **AWS S3 funciona con Backblaze B2 y otros compatibles** poniendo el
  endpoint personalizado. No hace falta AWS.
- Esto vigila que el backup *existe*. **No verifica que se pueda restaurar** —
  eso sigue siendo la prueba de restauración manual y trimestral que quedó
  pendiente en [easypanel.md](./easypanel.md) §6. Un backup no restaurado no se
  sabe si es un backup.

---

## 7. Digest semanal de seguridad

**Objetivo.** Reunir en un solo mensaje lo que hoy vive en tres paneles que nadie
abre. Es el workflow donde n8n gana claramente a Actions: tres APIs con formatos
distintos que hay que normalizar y unificar.

| Herramientas | |
|---|---|
| Nodos n8n | Schedule Trigger · HTTP Request ×3 · Merge · Code · IF · Telegram / Gmail |
| Servicios | API de SonarQube Cloud · API de Snyk · API de GitHub (Dependabot) |
| Credenciales | User Token de Sonar · token de Snyk · PAT de GitHub · bot |
| Requiere en el proyecto | Que SonarQube y Snyk **estén corriendo de verdad** |

```
Schedule Trigger (lunes 08:00)
   │
   ├─→ HTTP  SonarQube  /api/issues/search?severities=CRITICAL,MAJOR
   ├─→ HTTP  Snyk       /rest/orgs/{id}/issues
   └─→ HTTP  GitHub     /repos/{owner}/{repo}/dependabot/alerts
   │
   ▼
Merge  (mode: combine)
   │
   ▼
Code   normalizar a {fuente, severidad, título, url}
       ordenar por severidad · contar por fuente
       comparar con los IDs de la semana pasada
   │
   ▼
IF   ¿hay novedades?
   ├─ sí →  Telegram / Gmail  informe completo
   └─ no →  Telegram  "sin novedades esta semana"
```

**Detalles críticos:**

- **Mándalo aunque no haya novedades.** Un digest que solo aparece cuando hay
  problemas es indistinguible de un digest roto.
- El estado de la semana anterior va en `$getWorkflowStaticData('global')`.
- Con Actions esto acaba siendo un script de 200 líneas que nadie mantiene. Aquí
  el `Merge` más un `Code` corto lo resuelve y el flujo se lee de un vistazo.

**Bloqueado, y es el ejemplo del problema de fondo:** un digest de SonarQube
cuando SonarQube todavía no corre en el pipeline no tiene contenido. Informa
sobre controles que aún no existen.

---

## 8. Alerta enriquecida de fallo de CI

**Objetivo.** Convertir el *"workflow failed"* de GitHub en un mensaje que diga
qué test falló y en qué archivo. La diferencia entre un aviso que se ignora y uno
que dice dónde mirar.

| Herramientas | |
|---|---|
| Nodos n8n | Webhook · IF · HTTP Request ×2 · Code · Telegram |
| Servicios | Webhook de GitHub (evento `workflow_run`) · API de GitHub · bot |
| Credenciales | Secreto compartido del webhook · PAT de GitHub · token del bot |
| Requiere en el proyecto | **Que exista el workflow de CI** (HU-21) |

```
Webhook  ← GitHub, evento workflow_run
         Authentication: Header Auth        ← imprescindible
   │
   ▼
IF   {{ $json.body.workflow_run.conclusion === 'failure' }}      ← filtrar arriba
   │
   ▼
HTTP Request  GET /repos/.../actions/runs/{id}/jobs
   │
   ▼
HTTP Request  descargar el log del job fallido
   │
   ▼
Code   extraer qué step falló, qué test, qué archivo
       recortar a 15 líneas útiles
   │
   ▼
Telegram   ❌ modulo_policia_backend · main
           Step: npm test
           parser-excel.spec.ts:47 — esperaba 3, recibió 0
           → enlace al run
```

**Detalles críticos:**

- **Los datos del webhook llegan bajo `$json.body`**, no en la raíz. Es el error
  número uno con este nodo.
- **El webhook de n8n es una URL pública sin autenticación por defecto.** Activa
  Header Auth y configura el mismo secreto en GitHub, o cualquiera puede
  inyectarte alertas falsas — o hacerte descargar logs en bucle.
- **El `IF` va arriba del todo.** GitHub dispara `workflow_run` en cada
  ejecución; filtrar tarde significa descargar logs de builds que fueron bien.

---

## 9. Reglas transversales

Aplican a los seis, y las tres primeras son de seguridad:

**Las credenciales van en la sección Credentials, nunca como parámetro de nodo.**
Un token escrito en un parámetro queda en el JSON exportado del workflow y en los
logs de ejecución. En un proyecto de seguridad esto es sangrante, y es fácil de
hacer mal porque el campo acepta el texto sin protestar.

**Todo webhook lleva autenticación.** Header Auth como mínimo. Una URL de n8n sin
autenticar es un endpoint público que ejecuta lógica tuya.

**Principio de mínimo privilegio en los tokens.** El PAT de GitHub del digest
solo necesita lectura. El de Sonar, solo lectura. Un token de administración en
un workflow de notificación es superficie regalada.

**Un Error Trigger por workflow.** Sin él, un workflow que falla lo hace en
silencio — y un monitor silenciosamente roto es peor que no tener monitor, porque
genera confianza infundada. El patrón es un workflow aparte con nodo Error
Trigger que avisa por Telegram.

**Alerta con umbral y con recuperación.** Vale para el monitor de salud y para el
watchdog: sin umbral, ruido; sin aviso de recuperación, incertidumbre.

**Prueba con Manual Trigger antes de activar.** Y revisa las primeras
ejecuciones.

---

## 10. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Endpoint `/health` con `@nestjs/terminus` | No existe | Alta |
| **1. Monitor de salud** | Sin montar | Alta |
| **2. Caducidad de certificados** | Sin montar | Media |
| **3. Cambios en la superficie de la API** | Sin montar | Media |
| Workflow de errores con Error Trigger | Sin montar | Media |
| **4. Watchdog del backup** | Bloqueado — no hay backups | Baja |
| **5. Digest semanal** | Bloqueado — Sonar y Snyk no corren | Baja |
| **6. Alerta de fallo de CI** | Bloqueado — no hay CI | Baja |
| Revisar que ningún token esté en parámetros de nodo | Sin verificar | Alta |
