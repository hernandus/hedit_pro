# Qt Docking — Problema de Resize en BottomDockWidgetArea

**Fecha:** 2026-07-30  
**Contexto:** Hedit Pro — Sistema de docking estilo Premiere Pro  
**Archivo de prueba:** `test_docking.py`

---

## Síntoma

El panel de Timeline, ubicado en `Qt.BottomDockWidgetArea` con full-width horizontal, **no podía ser redimensionado verticalmente**. Al intentar arrastrar el separador entre la fila superior de paneles y el Timeline, el separador no respondía o volvía inmediatamente a su posición.

Además, cuando el dock inferior se agregaba sin un `centralWidget()` definido, **tomaba todo el espacio vertical disponible** desde el inicio, aplastando los paneles superiores.

---

## Metodología de diagnóstico

Se construyó un script de prueba paralelo (`test_docking.py`) que replicaba el sistema de docking **sin contenido real**, para aislar el problema capa por capa:

| Iteración | Configuración | Resultado |
|---|---|---|
| 1 | 2 paneles: Left + Right | ✅ Resize libre en ambos |
| 2 | 3 paneles: Left + Right + Bottom (sin `setCentralWidget`) | ❌ Bottom toma todo el espacio, sin resize |
| 3 | 3 paneles + `setCentralWidget(QWidget())` con `setMinimumSize(0,0)` | ✅ Resize funciona |
| 4 | Todos los docks en `LeftDockWidgetArea` + `setFixedSize(0,0)` en central | ❌ Resize roto nuevamente |
| 5 | Todos los docks en `LeftDockWidgetArea` + `setMinimumSize(0,0)` en central | ✅ Resize funciona, sin "stage" visible |

**Conclusión del diagnóstico:** el problema es **nativo de Qt 6**, no del código del proyecto. Se reproduce con `QDockWidget` puro, sin QSS, sin subclases, sin nada extra.

---

## Causa raíz

### Por qué el bottom dock no se podía redimensionar

`QMainWindow` internamente usa `QMainWindowLayout` + `QDockAreaLayout` para distribuir el espacio entre las áreas de dock y el widget central.

Cuando se agrega un dock en `Qt.BottomDockWidgetArea` **sin un `centralWidget()`**, Qt no tiene un elemento de referencia flexible para el eje vertical. El resultado es que el layout trata todo el espacio disponible como perteneciente al dock inferior, impidiendo que el separador sea arrastrable.

```
Sin centralWidget():

┌─────────────────────────────────┐
│   Fila superior (docks)         │  ← comprimida
├─────────────────────────────────┤
│                                 │
│   BottomDockWidgetArea          │  ← toma todo
│                                 │
└─────────────────────────────────┘
```

### Por qué `setFixedSize(0, 0)` también rompe el resize

Cuando se intentó ocultar el central widget usando `setFixedSize(0, 0)`, el resize volvió a romperse.

La razón: `QMainWindowLayout` necesita poder **ajustar la altura del central widget** como buffer cuando el usuario arrastra el separador vertical. A este mecanismo lo llamamos "slack vertical".

- `setFixedSize(0, 0)` → el central widget es rígido, no puede cambiar de tamaño → el layout no tiene dónde "absorber" el delta del drag → el separador no responde.
- `setMinimumSize(0, 0)` (sin fijar el máximo) → el central widget puede crecer como buffer → el drag funciona correctamente.

```
Con setCentralWidget(dummy) y setMinimumSize(0, 0):

┌─────────────────────────────────┐
│   Fila superior (docks)         │
├───────┬─────────────────────────┤
│ dummy │  ← absorbe el delta     │  ← "slack vertical"
│  0px  │    al arrastrar         │
├───────┴─────────────────────────┤
│   BottomDockWidgetArea          │  ← se puede achicar
└─────────────────────────────────┘
```

### Por qué aparecía el "stage" (central widget visible entre paneles)

Cuando algunos docks estaban en `Qt.LeftDockWidgetArea` y otros en `Qt.RightDockWidgetArea`, Qt colocaba el central widget **entre ambas áreas**:

```
Left area | [central widget visible] | Right area
```

La solución fue agregar **todos** los docks superiores a `Qt.LeftDockWidgetArea` y splitearlos horizontalmente con `splitDockWidget()`, replicando exactamente el patrón de `main_window.py`. Al no haber docks en `RightDockWidgetArea`, el central widget queda comprimido a 0px de ancho de forma natural.

---

## Solución

Dos reglas que deben cumplirse simultáneamente:

### Regla 1 — Siempre definir un `centralWidget()`

```python
dummy = QWidget()
dummy.setMinimumSize(0, 0)   # ← mínimo 0px
# NO usar setFixedSize ni setMaximumSize
self.setCentralWidget(dummy)
```

### Regla 2 — Todos los docks superiores en el mismo área, spliteados horizontalmente

```python
self.addDockWidget(Qt.LeftDockWidgetArea, dock_A)
self.splitDockWidget(dock_A, dock_B, Qt.Horizontal)
self.splitDockWidget(dock_B, dock_C, Qt.Horizontal)
self.splitDockWidget(dock_C, dock_D, Qt.Horizontal)
# NO usar Qt.RightDockWidgetArea para docks de la fila superior
```

### Regla 3 — Las esquinas inferiores deben asignarse a `BottomDockWidgetArea`

```python
self.setCorner(Qt.BottomLeftCorner,  Qt.BottomDockWidgetArea)
self.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
```

Esto garantiza que el dock inferior ocupe el ancho completo de la ventana.

---

## Aplicación a `main_window.py`

La producción (`main_window.py`) actualmente **no tiene `setCentralWidget()`**. Funciona porque los widgets reales (`TimelineCanvasWidget`, `SourceMonitorWidget`, etc.) tienen `sizeHint()` no triviales que proveen el slack vertical implícitamente.

Sin embargo, si se agregan docks con contenido más liviano o se modifica el layout, el problema puede reaparecer. La recomendación es **agregar el central widget dummy** también en `main_window.py` para hacer el comportamiento explícito y robusto.

---

## Archivos relevantes

| Archivo | Rol |
|---|---|
| `test_docking.py` | Script de prueba aislado donde se reprodujo y resolvió el problema |
| `gui/main_window.py` | Ventana principal — candidata a recibir el fix |
| `gui/widgets/timeline/canvas.py` | `TimelineCanvasWidget` — tiene `CompactDockWidget` y `setMinimumHeight` que afectaban el resize |
| `run_test.sh` | Launcher del script de prueba |
