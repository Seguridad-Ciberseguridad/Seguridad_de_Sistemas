# Flujo CIA+AAA — Custodia segura de archivos vía Telegram

> Categoría: **control preventivo + detectivo** · Escalón: **Verificar + Correlacionar + Responder**
> Relacionadas: [automatizaciones-de-seguridad.md](./automatizaciones-de-seguridad.md) · [n8n.md](./n8n.md)
> Conceptos que cubre: CIA (Confidencialidad, Integridad, Disponibilidad) · AAA (Autenticación, Autorización, Accounting) · Riesgo · Amenaza · Vulnerabilidad

---

## 1. Qué es esta automatización

Un flujo n8n que recibe archivos enviados por Telegram, los valida, los analiza con VirusTotal, los cifra y los custodia en Google Drive. Solo usuarios con rol `admin` en Supabase pueden interactuar con el sistema. Cada acción queda registrada en un audit log en Google Sheets.

**No es solo una automatización de archivos.** Es un sistema de control de acceso, detección de amenazas y custodia que hace tangibles los conceptos del Mes 1 de ciberseguridad — CIA, AAA, riesgo, amenaza y vulnerabilidad — en un flujo real y funcional.

---

## 2. Tipo de automatización

| Dimensión | Clasificación |
|---|---|
| Escalón SOAR | Verificar + Correlacionar + Responder |
| Tipo de control ISO 27002 | Preventivo (cifrado, lista blanca) + Detectivo (hash, audit log) |
| Categoría | Gestión de activos + Control de acceso + Criptografía |
| Controles del Anexo A que implementa | A.5.10 Uso aceptable · A.5.15 Control de acceso · A.8.3 Restricción de acceso · A.8.24 Uso de criptografía |

---

## 3. Objetivos

### Objetivo principal
Aplicar CIA + AAA en un flujo real y funcional — no en teoría — usando herramientas reales (n8n, Supabase, Google Sheets, Drive, VirusTotal, Telegram) para entender cómo cada concepto de seguridad se traduce en una decisión técnica concreta.

### Qué se quiere aprender con esto y por qué

| Concepto | Qué se aprende | Por qué importa |
|---|---|---|
| Autenticación (AAA) | Cómo verificar identidad de un remitente contra una base de datos real (Supabase) | En sistemas reales no basta con confiar en quien dice ser — hay que verificarlo contra una fuente de verdad |
| Autorización (AAA) | Cómo el rol de un usuario determina qué puede hacer, no solo si puede entrar | La autenticación y la autorización son controles distintos — pasar uno no garantiza pasar el otro |
| Accounting (AAA) | Cómo construir un audit log append-only que registre cada acción con contexto completo | Sin trazabilidad no hay forense posible — el log es la evidencia |
| Integridad (CIA) | Cómo SHA-256 detecta si un archivo fue modificado entre una entrega y otra | Un hash cambiado es una señal de alerta — puede ser un ataque o un error, pero hay que saberlo |
| Confidencialidad (CIA) | Cómo AES-256 protege el contenido de un archivo en reposo | Cifrar no es opcional cuando el activo tiene valor — el archivo en Drive sin cifrar es un riesgo residual |
| Disponibilidad (CIA) | Cómo el sistema responde siempre — aunque sea para rechazar — y notifica al usuario | Un sistema que falla silenciosamente no es confiable — la respuesta es parte del control |
| Amenaza | Cómo un intento de acceso no autorizado se registra como evento de seguridad, no solo se ignora | Ignorar un intento fallido es perder información valiosa sobre quién intenta acceder y cuándo |
| Vulnerabilidad | Cómo una extensión peligrosa (.exe, .bat, .js) es una vulnerabilidad explotable si no se controla | El vector de ataque más común es el archivo malicioso — detectarlo antes de procesarlo es control preventivo |
| Riesgo | Cómo el nivel de riesgo se calcula automáticamente según integridad + veredicto de VirusTotal | El riesgo no es binario — hay que cuantificarlo para priorizar la respuesta |
| Análisis de malware | Cómo integrar VirusTotal para obtener un veredicto externo sobre un archivo sospechoso | Ningún sistema de seguridad es una isla — la inteligencia de amenazas externa mejora la detección |

### Objetivos específicos del flujo

| # | Objetivo | Propiedad CIA/AAA que implementa |
|---|---|---|
| 1 | Solo usuarios con rol `admin` en Supabase pueden subir archivos | Autenticación + Autorización |
| 2 | Detectar extensiones peligrosas antes de procesar el archivo | Vulnerabilidad — control preventivo |
| 3 | Calcular SHA-256 del archivo al recibirlo | Integridad |
| 4 | Comparar el hash con versiones anteriores y detectar cambios | Integridad + Trazabilidad |
| 5 | Analizar con VirusTotal si el hash cambió | Amenaza — detección activa |
| 6 | Cifrar el archivo con AES-256 antes de almacenarlo en Drive | Confidencialidad |
| 7 | Actualizar el hash en Google Sheets después de procesar | Integridad — estado actualizado |
| 8 | Registrar cada acción en audit log (quién, qué, cuándo, resultado) | Accounting + Trazabilidad |
| 9 | Notificar al usuario el resultado del procesamiento | Disponibilidad + Autenticidad |
| 10 | Alertar al equipo si se detecta malware confirmado | Respuesta ante incidentes |

