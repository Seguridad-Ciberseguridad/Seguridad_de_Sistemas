# OWASP ZAP — DAST

> Categoría: análisis dinámico de la aplicación en ejecución (DAST) · **Veredicto: viable, después del CI**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §5

---

## 1. Qué hace

En vez de leer el código, **ataca la aplicación ya corriendo**. Actúa como un
proxy y como un cliente hostil: recorre la aplicación, cataloga los endpoints y
les manda peticiones deformadas para ver qué devuelven.

```
SonarQube (SAST)   lee el código      →  "esta función es vulnerable"
ZAP        (DAST)  ataca la app viva  →  "este endpoint responde sin token"
```

La diferencia importa: ZAP encuentra cosas que el SAST **no puede** ver, porque
solo existen cuando el sistema está montado. Un guard que se olvidó de registrar,
una cabecera de seguridad que el reverse proxy no pone, un endpoint de debug que
quedó publicado, una URL de archivo que responde sin firma.

---

## 2. Cómo funciona por dentro

Es un **proxy de interceptación**: se sitúa entre el cliente y la aplicación y ve
todo el tráfico. Sobre eso monta dos análisis muy distintos, y la diferencia
decide si puedes ejecutarlo o no en un entorno dado.

| | Escaneo pasivo | Escaneo activo |
|---|---|---|
| Qué hace | Observa el tráfico que ya pasa | Inyecta cargas de ataque en cada parámetro |
| Peticiones extra | **Ninguna** | Miles |
| Qué encuentra | Cabeceras ausentes, cookies sin `Secure`/`HttpOnly`, información filtrada en respuestas | SQLi, XSS, path traversal, inyección de comandos |
| Riesgo | Nulo | **Destructivo** |

Para saber *qué* atacar necesita antes descubrir la superficie. Tres caminos:

- **Spider** — sigue enlaces del HTML. Inútil contra una API JSON.
- **AJAX Spider** — abre un navegador real. Sirve para la web Next.js.
- **Importar el OpenAPI** — le das el contrato y conoce todos los endpoints, sus
  parámetros y sus tipos.

Para el backend NestJS, el tercero es el único que tiene sentido: el spider no
encuentra endpoints de API porque no hay enlaces que seguir.

---

## 3. Sobre el nombre

El proyecto **salió de OWASP en 2024** y hoy se llama simplemente **ZAP** (Zed
Attack Proxy), bajo el Software Security Project. Sigue siendo software libre y
la herramienta es la misma; el nombre "OWASP ZAP" se usa por costumbre. Se
menciona porque afecta a las búsquedas de documentación: la actual está en
`zaproxy.org`, no en el wiki de OWASP.

---

## 4. Viabilidad para Seguridad de Sistemas

**Sí, y encaja especialmente bien en este proyecto.** El backend es una API
NestJS con autenticación JWT: eso es exactamente el escenario donde el escaneo de
API da resultados concretos y no ruido.

Dónde encajaría: **tras desplegar al entorno de pruebas**, escaneando la API. Lo
que detectaría de forma realista aquí:

- endpoints sin `JwtAuthGuard` — el fallo más común y el más caro,
- endpoints con guard pero sin comprobación de *rol* (autorización horizontal),
- URLs de archivos accesibles sin firma,
- cabeceras de seguridad ausentes (`helmet` no puesto o mal puesto),
- mensajes de error que filtran stack traces o versiones,
- CORS demasiado permisivo.

**Pero la prioridad es baja hoy, y el motivo es correcto.** Antes hay que cerrar
lo que ya se sabe que falta: el CI que corra tests y lint, y las contraseñas de
prueba en una base accesible desde internet. ZAP sirve para *descubrir* problemas
desconocidos; no tiene sentido pagar ese coste mientras hay problemas **conocidos
y sin cerrar**. Cobra sentido cuando el sistema esté cerca de manejar datos
reales de la EPI.

---

## 5. Los tres modos, y cuál usar

