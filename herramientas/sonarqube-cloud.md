# SonarQube Cloud — SAST

> Categoría: análisis estático de código (SAST) · **Veredicto: viable y prioritaria**
> Índice: [README.md](./README.md) · Origen: [ci-cd-y-herramientas.md](../ci-cd-y-herramientas.md) §4

---

## 1. Qué hace

Lee el código fuente **sin ejecutarlo** y busca patrones conocidos de bug,
vulnerabilidad y *code smell*. Trabaja sobre el árbol sintáctico y sobre el flujo
de datos: puede seguir un valor desde que entra por un parámetro de un
controlador hasta que se concatena en una consulta SQL, y marcar el camino.

```
código fuente  →  parser  →  reglas + análisis de flujo  →  hallazgos
```

No ejecuta la aplicación, no necesita entorno, no necesita base de datos. Por eso
corre en cualquier push en dos minutos.

---

## 2. Viabilidad para Seguridad de Sistemas

**Sí, sin reservas.** Es la herramienta de seguridad de más bajo coste de entrada
de todo el inventario: la cuenta ya existe, el plan gratuito sobra para el tamaño
del proyecto, y la integración es un solo job de GitHub Actions.

Lo que sí conviene entender es **qué no cubre**, porque el nombre "análisis de
seguridad" invita a confiar de más:

| Cubre | No cubre |
|---|---|
| Inyección SQL/NoSQL en código propio | Vulnerabilidades en dependencias (`node_modules`) |
| XSS por concatenación sin escapar | Errores de configuración del despliegue |
| Criptografía débil, aleatoriedad insegura | Endpoints sin guard **en tiempo de ejecución** |
| Secretos escritos a fuego en el código | Lógica de negocio rota (permisos mal pensados) |
| Rutas de datos sin validar | Puertos abiertos, red, contenedor |

El punto crítico: **con ~2.262 líneas propias frente a decenas de miles en
dependencias, el SAST mira la parte pequeña del problema.** Complementarlo con
SCA (Dependabot, `npm audit`) no es opcional.

---

## 3. Estado y límites de la cuenta

```
Organización   paredes-work
Plan           Free
Código actual  ~2.262 líneas  →  ~4,5% del límite
```

| | Free |
|---|---|
| Líneas de código **privado** | 50.000 |
| Líneas de código **público** | Ilimitadas |
| Miembros | 5 |

Un sistema terminado de este tipo suele quedar entre 15.000 y 30.000 líneas: el
plan gratuito basta. Si algún día se acerca al techo, poner un repo en público
deja de consumir cuota, y las migraciones de Prisma se pueden excluir desde
`sonar-project.properties`.

> El límite que se agota antes no es el de líneas, es el de **5 miembros**.

*(Cifras tomadas del documento original. Los planes de SonarSource cambian; conviene
verificarlas contra la página de precios antes de tomar una decisión que dependa de ellas.)*

---

## 4. Las cinco trampas del montaje

1. **Apagar el *Automatic Analysis*** en `Administration → Analysis Method`.
   Causa número uno de fallo: si queda encendido y además se ejecuta el scanner
   desde Actions, los dos análisis chocan.
2. **El token debe ser *User Token***. Con un *project token*, *global token* o
   *scoped organization token* la conexión se guarda, pero el binding falla
   después sin mensaje claro.
3. **`fetch-depth: 0`** en `actions/checkout`, o el análisis de *código nuevo*
   sale mal por trabajar sobre un clon superficial.
4. **La action es `SonarSource/sonarqube-scan-action`**. La antigua
   `sonarcloud-github-action` está deprecada.
5. **El proyecto debe existir en SonarQube Cloud antes de analizarlo.** La action
   analiza; no crea el proyecto.

Desde julio de 2026 los análisis requieren **Java 21 o superior**. La versión 7 de
la action ya lo trae embebido; los ejemplos antiguos que instalan Java 17 fallan.

---

## 5. Workflow

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  sonar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # trampa 3

      - uses: SonarSource/sonarqube-scan-action@v7   # trampa 4
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}    # trampa 2: User Token
```

Y `sonar-project.properties` en la raíz del repositorio:

```properties
sonar.organization=paredes-work
sonar.projectKey=paredes-work_modulo_policia_backend
sonar.sources=src
sonar.tests=test
sonar.exclusions=**/prisma/migrations/**,**/*.spec.ts
sonar.javascript.lcov.reportPaths=coverage/lcov.info
```

`sonar.javascript.lcov.reportPaths` solo sirve si el job de tests ha corrido
antes y ha dejado el `lcov.info`. Sin eso, la cobertura sale en 0% y el Quality
Gate puede bloquear por un motivo falso.

---

## 6. El Quality Gate es lo que convierte esto en un control

Un análisis que solo publica un informe en un panel que nadie abre no protege
nada. Lo que lo convierte en control es que **falle el pipeline**:

```yaml
      - uses: SonarSource/sonarqube-quality-gate-action@master
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

Con el gate por defecto (*Sonar way*), una vulnerabilidad nueva en código nuevo
rompe el build. Ese es el comportamiento que se quiere.

> **Ojo con el "código nuevo".** El gate por defecto solo evalúa lo que cambió.
> La deuda que ya existía no bloquea nada — es deliberado, para poder adoptar la
> herramienta en un proyecto en marcha sin quedar bloqueado el primer día. Pero
> significa que las vulnerabilidades **anteriores a la adopción no van a saltar
> solas**: hay que ir a mirarlas a mano una vez.

---

## 7. Vulnerabilities frente a Security Hotspots

SonarQube separa dos cosas que suelen confundirse:

- **Vulnerability** — la herramienta afirma que hay un fallo explotable. Se
  arregla.
- **Security Hotspot** — código *sensible al contexto* que necesita que un humano
  decida. Por ejemplo, un `Math.random()`: es un problema si genera un token de
  sesión, y no lo es si baraja una lista para una demo.

Los hotspots **no cuentan para el Quality Gate por defecto** y por eso se acumulan
sin que nadie los mire. Merece la pena revisarlos una vez y marcarlos como
revisados; a partir de ahí solo aparecen los nuevos.

---

## 8. SonarQube for IDE

Extensión de VS Code, distinta del análisis en CI. En *Connected Mode* sincroniza
las reglas del servidor con el editor, con lo que el hallazgo aparece al escribir
en vez de tres minutos después en el pipeline. Requiere el mismo tipo de *User
Token*. Sin conectar también funciona, con las reglas por defecto.

Es la diferencia entre corregir mientras se tiene el problema en la cabeza y
corregir después de un cambio de contexto. Vale la instalación.

---

## 9. Pendientes

| | Estado |
|---|---|
| Workflow de análisis | Falta |
| `sonar-project.properties` en los tres repos | Falta |
| Secret `SONAR_TOKEN` (User Token) | Falta |
| Quality Gate bloqueante con `needs:` antes del deploy | Falta |
| Revisión inicial de Security Hotspots | Falta |
| Connected Mode en VS Code | Falta |