---

## 4. Conceptos de seguridad que hace tangibles

### CIA
| Propiedad | Cómo la implementa este flujo |
|---|---|
| Confidencialidad | Lista blanca de correos + cifrado AES-256 del archivo almacenado |
| Integridad | Hash SHA-256 calculado al recibir y comparado en cada acceso posterior |
| Disponibilidad | Notificación de confirmación al usuario; el sistema responde siempre, aunque sea para rechazar |

### AAA
| Propiedad | Cómo la implementa este flujo |
|---|---|
| Autenticación | Verificación del remitente de Telegram contra lista blanca de correos |
| Autorización | Solo usuarios autorizados pueden subir; el sistema rechaza y registra los demás |
| Accounting | Audit log con cada acción: usuario · acción · archivo · timestamp · resultado |

### Riesgo, Amenaza, Vulnerabilidad
| Concepto | Cómo aparece en el flujo |
|---|---|
| Amenaza | Intento de acceso de correo no autorizado → se registra como amenaza activa |
| Vulnerabilidad | Archivo con extensión peligrosa (.exe, .js, .bat) → se detecta antes de procesar |
| Riesgo | Nivel calculado automáticamente: tipo de archivo × sensibilidad → bajo / medio / alto / crítico |
| Riesgo residual | El archivo cifrado con hash verificado es el riesgo residual después de aplicar los controles |

---

## 5. Arquitectura del flujo

```
TELEGRAM (usuario sube archivo)
        ↓
[Telegram Trigger] Recibe el mensaje
        ↓
[Normalizar y Clasificar] Extrae userId, fileName, extension, isDangerous
        ↓
[IF] ¿Tiene archivo adjunto? (fileSize > 0)
        ├── NO  → Telegram: "sube un archivo para comenzar"
        └── SÍ  ↓
[Verificar Rol en Supabase] Busca telegram_id en tabla public.users
        ↓
[Evaluar Rol] Determina isAuthorized (rol === "admin")
        ↓
[Remitente Autorizado?]
        ├── NO  → Log AMENAZA + Telegram: "acceso denegado"
        └── SÍ  ↓
[Descargar Archivo] Descarga el binario desde Telegram
        ↓
[Extension Peligrosa?] (.exe .bat .cmd .js .vbs .ps1 .sh .dll ...)
        ├── SÍ  → Cuarentena Drive + Log VULNERABILIDAD + Telegram: "archivo rechazado"
        └── NO  ↓
[Calcular SHA-256] Hash del binario
        ↓
[Preparar Archivo] Consolida json + binary para nodos siguientes
        ↓
[Leer Hash Anterior] Busca en Google Sheets hoja "Hashes" por file_name
        ↓
[Comparar Integridad] NUEVO / OK (BAJO) / INTEGRIDAD COMPROMETIDA (ALTO)
        ↓
[Se modifico?] integrityStatus === "INTEGRIDAD COMPROMETIDA"
        ├── SÍ (true)  ↓
        │   [Subir archivo a VirusTotal] multipart POST
        │   [Wait 15s]
        │   [Obtener Resultado del analisis] GET /analyses/{id}
        │   [Interpretar VirusTotal] verdict + riskLevel
        │   [Esta Limpio?] verdict contains "MALWARE"
        │       ├── SÍ → [Avisar al equipo] alerta crítica por Telegram
        │       └── NO → [Notificar Proceso de VirusTotal] resultado al usuario
        │                ↓
        │           [Preparar Log] consolida datos de ambas ramas
        │                ↓
        └── NO (false) → [Preparar Log] (riskLevel de Comparar Integridad, verdict N/A)
                              ↓
                    [Log Integridad] append hoja "Auditoria"
                              ↓
                    [Cifrar Archivo (AES-256)]
                              ↓
                    [Convertir Cifrado a Archivo] → .enc binario
                              ↓
                    [Guardar Cifrado Drive] carpeta "Archivos Cifrados"
                              ↓
                    [Actualizar Hash] appendOrUpdate hoja "Hashes"
                              ↓
                    [Notificar Procesado] Telegram al usuario
                              ↓
                    [Audit Log Completo] append hoja "Auditoria"
```

---

## 6. Estructura del audit log

Cada fila del Google Sheets de auditoría tiene este formato:

