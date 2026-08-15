# Gitleaks — detección de secretos

> Categoría: escaneo de secretos en el repositorio · **Veredicto: viable, coste casi nulo**
> Índice: [README.md](./README.md) · Relacionadas: [github-actions.md](./github-actions.md) · [easypanel.md](./easypanel.md)

---

## 1. Qué hace

Busca secretos —claves de API, tokens, contraseñas, claves privadas— escritos
dentro del repositorio, incluido **todo el historial de git**.

Es de los controles con mejor relación valor/esfuerzo del inventario: se instala
en minutos y ataja una de las formas más comunes y más silenciosas de filtrar
credenciales.

---

## 2. Cómo funciona

Combina dos técnicas complementarias:

**Reglas por patrón.** Unas 150 expresiones regulares para formatos conocidos y
reconocibles: claves de AWS (`AKIA...`), tokens de GitHub (`ghp_...`), claves
privadas PEM, cadenas de conexión, JWTs. Precisión alta, casi sin falsos
positivos.

**Entropía de Shannon.** Para lo que no tiene formato fijo. Una cadena como
`8f3d9a2b1c7e4f0a` tiene aleatoriedad mucho más alta que texto o código normal, y
eso la delata aunque no coincida con ningún patrón. Aquí es donde aparecen los
falsos positivos: hashes de commits, sumas de verificación, ficheros minificados.

Se configura en `.gitleaks.toml`, con reglas propias y lista de permitidos:

```toml
[extend]
useDefault = true

[[rules]]
id = "easypanel-hook"
description = "Deploy hook de EasyPanel"
regex = '''https://[a-z0-9.-]+/api/deploy/[A-Za-z0-9_-]{20,}'''

[allowlist]
paths = ['''package-lock\.json''', '''\.spec\.ts$''']
```

---

## 3. Los dos modos

```bash
gitleaks detect --source . --verbose    # recorre TODO el historial
gitleaks protect --staged               # solo lo que vas a commitear
```

| | `detect` | `protect` |
|---|---|---|
| Alcance | Todos los commits, todas las ramas | Cambios sin commitear |
| Velocidad | Segundos a minutos | Instantáneo |
| Dónde va | CI | Hook de pre-commit |

**Se usan los dos.** El hook da velocidad —te para antes de que el secreto entre
en la historia— pero es evitable con `--no-verify` y depende de que cada persona
lo tenga instalado. El CI no es evitable. Ninguno de los dos sustituye al otro.

---

## 4. El detalle que casi todo el mundo pasa por alto

**Escanea el historial completo, y ese es el punto.**

Un secreto que se subió el martes y se borró el miércoles **sigue en el
repositorio**. Está en el objeto de aquel commit, y cualquiera que clone lo tiene.
El archivo actual está limpio; la credencial está filtrada igual.

De ahí la regla operativa: **cuando Gitleaks encuentra algo, la respuesta es
rotar la credencial, no borrar la línea.**

```
Encontrado un secreto en el historial
        ↓
1. Rotar / regenerar la credencial          ← esto es lo que resuelve
2. Quitarlo del código actual
3. Reescribir el historial                  ← opcional, y llega tarde
```

El paso 3 (`git filter-repo`, BFG) es incómodo, obliga a reescribir ramas y
**no sirve de nada si el repositorio ya se clonó o si es público**. Sirve para
higiene, no para contención. Lo que contiene es el paso 1.

---

## 5. En el pipeline

```yaml
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # sin esto solo ve el último commit
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`fetch-depth: 0` es obligatorio y es el error de montaje número uno: con el clon
superficial por defecto, Gitleaks solo mira el commit más reciente y el escaneo
sale limpio siempre.

Y el hook local:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

---

## 6. Qué esperar en la primera pasada

En un proyecto que lleva tiempo andando, lo habitual es que salga algo. Los
sospechosos frecuentes en un stack como este:

- `DATABASE_URL` completa en un `.env.example` que se rellenó "para probar"
- Un `JWT_SECRET` en un fichero de tests
- La URL del deploy hook de EasyPanel pegada en un README o en un script
- Credenciales en capturas de pantalla o en `docker-compose.yml`

El caso del hook merece atención especial aquí: en
[github-actions.md](./github-actions.md) quedó pendiente verificar si el secret
`EASYPANEL_DEPLOY_HOOK_1` viene heredado de otro proyecto. Una regla propia para
ese formato de URL responde a la mitad de la pregunta en una pasada.

---

## 7. Lo que no cubre

- **Secretos que nunca tocaron git.** Los que están solo en el panel de EasyPanel
  o en la máquina de alguien. Correcto: ese es su sitio.
- **Secretos con formato de texto normal.** Una contraseña como `Comisaria2024`
  no tiene entropía alta ni patrón reconocible. Ninguna herramienta la detecta.
- **Secretos ya filtrados fuera del repo.** En un log, en un chat, en una
  captura.

Es un control de una vía de fuga concreta, no una garantía de que no haya
secretos sueltos.

---

## 8. Pendientes

| | Estado | Prioridad |
|---|---|---|
| Job de Gitleaks en CI con `fetch-depth: 0` | No existe | **Alta** |
| Primera pasada sobre el historial de los tres repos | Sin hacer | **Alta** |
| Rotar lo que aparezca | Pendiente del anterior | Alta |
| Regla propia para las URLs de deploy hook | Sin escribir | Media |
| Hook de pre-commit | No existe | Baja |
| `.gitleaks.toml` con lista de permitidos | Sin escribir | Baja |
