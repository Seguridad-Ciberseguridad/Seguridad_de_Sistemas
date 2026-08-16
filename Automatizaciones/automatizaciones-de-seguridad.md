# Automatizaciones de seguridad — catálogo general

> Categoría: verificación continua, correlación y respuesta (SOAR) · **Aplicable a cualquier sistema con API, servidor y despliegue**
> Índice: [README.md](./README.md) · Relacionadas: [n8n.md](./n8n.md)

---

## 1. Los cuatro escalones

Casi toda la automatización de seguridad que se monta en la práctica se queda en
el primer escalón. Los tres de arriba son donde está el valor.

```
1. Notificar      "algo pasó"
2. Verificar      "compruebo que el control sigue funcionando"
3. Correlacionar  "esta señal + aquella = importa"
4. Responder      "actúo sin esperar a nadie"      ← SOAR
```

**SOAR** —*Security Orchestration, Automation and Response*— es el nombre
profesional del cuarto. Las plataformas comerciales cuestan decenas de miles al
año; para un sistema pequeño o mediano, un orquestador genérico como n8n cubre
los casos que importan.

**El límite honesto:** a partir de cierto volumen de eventos esto pide un SIEM de
verdad —**Wazuh** es la opción libre— con el orquestador como capa de respuesta
encima. Mientras sean estos flujos, el orquestador solo basta.

---

## 2. El catálogo

