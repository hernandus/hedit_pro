# Timeline Rendering Architecture

## Contexto

La timeline de un NLE (Non-Linear Editor) es el componente más demandante a nivel de rendering de toda la aplicación.
Exige renderizado de alta frecuencia (actualizaciones de playhead a 60fps), manejo de miles de clips, waveforms de audio,
zoom horizontal continuo, y scroll bidireccional fluido.

Este documento describe la arquitectura de rendering elegida para Hedit Pro y las alternativas evaluadas.

---

## Alternativas Evaluadas

### Opción A — `QGraphicsView` / `QGraphicsScene` (descartada como arquitectura permanente)

Qt ofrece un sistema de scene graph con `QGraphicsView`, `QGraphicsScene` y `QGraphicsItem`.

**Ventajas:**
- Hit-testing, selección y drag & drop integrados.
- Zoom via `QGraphicsView.scale()` sin lógica manual.
- `DragMode.RubberBandDrag` built-in.

**Desventajas críticas para NLE:**
- `scene.clear()` destruye y recrea todos los `QGraphicsItem` en cada redibujado. Con 200+ clips y 8+ tracks, este es un loop O(n) ejecutado en cada zoom, click de playhead o cambio de estado.
- Cada `QGraphicsItem` tiene overhead propio (`QTransform`, z-order, hover tracking, flags) innecesario para elementos estáticos de fondo como los lanes de las pistas.
- El playhead requiere redibujado completo de la escena por cada frame de playback.
- `QGraphicsView.sizeHint()` propaga la altura del `sceneRect` al sistema de docks de Qt, generando constraints difíciles de anular (`sizeHint()` = 220px cuando `sceneRect.height()` = 220px).
- Waveforms de audio como `QGraphicsItem` custom son costosas de calcular en cada paint.

**Conclusión:** Viable para prototipos. No es la arquitectura óptima para un NLE completo con playback en tiempo real.

---

### Opción B — `QPainter` Directo sobre `QWidget` ✅ (arquitectura adoptada)

Un `QWidget` con `paintEvent()` custom que dibuja todo el contenido de la timeline directamente con `QPainter`.

**Ventajas:**
- **Sin escena de objetos**: No hay `QGraphicsItem` que crear, destruir o iterar. El `paintEvent()` dibuja solo lo que está en el viewport visible.
- **Frustum culling trivial**: Antes de dibujar cada clip, se verifica si está dentro del rectángulo visible (`clip.end_frame * ppf < scroll_x` → skip). Esto mantiene el rendimiento constante independientemente de cuántos clips haya fuera del viewport.
- **Playhead por dirty rect**: La actualización del playhead invalida solo dos columnas de píxeles (`update(QRect(phx-1, 0, 3, height))`), no toda la escena. Esto permite 60fps sin redibujado total.
- **Waveform caching**: Los picos de audio se precomputan como `list[float]` por clip y se cachean. El `paintEvent()` solo itera sobre ellos y llama a `drawLine()`.
- **Sin `sizeHint` inflado**: El `QWidget` puro retorna lo que se le indica. No hay overhead de `sceneRect` burbujando hacia el dock manager.
- **Zoom directo**: `x = frame * pixels_per_frame - scroll_x`. Sin matrices de transformación ni `QTransform`.

**Desventajas:**
- Hit-testing manual: `clip_at(x, y)` requiere calcular el índice de track y buscar el clip en el frame. Se resuelve con búsqueda O(log n) en clips ordenados por `start_frame`.
- Drag & drop manual: Se trackea en `mouseMoveEvent`. Más código pero control total.

**Conclusión:** Es la arquitectura estándar de NLEs basados en Qt. Es la que usan Kdenlive, Shotcut y OpenShot.

---

### Opción C — `QOpenGLWidget` (descartada)

Renderizado GPU directo con shaders.

- Útil para NLEs con thumbnails de video en tiempo real sobre cada clip (DaVinci Resolve).
- Complejidad muy alta (VAO/VBO, shaders GLSL).
- Innecesario para el nivel actual del proyecto. Se puede agregar como capa de optimización futura.

---

### Opción D — `QML` / Qt Quick (descartada)

Renderizado GPU-acelerado con delegates y `ListView` virtualizados.

- Animaciones de 60fps nativas.
- Mezclar QML con PySide6/Python tiene overhead de binding complejo.
- Requeriría reescribir toda la UI del proyecto.

---

## Arquitectura QPainter Adoptada

### Estructura de Clases

