# EasyPanel — despliegue

> Categoría: plataforma de despliegue · **Veredicto: viable, pero es el punto más expuesto del sistema**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §6

---

## 1. Qué hace

Panel de gestión sobre Docker en un VPS. El `curl` al *deploy hook* dispara una
reconstrucción del contenedor desde el `Dockerfile` del repositorio. Las
variables de entorno se configuran **en el panel, no en el `.env`** del
repositorio, que es lo correcto: mantiene los secretos fuera del control de
versiones.

```
GitHub Actions  →  POST al hook  →  EasyPanel: git pull + docker build + swap
```

---

## 2. Viabilidad para Seguridad de Sistemas

EasyPanel **no es una herramienta de seguridad**: es la superficie sobre la que
corre el sistema. Como decisión de despliegue para un proyecto de este tamaño es
razonable —simplifica mucho frente a gestionar systemd y nginx a mano— y no hay
motivo para cambiarla.

Pero es **donde vive el riesgo real de este proyecto**, y donde el documento
original dedica menos atención en proporción. SonarQube y ZAP buscan
vulnerabilidades hipotéticas en el código; aquí hay, según el propio documento,
una **confirmada y en producción**.

---

## 3. El hallazgo grave

En la sección 5 del documento original, como argumento para posponer ZAP:

> *"Antes conviene cerrar lo que ya se sabe que falta: el CI que corra tests y
> lint, y **las contraseñas de prueba en una base accesible desde internet**."*

Esa frase describe una base de datos expuesta a internet con credenciales
conocidas. No aparece en la tabla de pendientes de la sección 8, ni con prioridad
alta ni con ninguna otra.

**Es el hallazgo de mayor severidad de todo el documento**, y el único que ya está
siendo explotable ahora mismo. Los escáneres automatizados encuentran un Postgres
en el puerto 5432 en cuestión de horas, y prueban credenciales por defecto de
inmediato. No hace falta que nadie tenga interés en este proyecto en concreto.

Lo que corresponde hacer, sin esperar a ninguna otra tarea del pipeline:

1. **Cerrar el puerto.** En EasyPanel, quitar el mapeo público de Postgres. Los
   contenedores de la misma red interna siguen alcanzándolo por nombre de
   servicio; solo se pierde la conexión directa desde fuera.
2. **Para administrar la base, un túnel SSH**, no un puerto abierto:
   `ssh -L 5432:localhost:5432 usuario@servidor`.
3. **Rotar las credenciales**, dando por hecho que las actuales están
   comprometidas. Si estuvo abierto, se asume que se vio.
4. **Revisar qué datos hay dentro.** Si hay algo real de la EPI y no datos
   sintéticos, deja de ser un problema técnico y pasa a ser un incidente con
   obligaciones de notificación.

Coste: una tarde. Es la mejor inversión de seguridad disponible en el proyecto.

---

## 4. `NEXT_PUBLIC_*` no es una variable de entorno privada

El documento apunta el aspecto operativo:

> Las `NEXT_PUBLIC_*` se incrustan en el bundle **durante el build**, así que
> tienen que llegar como *build args*, no solo como variables de ejecución.

Correcto, y hay que añadir la consecuencia de seguridad, porque es una fuente
recurrente de filtraciones en proyectos Next.js:

**Todo lo que lleve el prefijo `NEXT_PUBLIC_` queda escrito en texto plano dentro
del JavaScript que se descarga el navegador.** Es público para cualquiera que
abra las DevTools. El prefijo no es una convención de nombres: es una instrucción
al compilador para que lo exponga.

| Correcto en `NEXT_PUBLIC_*` | **Nunca** en `NEXT_PUBLIC_*` |
|---|---|
| URL de la API | Claves de API de cualquier servicio |
| Clave *publishable* de un proveedor de pagos | Secretos de firma de JWT |
| Nombre del entorno | Cadenas de conexión a base de datos |
| Clave *anon* de Supabase (con RLS activo) | Claves *service role* |

Comprobación de un minuto, y conviene hacerla:

```bash
grep -rhoE "NEXT_PUBLIC_[A-Z_]+" modulo_policial_web/ | sort -u
```

Cualquier nombre en esa lista que contenga `SECRET`, `KEY`, `TOKEN` o `PASSWORD`
ya está publicado, y rotarlo es lo primero.

---

## 5. Superficie de la propia plataforma

EasyPanel es una aplicación web con permisos de root efectivos sobre el VPS:
puede desplegar contenedores, leer todas las variables de entorno y abrir puertos.
Comprometer el panel es comprometer el servidor entero.

| | Qué comprobar |
|---|---|
| **Acceso al panel** | 2FA activo. Contraseña única, no reutilizada |
| **Puerto del panel** | Detrás de HTTPS con certificado válido, nunca en HTTP |
| **Deploy hooks** | Son URLs con un token en la ruta: quien la tenga, despliega. Tratar como secretos |
| **Actualizaciones** | El panel se actualiza a mano; conviene revisarlo cada cierto tiempo |
| **Usuarios** | Un usuario por persona, no una cuenta compartida |

Sobre los hooks, en concreto: no llevan autenticación adicional más allá del
token en la URL. Aparecer en un log, en una captura de pantalla o en un historial
de shell equivale a filtrarlos. Y son regenerables — si hay duda, se regenera.

---

## 6. Backups

No aparecen en el documento original, ni como pendiente. Un `docker build`
fallido no borra datos, pero un `docker volume rm` sí, y en un panel con botones
está a dos clics.

Lo mínimo: volcado periódico de Postgres a almacenamiento **fuera del mismo VPS**,
y una restauración de prueba al menos una vez. Un backup que nunca se ha
restaurado no se sabe si es un backup.

---

## 7. Extensión de VS Code

**No hay.** EasyPanel es un panel web y se administra desde el navegador.

| | |
|---|---|
| Sitio | https://easypanel.io |
| Documentación | https://easypanel.io/docs |

Lo que sí sirve es alcanzar el VPS desde el editor:

| Extensión | ID |
|---|---|
| Remote - SSH | `ms-vscode-remote.remote-ssh` |

https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh

Es además la vía correcta para administrar Postgres una vez cerrado el puerto
público: túnel SSH en lugar de un puerto abierto, como dice la sección 3.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Cerrar el puerto público de Postgres | Abierto | **Crítica** |
| Rotar las credenciales de la base | Sin hacer | **Crítica** |
| Auditar qué datos hay en esa base | Sin hacer | **Alta** |
| Revisar que no haya secretos en `NEXT_PUBLIC_*` | Sin verificar | **Alta** |
| 2FA en el panel | Sin verificar | Media |
| Backups fuera del VPS, con restauración probada | No existen | Media |
| Regenerar los deploy hooks heredados | Pendiente | Media |