| | Automatización | Escalón | Potencia | Coste |
|---|---|---|---|---|
| 1 | [Canario de autenticación](#3-canario-de-autenticación) | Verificar | ⭐⭐⭐ | Bajo |
| 2 | [Escaneo de puertos propio](#4-escaneo-de-puertos-propio) | Verificar | ⭐⭐ | Bajo |
| 3 | [Deriva de configuración](#5-deriva-de-configuración) | Verificar | ⭐⭐ | Bajo |
| 4 | [CVE × explotación activa](#6-cve--catálogo-de-explotación-activa) | Correlacionar | ⭐⭐⭐ | Bajo |
| 5 | [Credenciales filtradas](#7-credenciales-filtradas-del-equipo) | Correlacionar | ⭐⭐ | Bajo |
| 6 | [Reputación de IP](#8-reputación-de-ip) | Correlacionar | ⭐⭐ | Bajo |
| 7 | [Bloqueo temporal de IP](#9-bloqueo-temporal-de-ip) | Responder | ⭐⭐ | Medio |
| 8 | [Viaje imposible](#10-viaje-imposible) | Responder | ⭐⭐⭐ | Medio |
| 9 | [Runbook de incidente](#11-runbook-de-incidente) | Responder | ⭐⭐ | Alto |

---

## 3. Canario de autenticación

**Objetivo.** Comprobar continuamente, **en producción**, que el control de
acceso realmente funciona. No espera a que alguien reporte un fallo: intenta
activamente lo que debería estar prohibido y verifica que sigue prohibido.

| Herramientas | |
|---|---|
| Nodos | Schedule Trigger · HTTP Request ×4 · IF · notificación |
| Servicios | La propia API · canal de alerta |
| Credenciales | Tokens de prueba: uno caducado, uno de bajo privilegio |
| Requisitos previos | Cuentas de prueba con roles distintos |

```
Schedule Trigger (cada 5 min)
   ├─→ GET /recurso/1        sin token                 → debe dar 401
   ├─→ GET /admin/...        token de usuario raso     → debe dar 403
   ├─→ GET /recurso/{ajeno}  token de otro propietario → debe dar 403/404
   └─→ GET /recurso/1        token caducado            → debe dar 401
   │
   ▼
IF   ¿alguna devolvió 200?  →  🚨 alerta crítica
```

**Detalles críticos:**

- **`On Error: Continue` en los nodos HTTP.** Un 401 es la respuesta *correcta*
  aquí; si el nodo lo trata como fallo, el workflow muere en el caso bueno.
- **La tercera comprobación es la más valiosa**: verifica autorización a nivel de
  objeto de forma continua. Un pentest la encuentra una vez; esto vigila que no
  vuelva.
- **Es inofensiva.** Son peticiones GET que deben fallar. A diferencia de un
  escaneo activo, se puede ejecutar contra producción sin riesgo.
- Los tokens de prueba deben tener vida larga o renovarse en el propio flujo.

**Es la de mayor relación potencia/coste del catálogo.** Detecta en minutos un
control de acceso roto por un despliegue, que es el fallo más caro y más
silencioso que existe.

---

## 4. Escaneo de puertos propio

**Objetivo.** Detectar deriva de infraestructura: puertos que se abren sin que
nadie lo decida conscientemente. Un agujero cerrado hace seis meses se reabre con
un fichero de composición mal editado.

| Herramientas | |
|---|---|
| Nodos | Schedule Trigger · Execute Command *(o servicio HTTP de escaneo)* · Code · IF · notificación |
| Servicios | `nmap` en el host del orquestador |
| Credenciales | Ninguna |
| Requisitos previos | Lista escrita de puertos que **deben** estar abiertos |

```
Schedule Trigger (diario)
   → Execute Command   nmap -Pn -p- servidor
   → Code              diff contra la lista esperada
   → IF                ¿puerto no previsto?  →  alerta
```

**Detalles críticos:**

- **El requisito previo es el trabajo real.** Sin una lista explícita de puertos
  esperados no hay con qué comparar, y escribirla obliga a justificar cada uno.
- Escanear infraestructura propia es legítimo; escanear ajena, no. Que el destino
  sea siempre una constante del workflow, nunca un parámetro de entrada.
- Si el orquestador es gestionado, Execute Command suele estar deshabilitado.
  Alternativa: un servicio HTTP de comprobación de puertos.
- Un `-p-` completo tarda minutos. Diario está bien; cada hora es innecesario.

---

## 5. Deriva de configuración

**Objetivo.** Vigilar que la configuración de seguridad expuesta no cambia sin
que nadie lo advierta. Complementa al canario: uno vigila la autorización, este
la configuración.

| Herramientas | |
|---|---|
| Nodos | Schedule Trigger · HTTP Request · Code · IF · notificación |
| Servicios | El dominio público · almacenamiento de estado del orquestador |
| Credenciales | Ninguna |
| Requisitos previos | Ninguno |

```
Schedule Trigger (diario)
   ├─→ HEAD dominio             → ¿están las cabeceras de seguridad?
   ├─→ Comprobar TLS            → versión mínima, cifrados débiles
   └─→ OPTIONS con Origin falso → ¿qué respondería CORS?
   │
   ▼
Code  comparar con el estado guardado
   │
   ▼
IF → alerta con el diff
```

**Detalles críticos:**

- Guardar el estado del día anterior en el almacenamiento persistente del
  orquestador y **alertar sobre el cambio**, no sobre el valor absoluto. Un aviso
  diario con la misma lista se ignora en una semana.
- La comprobación de CORS es la que más sorpresas da: un comodín que se puso
  "temporalmente" para depurar y se quedó.

---

## 6. CVE × catálogo de explotación activa

**Objetivo.** Separar la vulnerabilidad teórica de la que **se está explotando
hoy**. Es la automatización que más ruido elimina de todo el catálogo.

| Herramientas | |
|---|---|
| Nodos | Schedule Trigger · HTTP Request ×3 · Merge · Code · IF · notificación |
| Servicios | Tu fuente de vulnerabilidades (Dependabot, Snyk, Trivy) · catálogo **CISA KEV** · **EPSS** |
| Credenciales | Solo la de tu fuente — KEV y EPSS son públicos y sin autenticación |
| Requisitos previos | Algún escáner de dependencias ya funcionando |

```
Schedule Trigger (diario)
   ├─→ HTTP  tus alertas de dependencias
   ├─→ HTTP  catálogo CISA KEV   (explotadas activamente)
   └─→ HTTP  EPSS                (probabilidad de explotación)
   │
   ▼
Merge → Code   intersección por identificador CVE
   │
   ▼
IF  ¿coincidencia?  →  🚨 "esto no es teórico"
```

**Detalles críticos:**

- **El efecto real:** de 40 CVEs que reporta un escáner, el catálogo KEV suele
  dejar 2 o 3. Eso convierte una lista que nadie prioriza en un aviso que se
  atiende.
- EPSS da una probabilidad continua; KEV es binario y más contundente. Usar KEV
  como disparador y EPSS para ordenar el resto.
- **Es la mejor respuesta a la fatiga de alertas** en gestión de dependencias, que
  es el motivo por el que casi todo el mundo acaba ignorando su escáner.

---

## 7. Credenciales filtradas del equipo

**Objetivo.** Enterarse de que la cuenta de alguien del equipo aparece en una
filtración conocida, antes que quien compró la lista.

| Herramientas | |
|---|---|
| Nodos | Schedule Trigger · HTTP Request · IF · notificación |
| Servicios | API de **Have I Been Pwned** (búsqueda por dominio) |
| Credenciales | Clave de API de HIBP (de pago, coste bajo) |
| Requisitos previos | Control del dominio de correo del equipo |

```
Schedule Trigger (semanal)
   → HTTP  HIBP: brechas del dominio
   → IF    ¿alguien nuevo?  →  notificar + forzar rotación
```

**Detalles críticos:**

- Ataca la vía que no depende de tu código: **reutilización de contraseñas**. Una
  cuenta de administrador comprometida por una filtración ajena es más probable
  que un fallo desconocido en tu software.
- La respuesta correcta es rotar, no solo avisar — y comprobar si esa cuenta
  tiene segundo factor.

---

## 8. Reputación de IP

**Objetivo.** Distinguir al usuario despistado del escáner automatizado, para no
tratar igual dos cosas que no se parecen.

| Herramientas | |
|---|---|
| Nodos | Webhook *(o consulta programada de logs)* · HTTP Request ×2 · Code · IF |
| Servicios | **AbuseIPDB**, **GreyNoise** o **VirusTotal** · una base GeoIP |
| Credenciales | Claves de API (los tres tienen plan gratuito) |
| Requisitos previos | Que la aplicación emita un evento ante fallos de login repetidos |

```
Disparador: N fallos de login desde una IP
   → HTTP  reputación
   → HTTP  geolocalización, ASN
   → Code  puntuación combinada
   → IF alta  →  escalar (o alimentar la automatización 9)
```

**Detalles críticos:**

- Por sí sola solo enriquece. Su valor aparece **encadenada** con la siguiente.
- Los planes gratuitos tienen cuota diaria: cachear el resultado por IP durante
  24 h, o se agota en el primer ataque serio.

---

## 9. Bloqueo temporal de IP

**Objetivo.** Cortar un ataque en curso sin esperar a que alguien lea una
notificación.

| Herramientas | |
|---|---|
| Nodos | Trigger de detección · HTTP Request · Code · IF · notificación |
| Servicios | **CrowdSec**, fail2ban, o la API del cortafuegos / CDN |
| Credenciales | Clave de la API de bloqueo — **con permiso mínimo** |
| Requisitos previos | La automatización 8 · lista blanca escrita |

```
Detección  →  enriquecer reputación
           →  IF puntuación alta y no está en lista blanca
                 →  API: banear 24 h
                 →  registrar la decisión
                 →  notificar (informativo, no pide permiso)
```

**Detalles críticos:**

- **Bloqueo temporal, nunca permanente.** 24 horas corta el ataque y limita el
  daño de un falso positivo.
- Ver la sección 12: esta es la automatización que más fácilmente se vuelve
  contra ti.

---

## 10. Viaje imposible

**Objetivo.** Detectar credenciales compartidas o robadas mediante una señal muy
fiable: la misma cuenta autenticándose desde dos lugares incompatibles con el
desplazamiento físico.

| Herramientas | |
|---|---|
| Nodos | Webhook · HTTP Request · Code · IF · HTTP Request · notificación |
| Servicios | Base GeoIP · endpoint propio de revocación de sesión |
| Credenciales | Secreto del webhook · token de administración de sesiones |
| Requisitos previos | Que la aplicación emita un webhook en cada login · un mecanismo de revocación |

```
Login  →  webhook
   → GeoIP de la IP
   → recuperar el último login de ese usuario
   → Code:  distancia / tiempo  >  900 km/h ?
   → IF sí:  revocar la sesión
             forzar reautenticación
             alertar
```

**Detalles críticos:**

- **Es de las señales de compromiso más fiables que existen**, y no necesita
  ninguna herramienta comercial: geolocalización más aritmética.
- **Las VPN generan falsos positivos.** Mantener una lista de ASN conocidos del
  equipo, o el aviso pierde credibilidad rápido.
- Umbral generoso —900 km/h es un avión comercial— para que el disparo signifique
  algo.
- Requiere que la aplicación tenga **revocación real de sesión**. Con JWT sin
  lista de revocación, esto no se puede implementar: es una decisión de
  arquitectura previa.

---

## 11. Runbook de incidente

**Objetivo.** Capturar el estado del sistema **mientras existe**. En un incidente
real se pierde tiempo y evidencia recopilando a mano lo que ya se ha rotado.

| Herramientas | |
|---|---|
| Nodos | Trigger de alerta crítica · Execute Command / SSH · HTTP Request ×N · notificación |
| Servicios | Almacenamiento de evidencia · gestor de incidencias · canal prioritario |
| Credenciales | Acceso al servidor · token del gestor de incidencias |
| Requisitos previos | Las automatizaciones que generan la alerta · almacenamiento externo |

```
Alerta crítica de cualquier origen
   → crear registro de incidente con marca de tiempo
   → capturar logs de la última hora y estado de los servicios
   → disparar copia de seguridad inmediata
   → subir la evidencia a almacenamiento externo
   → notificar por canal prioritario
   → abrir ticket con todo enganchado
```

**Detalles críticos:**

- **La evidencia va a almacenamiento externo**, no al servidor afectado. Si está
  comprometido, lo que guardes allí no es fiable.
- El registro con marca de tiempo es lo que después sostiene una notificación de
  brecha ante quien corresponda. En muchas jurisdicciones hay plazo legal, y la
  cronología se reconstruye mal de memoria.
- Es la más cara de montar y la que menos se ejecuta. Su valor es que funciona el
  día que hace falta — conviene **probarla en seco** una vez.

---

## 12. La advertencia sobre la respuesta automática

**Automatizar la respuesta es un arma que apunta en las dos direcciones.**

Quien sepa que bloqueas IPs automáticamente puede provocar que **bloquees a tus
propios usuarios**: basta con generar tráfico aparentemente hostil desde la IP de
tu oficina. La automatización de respuesta se convierte entonces en el vector de
denegación de servicio.

Cuatro reglas, no negociables:

1. **Límite de tasa en tus propias acciones.** Máximo N bloqueos por hora;
   superado ese umbral, escalar a un humano en lugar de seguir actuando.
2. **Lista blanca permanente** de las IPs y cuentas del equipo y de las
   ubicaciones legítimas.
3. **Toda acción automática, reversible y registrada** — quién, qué, cuándo y por
   qué. Sin registro no hay forma de deshacer ni de auditar.
4. **Lo destructivo lleva humano en el bucle.** Bloquear una IP durante 24 horas,
   sí. Suspender la cuenta de una persona que está trabajando, no sin
   confirmación.

Y una regla transversal a todo el catálogo, igual que en [n8n.md](./n8n.md) §9:
**las credenciales van en el gestor de credenciales del orquestador, nunca como
parámetro de nodo**, y con el permiso mínimo. Un token de administración dentro
de un flujo de notificación es superficie regalada.

---

## 13. Orden de adopción

```
Nivel 1  Canario de autenticación · CVE × KEV · escaneo de puertos
         Baratos, sin dependencias, y verifican en vez de solo avisar

Nivel 2  Deriva de configuración · credenciales filtradas
         Igual de baratos, cubren frentes distintos

Nivel 3  Reputación de IP → bloqueo temporal
         Se montan juntos; aquí empieza la respuesta y aplica la sección 12

Nivel 4  Viaje imposible
         Requiere webhooks de login y revocación real de sesión

Nivel 5  Runbook de incidente
         Tiene sentido cuando ya hay varias fuentes de alerta que orquestar
```

Regla general: **verificar antes que responder.** Un sistema que responde
automáticamente a señales que no ha verificado hace daño más rápido que un
atacante.