```
TimelineCanvasWidget (QWidget)
├── [header bar]         QFrame + QHBoxLayout
│   ├── timecode_display QLabel (00:00:00:00 cyan)
│   └── zoom buttons     QPushButton (+ / -)
├── [content area]       QHBoxLayout
│   ├── [left column]    QVBoxLayout
│   │   ├── ruler_spacer QFrame (RULER_H px, alinea con ruler)
│   │   └── headers_clip QWidget (clip container con scroll_y)
│   │       └── headers_container QWidget (suma de TrackHeaderWidgets)
│   │           ├── TrackHeaderWidget × N_VIDEO
│   │           ├── QFrame (separador azul 4px)
│   │           └── TrackHeaderWidget × N_AUDIO
│   └── [right column]   QVBoxLayout
│       ├── TimelineRulerWidget   (QPainter, RULER_H px fijo)
│       ├── TimelineTracksWidget  (QPainter, stretch=1)
│       ├── QScrollBar horizontal (hbar)
│       └── QScrollBar vertical   (vbar, visible solo si total_h > view_h)
```

### Constantes de Geometría

| Constante      | Valor | Descripción |
|----------------|-------|-------------|
| `TRACK_PITCH`  | 27px  | Altura total de cada pista (26px lane + 1px divider) |
| `LANE_H`       | 26px  | Altura útil del lane (contenido de clips) |
| `SEP_H`        | 4px   | Separador azul entre Video y Audio |
| `RULER_H`      | 20px  | Altura del ruler de timecode |
| `HEADER_AREA_W`| 140px | Ancho del panel izquierdo de Track Headers |

### Fórmulas de Coordenadas

```python
# Frame → posición X en widget
x_widget = int(frame * pixels_per_frame) - scroll_x

# Posición X en widget → frame
frame = int((x_widget + scroll_x) / pixels_per_frame)

# Índice de track Video desde Y en widget
track_idx = (y_widget + scroll_y) // TRACK_PITCH

# Índice de track Audio desde Y en widget
audio_y = y_widget + scroll_y - (n_video * TRACK_PITCH) - SEP_H
track_idx = audio_y // TRACK_PITCH

# Altura total del contenido (dinámica según tracks del modelo)
total_h = (n_video * TRACK_PITCH) + SEP_H + (n_audio * TRACK_PITCH)
```

### Sincronización de Scroll

El scroll vertical es compartido entre `TimelineTracksWidget` (canvas derecho) y `headers_container` (panel izquierdo).

- `vbar.valueChanged` → `tracks.set_scroll_y(v)` + `headers_container.move(0, RULER_H - v)`
- El panel de headers usa `move()` en lugar de scroll area, ya que es un widget de tamaño fijo posicionado dentro de su contenedor clip.

El scroll horizontal mueve solo el canvas derecho y el ruler:
- `hbar.valueChanged` → `tracks.set_scroll_x(v)` + `ruler.set_view_state(ppf, v)`

### Frustum Culling

En `TimelineTracksWidget.paintEvent()`:

```python
# Vertical (por track)
if ty + TRACK_PITCH < clip_rect.top() or ty > clip_rect.bottom():
    continue  # Track entero fuera de viewport

# Horizontal (por clip)
cx = frame_to_x(clip.start_frame)
cw = int(clip.duration * pixels_per_frame)
if cx + cw < clip_rect.left() or cx > clip_rect.right():
    continue  # Clip fuera de viewport horizontal
```

Esto garantiza que el costo de `paintEvent()` es proporcional al número de clips **visibles**, no al total de clips en la secuencia.

### Playhead por Dirty Rect

```python
def set_playhead(self, frame: int):
    old_x = self._frame_to_x(self.model.playhead_frame)
    self.model.playhead_frame = max(0, frame)
    new_x = self._frame_to_x(self.model.playhead_frame)
    # Solo invalida las columnas afectadas
    self.update(QRect(old_x - 1, 0, 3, self.height()))
    self.update(QRect(new_x - 1, 0, 3, self.height()))
```

Qt fusiona los dos `QRect` en un solo `paintEvent`. El `clip_rect` del evento cubre solo ~6px de ancho → prácticamente gratis a 60fps.

---

## Referencias

- Kdenlive timeline source: `src/timeline2/view/timelinewidget.cpp` (migró de QGraphicsView a QML en 2019)
- Shotcut timeline: `src/widgets/timelinewidget.cpp` (QPainter directo)
- Qt docs: [QWidget::paintEvent](https://doc.qt.io/qt-6/qwidget.html#paintEvent), [QPainter](https://doc.qt.io/qt-6/qpainter.html)
