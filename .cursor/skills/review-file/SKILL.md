---
name: review-file
description: >-
  Revisión de código archivo por archivo, de forma conversada: leer el archivo y sus usos,
  presentar hallazgos numerados con una recomendación, esperar la aprobación del usuario y solo
  entonces aplicar los cambios con TDD y commits pequeños. Úsalo cuando el usuario pida revisar un
  archivo o carpeta ("revisemos X", "qué ves en este archivo", "sigue con el siguiente archivo").
  NO aplica cambios por iniciativa propia.
---

# Revisión de código archivo por archivo

El usuario revisa el código él mismo, archivo por archivo, y usa esta conversación para decidir qué
cambiar. Tu trabajo es dar hallazgos concretos y verificados; la decisión es suya.

## Regla de oro

**No ejecutes nada hasta que el usuario lo ordene explícitamente.** Una pregunta ("¿es posible X?",
"¿qué ves?") se responde con hallazgos o con la verificación, no con ediciones. Si aprueba solo
algunos puntos, aplica solo esos. Si un punto exige una decisión de diseño, explícala y espera. Si no
entiende un porqué o un término, explícalo antes de seguir.

## Proceso

1. **Leer** el archivo completo y buscar dónde se usa (cada nombre público, importaciones, tests).
   Un hallazgo sin comprobar es una conjetura.
2. **Lo mecánico primero** (idioma de comentarios, nombres, tipado, constantes arriba, mover tipos):
   se hace y se commitea antes del análisis; no necesita aprobación punto por punto si el usuario ya
   lo pidió así.
3. **Presentar el resto** numerado, del más al menos importante: qué pasa, por qué importa (con
   evidencia: archivo y línea) y tu recomendación. Di cuáles harías ahora y cuáles son decisión del
   usuario. Sé honesto si el archivo está bien. Lo que corresponde a otro archivo se anota, no se
   arregla aquí.
4. **Esperar** la respuesta. Si el cambio es grande o toca varias capas: plan primero, luego ejecutar.
5. **Aplicar** lo aprobado en commits pequeños, uno por propósito, con TDD.
6. **Cerrar:** resumir qué se aplicó, qué se verificó y qué NO; anotar lo diferido (notas del repo o
   del usuario y memoria de seguimiento) y dejar el marcador de dónde sigue la revisión.

## Criterios (genéricos, valen para cualquier repo)

**Lenguaje y comentarios**
- Comentarios y docstrings en el idioma que fije el repo; los textos que ve el usuario final (mensajes
  de API, logs de operación, etiquetas) conservan su idioma de producto.
- Un comentario explica el **porqué** (decisión, trade-off, bug evitado), no repite el código. Sin
  referencias históricas ("fase F1", "antes hacía…"). Si el código cambia, el docstring cambia.
- Documenta cada campo de una clase en la clase, no en el docstring del módulo.

**Tipado y nombres**
- Tipado fuerte: nada de `dict` ni `Any` sueltos; `TypedDict`, `Protocol`, dataclasses o uniones
  precisas. Para JSON sin validar, `object` y estrechar. Parámetros solo de lectura, como `Mapping`.
- Un texto que solo admite unos pocos valores es un `Enum`, no un `Literal` ni un `str`: elimina las
  comparaciones con texto suelto y los ignores de tipado en los tests.
- Un identificador que es un UUID se tipa y se mapea como UUID (`uuid.UUID`, `as_uuid=True`) en todas las capas: dominio, puertos, repositorios, rutas y columnas. El texto es solo la forma de transporte (JSON, logs, mensajes) y se convierte en el borde que lo necesite; `as_uuid=False` solo si una columna lo exige y se documenta el porqué.
- Nombres descriptivos; una letra no pasa; sin dígitos. Un mismo concepto se llama igual en todas las
  capas, y los de una misma familia de tipos comparten prefijo. Antes de renombrar, mira si el repo ya
  tiene una convención para no inventar una tercera forma.
- Si un nombre promete algo que el código no hace, o dos nombres parecen hacer lo mismo, renómbralo.
- Atributos de instancia declarados a nivel de clase antes de `__init__`.
- Una variable por línea: nada de asignación múltiple de valores sin relación (`a, b = f(x), g(y)`); no gana eficiencia ni
  legibilidad. Desempaquetar lo que devuelve una función (`ancho, alto = medir()`) sí está bien. Es un hallazgo mecánico.

**Estructura**
- Un archivo no mezcla naturalezas (tipos puros, reglas, presentación, persistencia); sigue la
  convención del repo sobre dónde viven los tipos. Un mapeo que usan varias capas va al dominio si solo
  depende de tipos del dominio.
- Las constantes de módulo van arriba, después de los imports; excepción: la que se DERIVA de algo
  definido en el mismo módulo va después de esa definición.
- **Una sola fuente de verdad:** una regla, constante o longitud vive en un lugar. Busca copias (la
  misma búsqueda en tres sitios, el mismo número en dos capas, una columna más ancha que su regla), y
  **compáralas antes de unificar**: pueden haber divergido y esconder un bug (se reproduce con un
  test, se corrige y solo entonces se unifica). Si dos cosas deben mantenerse sincronizadas, documenta
  la dependencia en AMBOS lados. Lo que se puede derivar de otra definición se deriva.
