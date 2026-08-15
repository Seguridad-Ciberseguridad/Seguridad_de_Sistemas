# Burp Suite Community — pruebas manuales

> Categoría: proxy de interceptación, trabajo manual · **Veredicto: viable e insustituible para BOLA**
> Índice: [README.md](./README.md) · Relacionadas: [owasp-zap.md](./owasp-zap.md) · [owasp-api-top-10.md](./owasp-api-top-10.md)

---

## 1. Qué hace

Se coloca entre el cliente y la aplicación y te deja **ver, modificar y reenviar**
cada petición. Es la herramienta con la que una persona prueba hipótesis
concretas: *"¿y si cambio este ID?", "¿y si borro esta cabecera?"*.

Comparte mecanismo con ZAP —los dos son proxies— pero el flujo de trabajo es el
opuesto:

```
ZAP    automatizado, en el pipeline    "¿hay fallos conocidos?"
Burp   manual, dirigido por una persona "¿qué pasa si hago esto?"
```

---

## 2. Por qué hace falta si ya está ZAP

Porque **el fallo nº1 de las APIs no es detectable automáticamente.**

BOLA —autorización a nivel de objeto, API1 del [Top 10](./owasp-api-top-10.md)—
es que un usuario acceda a un recurso que no le corresponde cambiando un
identificador. Ninguna herramienta automática lo encuentra, y el motivo es
estructural: la respuesta es un **200 perfectamente formado**. ZAP ve un 200,
Schemathesis ve un 200 que cumple el esquema, SonarQube ve código que compila.
Todas tienen razón. Nadie salvo un humano sabe que ese parte no le correspondía a
ese usuario.

Es también el fallo más caro en un sistema policial: no es un error técnico, es
un policía leyendo el expediente de quien no debe. Y no deja rastro salvo que
haya registro de auditoría.

---

## 3. Qué trae la edición Community

| Módulo | Uso |
|---|---|
| **Proxy** | Interceptar y modificar peticiones al vuelo |
| **Repeater** | Reenviar una petición cambiando lo que quieras, las veces que quieras |
| **Decoder** | Base64, URL-encoding, decodificar el payload de un JWT |
| **Comparer** | Diferencias entre dos respuestas |
| **Intruder** | Automatización básica — **fuertemente ralentizada** en la versión gratuita |
| ~~Scanner~~ | **No está.** Es exclusivo de la versión Pro |

La ausencia del escáner no importa aquí: para eso está ZAP, que es gratis y
automatizable. Community da exactamente lo que ZAP no da, que es Repeater.

El Intruder ralentizado sí es una limitación real — sirve para probar 20 valores,
no 2.000. Para eso se usa un script.

---

## 4. El flujo que importa: probar BOLA

Este es el procedimiento completo, y merece la pena tenerlo escrito porque es
repetible:

1. Crea **dos usuarios de prueba** de distinta jurisdicción o rol: A y B.
2. Como **A**, crea un recurso. Anota su ID: `/partes/123`.
3. Como **B**, entra y captura cualquier petición autenticada en el Proxy.
4. Manda esa petición al **Repeater** (`Ctrl+R`).
5. Cambia la ruta a `/partes/123` — el recurso de A — dejando el token de B.
6. Envía.

Interpretación:

| Respuesta | Veredicto |
|---|---|
| `403` / `404` | Correcto |
| `200` con los datos de A | **BOLA confirmado** |
| `500` | Otro fallo distinto, también reportable |

Y hay una variante que se escapa con frecuencia: repetir el mismo ejercicio con
**`PATCH` y `DELETE`**, no solo con `GET`. Es habitual proteger la lectura y
olvidar la escritura.

Extiéndelo también a la escalada vertical (API5): coge un endpoint de
administración y llámalo con el token de un usuario normal.

---

## 5. Montaje

```
1. Descargar Burp Community de portswigger.net
2. Proxy → por defecto escucha en 127.0.0.1:8080
3. Instalar el certificado CA de Burp en el navegador,
   o el tráfico HTTPS no se puede leer
   → http://burpsuite (con el proxy activo) → CA Certificate
4. Configurar el navegador para usar el proxy
```

El paso 3 es donde se atasca todo el mundo: sin el certificado, cada petición
HTTPS da error y parece que Burp está roto.

Para probar la **app móvil** (`modulo_policia_app`) hace falta además instalar el
CA en el dispositivo, y Android 7+ ignora los certificados de usuario salvo que
la aplicación lo permita explícitamente en su configuración de red. Es un
obstáculo conocido y tiene solución, pero cuenta con dedicarle un rato.

---

## 6. Uso responsable

Lo mismo que aplica a ZAP, con más motivo porque aquí las peticiones las lanzas
tú deliberadamente:

- **Solo contra sistemas propios o con autorización escrita.** Interceptar
  tráfico de terceros o probar contra un sistema ajeno es delito, y la
  herramienta no distingue.
- **Contra el entorno de pruebas**, con datos sintéticos.
- **Documenta lo que encuentres** con la petición y la respuesta completas. Un
  hallazgo de BOLA sin el `curl` que lo reproduce no se puede arreglar ni
  verificar.

---

## 7. Por qué vale la pena aunque no sea automatizable

Es la herramienta que enseña **cómo funciona una petición HTTP de verdad**. Ver
el `Authorization` en crudo, decodificar el JWT y descubrir que el `exp` es de
tres meses, quitar una cabecera y ver que la API responde igual: eso construye la
intuición que después hace que leas el código de otra manera.

Para una asignatura de Seguridad de Sistemas es probablemente lo más formativo de
toda la lista. Y en el trabajo real, **una sesión manual de dos horas con Burp
suele encontrar más que un mes de escáneres**, porque encuentra lo que los
escáneres no pueden ver por diseño.

---

## 8. Extensión de VS Code

**No hay.** Burp es una aplicación de escritorio en Java y todo el trabajo ocurre
en su interfaz — que es el punto: el flujo de la sección 4 consiste en mirar
peticiones y reenviarlas a mano, y eso no cabe en un editor.

| | |
|---|---|
| Sitio | https://portswigger.net/burp |
| Descarga Community | https://portswigger.net/burp/communitydownload |
| Documentación | https://portswigger.net/burp/documentation |
| Formación gratuita | https://portswigger.net/web-security |

La última fila merece atención aparte: la **Web Security Academy** de PortSwigger
es gratuita, tiene laboratorios prácticos con vulnerabilidades reales que se
explotan con Burp, y cubre BOLA y control de acceso con más profundidad que
cualquier documentación de herramienta. Para una asignatura de Seguridad de
Sistemas es material de primera y no cuesta nada.

**Complemento dentro del editor:** para lanzar peticiones sueltas sin salir de
VS Code está `humao.rest-client`
(https://marketplace.visualstudio.com/items?itemName=humao.rest-client), que
ejecuta peticiones desde un fichero `.http`. No sustituye a Burp —no intercepta
tráfico ni tiene Repeater— pero para repetir una llamada cambiando el token es
suficiente, y los ficheros `.http` se pueden commitear como casos de prueba.

---

## 9. Pendientes

| | Estado |
|---|---|
| Instalación y certificado CA | Sin hacer |
| Dos usuarios de prueba con roles/jurisdicciones distintas | Sin crear |
| Sesión de pruebas BOLA sobre los endpoints de partes | Sin hacer |
| Repetir con `PATCH` y `DELETE` | Sin hacer |
| Escalada vertical sobre endpoints de administración | Sin hacer |
| Certificado en el dispositivo para la app móvil | Sin hacer |
