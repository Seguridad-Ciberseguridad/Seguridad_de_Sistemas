# Hash vs Cifrado — diferencias, usos y objetivos

> Categoría: criptografía aplicada · Mes 1 — Semana 3
> Relacionado: [flujo-cia-aaa-telegram-archivos.md](../Automatizaciones/flujo-cia-aaa-telegram-archivos.md)
> Scripts que lo hacen tangible: `hash_lab.py` · `crypto_lab.py`

---

## 1. La diferencia fundamental

Son dos herramientas distintas que resuelven problemas distintos. Confundirlas es uno de los errores más comunes y más peligrosos en seguridad.

| | Hash | Cifrado |
|---|---|---|
| ¿Qué hace? | Genera una huella digital de longitud fija | Transforma datos para que solo quien tenga la clave pueda leerlos |
| ¿Es reversible? | ❌ No — irreversible por diseño | ✅ Sí — con la clave correcta |
| ¿Necesita clave? | ❌ No | ✅ Sí |
| ¿Mismo input = mismo output? | ✅ Siempre | Depende del modo y del IV |
| Propiedad CIA que protege | Integridad | Confidencialidad |
| Pregunta que responde | ¿Este dato fue modificado? | ¿Solo el destinatario correcto puede leer esto? |

---

## 2. Qué es un hash

Una función hash toma cualquier input (un archivo, una contraseña, un mensaje) y produce una cadena de longitud fija llamada **digest** o **huella**.

### Propiedades que debe cumplir un hash criptográfico

| Propiedad | Qué significa |
|---|---|
| Determinista | El mismo input siempre produce el mismo output |
| Efecto avalancha | Un cambio mínimo en el input cambia completamente el output |
| Irreversibilidad | No se puede reconstruir el input a partir del output |
| Resistencia a colisiones | Dos inputs distintos no deben producir el mismo hash |
| Velocidad | Debe ser rápido de calcular (excepto en hashes de contraseñas, donde se busca lo contrario) |

### Ejemplo del efecto avalancha con SHA-256

```
Input:  "hola"
Hash:   b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79

Input:  "Hola"  ← solo cambió la mayúscula
Hash:   0a042430b1b549d6e3b84e9a4e3e6e0e3e6e0e3e6e0e3e6e0e3e6e0e3e6e0e3
```

El output cambia completamente. Eso es el efecto avalancha.

### Para qué sirve un hash

| Uso | Cómo funciona | Ejemplo real |
|---|---|---|
| Verificar integridad de archivos | Calculas el hash antes y después — si coincide, no fue modificado | Git usa SHA-1/SHA-256 para cada commit |
| Verificar integridad en tránsito | El servidor publica el hash del archivo descargable | ISOs de Linux con su SHA-256 |
| Firmas digitales | Se firma el hash del mensaje, no el mensaje completo | TLS, certificados X.509 |
| Almacenar contraseñas | Se guarda el hash, nunca la contraseña en claro | Bases de datos de usuarios |
| Blockchain | Cada bloque contiene el hash del anterior — cadena inalterable | Bitcoin, Ethereum |

---

## 3. Qué es el cifrado

El cifrado transforma datos legibles (plaintext) en datos ilegibles (ciphertext) usando una clave. Solo quien tenga la clave correcta puede revertir el proceso.

### Dos tipos de cifrado

#### Simétrico — misma clave para cifrar y descifrar

```
Alice cifra con clave K → ciphertext → Bob descifra con la misma clave K
```

| Algoritmo | Estado | Por qué |
|---|---|---|
| **AES-256-GCM** | ✅ Estándar actual | Cifra + autentica la integridad simultáneamente |
| AES-256-CBC | ⚠️ Aceptable con HMAC | Cifra pero no autentica — vulnerable a ataques de padding |
| ChaCha20-Poly1305 | ✅ Muy seguro | Alternativa moderna, mejor en hardware sin aceleración AES |
| DES / 3DES | ❌ Obsoleto | Clave demasiado corta, roto en la práctica |
| RC4 | ❌ Roto | Vulnerabilidades conocidas, prohibido en TLS |

**Problema del simétrico:** ¿cómo compartes la clave de forma segura con el destinatario?

#### Asimétrico — clave pública para cifrar, clave privada para descifrar

```
Alice cifra con la clave PÚBLICA de Bob → ciphertext → Bob descifra con su clave PRIVADA
```

| Algoritmo | Estado | Uso principal |
|---|---|---|
| **RSA-4096** | ✅ Seguro | Intercambio de claves, firmas digitales |
| RSA-2048 | ✅ Aceptable hoy | Mínimo recomendado actualmente |
| RSA-1024 | ❌ Roto | No usar |
| **ECDSA / Ed25519** | ✅ Moderno | Firmas digitales, SSH, TLS moderno |
| **ECDH** | ✅ Moderno | Intercambio de claves (reemplaza RSA para ese uso) |

**Problema del asimétrico:** es mucho más lento que el simétrico.

#### La solución real — cifrado híbrido

En la práctica nunca se usa uno solo. Se combinan:

```
1. Se genera una clave AES aleatoria (clave de sesión)
2. Se cifra el archivo con AES-256-GCM (rápido)
3. Se cifra la clave AES con RSA-4096 del destinatario (seguro para el intercambio)
4. Se envían juntos: archivo cifrado + clave cifrada
```

Así funciona TLS, PGP/GPG y el cifrado de WhatsApp.

---

## 4. Hash de contraseñas — por qué SHA-256 no es suficiente

SHA-256 es demasiado rápido. Un atacante con una GPU moderna puede probar **10.000 millones de hashes SHA-256 por segundo**. Eso hace que un diccionario de contraseñas comunes se rompa en segundos.