- Si un tipo se guarda como texto "para evitar un import circular", el ciclo es la causa: se mueve el
  tipo puro y se tipa de verdad; la conversión a texto queda en el borde de persistencia.
- Código, imports y variables sin uso se eliminan. Un dato que se guarda pero nadie lee es un hallazgo:
  se buscan todos sus lectores y, si no hay, se registra para preguntarlo a quien decide (no se borra
  ni se inventa su significado).
- Lo exhaustivo se comprueba con el compilador (`match` + `assert_never`) cuando no cuesta legibilidad;
  si la tabla se lee mejor, se deja y un test exige que esté completa.
- Los invariantes se aplican en un solo punto (el constructor); un campo que se puede derivar de otro es
  una propiedad, no un campo que alguien pueda pasar inconsistente.
- Listas, no texto unido con separadores. Comprensiones para filtros (`filter` solo con función con
  nombre).
- Un valor que depende del reloj ("segundos transcurridos") no vive en la entidad: se guarda el hecho
  (cuándo empezó) y se deriva en el borde donde se muestra, con `now` explícito.

**Robustez**
- Una consulta trae solo las columnas que usa. Quien solo comprueba un estado no carga un cuerpo grande
  (JSON, texto largo, binarios): se selecciona el estado, o la columna pesada se declara diferida. Se
  revisan todas las consultas del archivo con esta pregunta.
- Un fallo con un elemento se registra y el procesamiento sigue con los demás. Se registra una vez,
  donde se maneja el error.
- **Un trabajo por lotes no se detiene por un elemento envenenado:** el fallo se captura POR ELEMENTO
  (`except Exception` con su comentario del porqué), se cuenta con su clase y su traza y se sigue; si cada
  corrida arranca desde el mismo punto, un solo elemento que lance algo imprevisto frenaría a todos los demás
  para siempre. Cada corrida deja un informe auditable (ids tratados, ids fallidos con su causa y por qué
  terminó: error o señal), y una pasada sin nada que hacer no deja archivo.
- **Un valor de configuración que significa «apagado»** (0, vacío) rechaza los negativos y todo valor que lo
  imite por error (un `-1` no apaga un trabajo); cuando apagarlo incumple algo (retención, seguridad) se dice
  con un aviso fuerte, no con una línea informativa. Una conversión de unidades no puede llevar un valor
  válido a 0 (techo, o validar el resultado).
- **Procesos de larga vida:** las tareas hermanas se lanzan con `TaskGroup`, no con `gather` (entrega el
  primer error y deja correr a las demás mientras el `finally` cierra los recursos que usan); la señal de
  parada (SIGTERM) se convierte en cancelación para dejar una línea de arranque y una de salida (sin ellas,
  un reinicio en bucle no deja rastro); el código de salida distingue «corrió con fallos», «no pudo correr» e
  «interrumpido», y se busca quién lo vigila antes de cambiarlo. Un error se registra UNA vez con su clase y
  su traza, no otra vez con el traceback crudo del intérprete.
- **Un parámetro opcional que cuesta algo si falta** (una URL que habilita una invalidación, un respaldo) se
  avisa en el log al faltar, diciendo qué pasa y cómo arreglarlo, y se documenta; no se deja vacío en
  silencio.
- Una validación de "no debería ocurrir" va en el constructor; los lectores de datos externos (BD,
  payloads) la ignoran con un `warning` para no tumbar todo por un dato dañado. Una función de
  autorización o permisos llamada sin nada que comprobar **deniega y registra un aviso**: nunca concede
  por omisión, ni siquiera a un rol con bypass.
- Un código muerto defensivo (un `try` que no puede dispararse) se quita cuando el dato ya llega
  validado; se comprueba dónde se valida antes de decidir.
- `except Exception` amplio solo con un comentario del porqué. Nunca desactivar alertas del analizador
  (`# NOSONAR`, `# noqa`, `pylint: disable`): se corrige la causa o se deja que la herramienta marque.
- Los instantes de registro los asigna la base de datos (`now()`), no la aplicación; se prueba abriendo
  una transacción, esperando y comprobando que el valor es el de su inicio. Las actualizaciones que
  compiten usan un `UPDATE` condicional atómico.
- **Todo acceso a datos pasa por el ORM** (modelos, `select`/`update` sobre el modelo, objetos cargados que se modifican). El SQL escrito a mano (`text(...)`), las sentencias de lote fuera del objeto cargado o un `upsert` de dialecto son una EXCEPCIÓN: se AVISA al usuario al revisar la tabla (con archivo y línea, para que revise por qué se hicieron así), se documenta en el código con el porqué y solo se admite sin avisar en las pruebas de restricciones y en la semilla de una migración. Las funciones de la base (candados, agregados) se llaman con `func`, no con `text`.
- **Quién escribe cada columna de auditoría:** los instantes (`created_at`, `updated_at`, `revoked_at`, `last_used_at`…) los pone SOLO la base con `now()`: nadie los pone ni los simula (ni un valor de relleno en una entidad). El actor (`created_by`/`updated_by`) lo pone el ORM desde la sesión (un oyente de la clase base), no cada repositorio; una columna que no cuenta como edición (marcar el uso) se declara exenta en el modelo.
- Si los datos tienen dueño o ámbito (inquilino, cuenta, equipo), la restricción de acceso la impone la
  capa de datos con una sola consulta (un `JOIN` que incluya al dueño), no el llamador encadenando
  búsquedas; se prueba con un test por nivel usando el id de otro dueño.