| timestamp | usuario | correo | accion | archivo | hash_sha256 | resultado | nivel_riesgo | observacion |
|---|---|---|---|---|---|---|---|---|
| 2026-08-21 14:32:01 | @garcia | garcia@empresa.com | UPLOAD | informe.pdf | a3f9... | OK | ALTO | Hash nuevo registrado |
| 2026-08-21 14:45:10 | @unknown | noautorizado@x.com | UPLOAD | datos.csv | — | RECHAZADO | — | AMENAZA: correo no en lista blanca |
| 2026-08-21 15:01:22 | @garcia | garcia@empresa.com | UPLOAD | informe.pdf | b7c2... | ALERTA | CRÍTICO | INTEGRIDAD COMPROMETIDA: hash cambió |

---

## 7. Matriz de riesgo del flujo

| Activo | Amenaza | Vulnerabilidad | Probabilidad | Impacto | Riesgo | Tratamiento |
|---|---|---|---|---|---|---|
| Archivo subido | Acceso no autorizado | Lista blanca mal configurada | Media | Alto | Alto | Mitigar — validación estricta de correos |
| Hash almacenado | Manipulación del hash | Google Sheets sin control de versiones | Baja | Crítico | Alto | Mitigar — hoja protegida + historial |
| Archivo cifrado | Robo del archivo en Drive | Permisos de Drive mal configurados | Media | Alto | Alto | Mitigar — carpeta privada solo para el flujo |
| Audit log | Borrado de evidencia | Acceso de escritura al log | Baja | Alto | Medio | Mitigar — hoja append-only, sin borrado |
| Credenciales n8n | Filtración de tokens | Token en texto plano en el flujo | Media | Crítico | Crítico | Mitigar — gestor de credenciales de n8n |

---

## 8. Herramientas y requisitos

| Elemento | Detalle |
|---|---|
| Orquestador | n8n.cloud |
| Trigger | Telegram Bot (BotFather) — bot `Testeando_Workflow` |
| Autenticación de usuarios | Supabase — tabla `public.users`, columna `telegram_id bigint` + columna `rol` |
| Almacenamiento de hashes | Google Sheets — hoja `Hashes` (file_name, sha256, user_id, updated_at) |
| Almacenamiento de archivos cifrados | Google Drive — carpeta `Carpeta de archivos Cifrados` |
| Cuarentena | Google Drive — carpeta `Carpeta de Cuarentena` |
| Cifrado | Nodo Crypto de n8n — AES-256 |
| Análisis de malware | VirusTotal API v3 — plan gratuito, Header Auth `x-apikey` |
| Audit log | Google Sheets — hoja `Auditoria` (append-only) |
| Notificaciones | Telegram al usuario + Telegram al admin en caso de malware confirmado |

---

## 9. Reglas no negociables del flujo

1. Las credenciales (tokens de Telegram, Google) van en el gestor de credenciales de n8n, nunca como parámetro de nodo.
2. El audit log es append-only: el flujo solo añade filas, nunca borra ni edita.
3. El archivo original se elimina del flujo después de cifrarlo — nunca se almacena en claro.
4. Si se detectan 3 violaciones de integridad seguidas del mismo usuario, el flujo lo bloquea y notifica al admin.
5. La lista blanca se actualiza manualmente por el admin, nunca por el propio flujo.

---

## 10. Relación con el entregable del Mes 1

Este flujo es una implementación práctica del análisis de riesgos ISO 27005 que pide el entregable:

- Los activos están identificados (sección 7 de este documento)
- Las amenazas y vulnerabilidades están mapeadas por activo
- La probabilidad × impacto está calculada
- El tratamiento está definido (mitigar en todos los casos críticos)
- Los controles del Anexo A están identificados (sección 2)

Cuando construyas el entregable formal, puedes usar este flujo como el caso práctico de la empresa ficticia.

---

## 11. Estado actual del flujo

- [x] Telegram Trigger + Normalizar y Clasificar
- [x] Verificar Rol en Supabase + Evaluar Rol + Remitente Autorizado?
- [x] Descargar Archivo + Extension Peligrosa? + Cuarentena Drive
- [x] Calcular SHA-256 + Preparar Archivo + Leer Hash Anterior + Comparar Integridad
- [x] Se modifico? → Subir a VirusTotal → Wait → Obtener Resultado → Interpretar VirusTotal
- [x] Esta Limpio? → Avisar al equipo (malware) / Notificar Proceso de VirusTotal (limpio)
- [x] Preparar Log (consolida datos de ambas ramas)
- [x] Log Integridad → Cifrar → Convertir → Guardar Drive → Actualizar Hash → Notificar Procesado → Audit Log Completo
- [x] Rama false de "Se modifico?" conectada a Preparar Log (sin pasar por VirusTotal)

---

*Documento creado el 2026-08-21 como práctica del Mes 1 — CIA + AAA + Riesgo aplicados.*
*Actualizado el 2026-08-22 con el flujo real implementado en n8n.cloud.*