| Modo | Action | Qué hace | Duración | ¿En CI? |
|---|---|---|---|---|
| **Baseline** | `zaproxy/action-baseline` | Solo escaneo pasivo: mira el tráfico, no ataca | 1–2 min | **Sí** |
| **API scan** | `zaproxy/action-api-scan` | Parte de un OpenAPI/Swagger y ataca cada operación | 5–20 min | Sí, nocturno |
| **Full scan** | `zaproxy/action-full-scan` | Spider + escaneo activo completo | 20 min – horas | No |

Para este proyecto el orden natural es **API scan**, no baseline: NestJS con
`@nestjs/swagger` ya genera el OpenAPI, y darle a ZAP el contrato de la API le
ahorra tener que adivinar los endpoints con el spider. La cobertura sube mucho.

```yaml
  zap:
    runs-on: ubuntu-latest
    steps:
      - uses: zaproxy/action-api-scan@v0.9.0
        with:
          target: 'https://staging.ejemplo/api-json'
          format: openapi
          cmd_options: '-a'
```

---

## 6. El punto difícil: la autenticación

Es donde fracasan la mayoría de los montajes de DAST, y conviene saberlo antes de
empezar.

Si ZAP escanea sin autenticarse, **todo lo que hay detrás del login es invisible
para él**: recibe 401 en todas partes, el informe sale limpio y da una falsa
sensación de seguridad. Un informe verde de un escaneo no autenticado no
significa nada.

Con JWT, el camino más simple es inyectar un token de un usuario de pruebas como
cabecera fija:

```yaml
          cmd_options: '-a -z "-config replacer.full_list(0).description=auth
                        -config replacer.full_list(0).enabled=true
                        -config replacer.full_list(0).matchtype=REQ_HEADER
                        -config replacer.full_list(0).matchstr=Authorization
                        -config replacer.full_list(0).replacement=Bearer ${{ secrets.ZAP_TOKEN }}"'
```

Esto trae dos consecuencias que hay que aceptar de antemano:

1. **Hay que gestionar la caducidad del token.** Un JWT de 15 minutos se agota a
   mitad de escaneo y la segunda mitad del informe es basura. O se emite uno de
   vida larga solo para el entorno de pruebas, o el pipeline hace login primero y
   extrae el token.
2. **Se escanea con los permisos de ese usuario.** Para encontrar fallos de
   autorización hacen falta al menos dos usuarios de roles distintos, y comparar.

---

## 7. Reglas de uso

- **Nunca contra producción sin autorización explícita y por escrito.** El
  escaneo activo manda miles de peticiones con cargas maliciosas: crea registros
  basura, dispara alertas, puede borrar datos a través de endpoints `DELETE` que
  encuentre, y puede tumbar el servicio. Contra un sistema de la EPI, además,
  hacerlo sin permiso documentado es un problema legal, no solo técnico.
- **Solo contra un entorno de pruebas con datos sintéticos**, que se pueda
  reconstruir.
- **El escaneo activo no va en el pipeline de cada push.** Va en un job nocturno
  o manual (`workflow_dispatch`).

---

## 8. Expectativas realistas

ZAP genera **falsos positivos con generosidad**. Un primer informe con 40
alertas es normal, y una buena parte serán informativas o no aplicables. Sin un
fichero de reglas que silencie lo ya revisado, el equipo deja de leer los
informes en la segunda semana y la herramienta se vuelve decorativa.

El fichero `.zap/rules.tsv` sirve para eso:

```tsv
10015	IGNORE	(Incomplete or No Cache-control Header)
10096	IGNORE	(Timestamp Disclosure)
```

Regla práctica: cada alerta silenciada lleva un motivo escrito. Sin motivo, no se
silencia.

---

## 9. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Entorno de pruebas estable que escanear | No existe | Bloqueante |
| API scan sobre el OpenAPI del backend | Sin empezar | Baja |
| Estrategia de token para el escaneo autenticado | Sin definir | Baja |
| `.zap/rules.tsv` con exclusiones justificadas | Sin empezar | Baja |

El bloqueante real es el primero: sin un entorno de pruebas desplegado y
reconstruible, no hay nada que escanear de forma segura.