- Un conflicto de datos (código repetido, recurso en uso) es un error de dominio con su 409; la
  integridad de "no borrar lo que está en uso" la impone la base (`RESTRICT`), no solo una comprobación
  previa.
- Un secreto nunca aparece en `repr`, logs ni trazas. Nada de métricas, umbrales ni pesos literales si el
  repo exige que vivan en la configuración; los valores de configuración que alimentan un cálculo se
  validan donde nacen para que fallen al arrancar, no en silencio.
- Un estimado que ya no se sostiene se declara "sin estimado" (`None`), no se recorta a un valor inventado.
- Todo `add_*` devuelve lo guardado (con lo que la base resuelve), igual que `update_*`; si entrada y
  salida tienen campos distintos, son dos tipos, sin opcionales que signifiquen "aún no se leyó".

**Contrato y datos**
- Lo que cambia un contrato (API, base de datos, mensajes) se dice antes de hacerlo.
- Una migración sobre datos reales se prueba subiendo, bajando y subiendo, con datos viejos; si el
  proyecto no está en producción se pueden estrechar columnas y simplificar migraciones.

**Bugs encontrados y no corregidos al momento**
- Se registran en un archivo de bugs del repo con código (`BUG-NNN`), estado, ejemplo reproducido e
  impacto; la función afectada lleva `TODO(BUG-NNN)` mientras esté pendiente, y si el código se mueve, el
  TODO y el registro se actualizan en el mismo commit. Los ya registrados NO cuentan como pendientes de
  la revisión ni se vuelven a proponer, salvo que la corrección caiga de forma natural en el cambio.

## Cómo aplicar los cambios

- **TDD:** test primero, verlo fallar por la razón correcta, luego el mínimo. Comprueba que no pasa por
  casualidad (por ejemplo, quitando lo que prueba y viendo que falla).
- **Lo que un comentario afirma de una librería se comprueba con un guion mínimo** antes de escribirlo o de
  creerlo: un comentario falso sobre el comportamiento de `gather`, de un reintento o de una caché es un bug
  que nadie busca.
- **Todo flujo con tiempo** (esperas, bucles, relojes) recibe `sleep`/reloj por parámetro y se prueba;
  «las pruebas no lo ejecutan» no es una razón si se puede inyectar. Sin `type: ignore`, `noqa` ni
  `pragma: no cover`: lo que no se ejecuta se queda sin cobertura, con un comentario del porqué.
- **Mutaciones:** se rompe a propósito lo que prueba cada prueba; si la mutación sobrevive, o la prueba no
  discrimina (se afina con otro caso: una excepción distinta de la capturada, un orden entrecruzado) o el
  código es redundante (se elimina). Se corren con `timeout` y una copia de respaldo del archivo.
- **Si el cambio toca el arranque o la parada, se verifica con el proceso real:** se lanza con `exec`, se le
  manda la señal por su PID y los procesos se buscan con un filtro exacto; nunca `pkill -f`/`pgrep -f` con un
  texto que también aparece en tu propia línea de comandos (mata tu shell).
- **Un cambio de estructura** (dividir un archivo, mover un paquete) se hace primero sin cambiar
  comportamiento, con el mismo número de pruebas antes y después y los importadores reescritos por script; las
  correcciones van en commits aparte y la documentación al final.
- Cambios masivos (renombres, mover imports) con un script sobre el árbol sintáctico (`ast`/tokens), no
  sobre texto ni a mano; luego repasar comentarios y documentación, y correr formateador, linter, tipos y
  tests, **leyendo el resultado del linter antes de commitear**.
- Antes de cada commit, lo que el repo exija (linter, formato, tipos, pruebas unitarias y de
  integración). Las de integración usan una base descartable, nunca la de desarrollo; bórrala al terminar
  y deja los contenedores como estaban.
- Commits en el formato e idioma del repo (su `CLAUDE.md` y el del usuario), respetando sus reglas de
  coautoría. Actualiza la documentación que el cambio toque (changelog, arquitectura, README).
- No hagas `push` ni toques archivos personales del usuario (notas, ideas) salvo para **añadir** lo que
  él pida.

## Criterios propios de cada repo y aprendizaje

Las convenciones específicas (dónde viven los tipos, comandos de verificación, reglas de commits) se leen
del `CLAUDE.md` del repo, de la memoria del proyecto y del contexto; no las inventes ni las copies aquí.
Un criterio nuevo y **general** aparecido en la conversación se integra en su categoría de arriba (con
ejemplos genéricos, nunca nombres del repo); uno específico de un repo va al `CLAUDE.md` de ese repo.