### Los algoritmos correctos para contraseñas

#### bcrypt — el estándar probado
- Diseñado en 1999 específicamente para contraseñas
- Factor de coste ajustable: `rounds=12` significa 2¹² iteraciones
- Incluye salt automático — dos usuarios con la misma contraseña tienen hashes distintos
- Lento por diseño: ~100ms por verificación hace inviable la fuerza bruta

```python
import bcrypt
hash = bcrypt.hashpw(b"micontraseña", bcrypt.gensalt(rounds=12))
# Verificar
bcrypt.checkpw(b"micontraseña", hash)  # True
```

#### Argon2id — el más recomendado hoy
- Ganó el Password Hashing Competition (2015)
- Recomendado por OWASP como primera opción
- Resistente a ataques con GPU y hardware especializado (ASIC)
- Costoso en memoria además de en CPU — hace inviables los ataques paralelos
- Variante **Argon2id** combina resistencia a ataques de canal lateral y de GPU

```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
hash = ph.hash("micontraseña")
ph.verify(hash, "micontraseña")  # True
```

#### scrypt — alternativa sólida
- Costoso en memoria, diseñado para resistir hardware especializado
- Usado en derivación de claves de Bitcoin
- Argon2id lo supera en la mayoría de casos modernos

### Comparativa de velocidad (por qué importa)

| Algoritmo | Hashes/segundo en GPU moderna | Tiempo para romper "password123" |
|---|---|---|
| SHA-256 | 10.000.000.000 | Milisegundos |
| MD5 | 50.000.000.000 | Instantáneo |
| bcrypt (rounds=12) | 10.000 | Horas |
| Argon2id | 1.000 | Días o imposible |

---

## 5. El concepto de salt

Un salt es un valor aleatorio que se añade al input antes de hashear. Resuelve dos problemas:

**Problema 1 — Rainbow tables:** tablas precalculadas de hash → contraseña. Con salt, cada hash es único aunque la contraseña sea la misma.

**Problema 2 — Dos usuarios con la misma contraseña tienen el mismo hash:**

```
Sin salt:
  usuario1: SHA256("1234") = 03ac674...
  usuario2: SHA256("1234") = 03ac674...  ← idéntico, se detecta

Con salt:
  usuario1: SHA256("1234" + "x7k2p") = a9f3c1...
  usuario2: SHA256("1234" + "m8q4r") = 7b2e9d...  ← distintos
```

bcrypt y Argon2id incluyen el salt automáticamente en el hash resultante — no necesitas gestionarlo tú.

---

## 6. Tabla de decisión — qué usar en cada caso

| Necesidad | Herramienta correcta | Por qué |
|---|---|---|
| Verificar que un archivo no fue modificado | SHA-256 | Rápido, estándar, irreversible |
| Guardar una contraseña en base de datos | Argon2id o bcrypt | Lentos por diseño, con salt |
| Cifrar un archivo para almacenarlo | AES-256-GCM | Rápido, cifra y autentica |
| Cifrar un mensaje para un destinatario específico | AES-256-GCM + RSA-4096 | Híbrido: velocidad + seguridad en el intercambio |
| Firma digital de un documento | SHA-256 + RSA o Ed25519 | Se firma el hash, no el documento completo |
| Verificar integridad Y autenticidad | HMAC-SHA256 o AES-GCM | HMAC añade una clave al hash — no cualquiera puede generarlo |
| Contraseña de base de datos / secreto de aplicación | Variable de entorno + gestor de secretos | No se hashea ni cifra en el código — no debe estar en el código |

---

## 7. Errores comunes que cuestan caro

| Error | Consecuencia | Corrección |
|---|---|---|
| Guardar contraseñas con SHA-256 sin salt | Rompible con rainbow tables en segundos | Usar Argon2id o bcrypt |
| Usar MD5 para integridad de archivos | MD5 tiene colisiones conocidas — dos archivos distintos pueden tener el mismo hash | Usar SHA-256 o SHA-3 |
| Usar AES-CBC sin HMAC | Vulnerable a ataques de padding oracle | Usar AES-GCM que autentica automáticamente |
| Confundir hash con cifrado | Intentar "descifrar" un hash o usar cifrado donde se necesita integridad | Entender qué propiedad CIA necesitas primero |
| RSA para cifrar archivos grandes directamente | RSA es lento y tiene límite de tamaño | Cifrado híbrido: AES para el archivo, RSA para la clave |
| Generar el IV/nonce de AES de forma predecible | Rompe la seguridad del cifrado aunque la clave sea fuerte | IV siempre aleatorio con `os.urandom()` |

---

## 8. Cómo aparecen en el flujo CIA+AAA de Telegram

| Nodo del flujo | Herramienta | Propiedad que protege |
|---|---|---|
| Calcular huella del archivo | SHA-256 | Integridad |
| Comparar con hash anterior | SHA-256 | Detección de violación de integridad |
| Cifrar el archivo antes de guardarlo | AES-256-GCM | Confidencialidad |
| Verificar que el archivo cifrado no fue manipulado | AES-256-GCM (autenticación integrada) | Integridad + Autenticidad |

SHA-256 y AES-256-GCM no se solapan — cada uno hace una cosa distinta y ambas son necesarias.

---

## 9. Scripts del Mes 1 que implementan estos conceptos

| Script | Qué demuestra |
|---|---|
| `hash_lab.py` | Efecto avalancha · salt · comparativa SHA-256 vs bcrypt vs Argon2id |
| `crypto_lab.py` | César/XOR → AES-256-GCM → RSA · cifrado híbrido · GPG en Kali |

---

*Documento creado el 2026-08-21 — Mes 1, Semana 3, concepto de criptografía aplicada.*
