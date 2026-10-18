# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Dependency-free orthographic mesh and bone preview for rig mapping."""
import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QPixmap
from PySide6.QtWidgets import QWidget

from .rig import leg_deform_bones


class ModelPreview(QWidget):
    bonesPicked = Signal(list)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.setMinimumSize(280, 300)
        self.setMouseTracking(True)
        self.selected = None
        self.yaw = self.pitch = 0.0
        self.zoom = 1.0
        self.pan = QPointF()
        self.show_mesh = True
        self.mesh_cache = None
        self.press_pos = None
        self.dragged = False
        self.deform = set()
        for role in ('left_thigh', 'right_thigh', 'left_shin', 'right_shin'):
            self.deform.update(leg_deform_bones(model, role))
        points = [v.position for v in model.vertices] or [b.position for b in model.bones]
        if not points:
            points = [(0, 0, 0), (0, 1, 0)]
        lows = [min(p[a] for p in points) for a in range(3)]
        highs = [max(p[a] for p in points) for a in range(3)]
        self.center = tuple((lo + hi) / 2 for lo, hi in zip(lows, highs))
        self.extent = max(max(hi - lo for lo, hi in zip(lows, highs)), 1e-6)
        self.vertices = [self.normalized(v.position) for v in model.vertices]
        self.bones = [self.normalized(b.position) for b in model.bones]
        self.faces = []
        offset = 0
        for material in model.materials:
            if material.diffuse[3] > 0.001:
                self.faces.extend(tuple(model.indices[i:i+3])
                                  for i in range(offset, offset + material.count, 3))
            offset += material.count

    def normalized(self, point):
        return tuple((point[i] - self.center[i]) / self.extent for i in range(3))

    def projected(self, points):
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        scale = min(self.width(), self.height()) * .82 * self.zoom
        result = []
        for x, y, z in points:
            # PMX +X is the character's left; front view shows it on the right.
            rx, rz = x * cy + z * sy, -x * sy + z * cy
            ry, depth = y * cp - rz * sp, y * sp + rz * cp
            result.append((QPointF(self.width()/2 + self.pan.x() + rx*scale,
                                  self.height()/2 + self.pan.y() - ry*scale), depth))
        return result

    def invalidate(self):
        self.mesh_cache = None
        self.update()

    def reset_view(self):
        self.yaw = self.pitch = 0.0
        self.zoom = 1.0
        self.pan = QPointF()
        self.invalidate()

    def set_mesh_visible(self, visible):
        self.show_mesh = visible
        self.update()

    def select_bone(self, index):
        self.selected = index
        self.update()

    def resizeEvent(self, event):
        self.invalidate()
        super().resizeEvent(event)

    def render_mesh(self):
        # Cache the expensive mesh; highlighting only redraws the skeleton.
        pixmap = QPixmap(self.size())
        pixmap.fill(QColor('#101923'))
        painter = QPainter(pixmap)
        painter.setPen(Qt.PenStyle.NoPen)
        points = self.projected(self.vertices)
        faces = sorted(self.faces, key=lambda face: sum(points[i][1] for i in face), reverse=True)
        for face in faces:
            a, b, c = [points[i] for i in face]
            ux, uy, uz = b[0].x()-a[0].x(), b[0].y()-a[0].y(), b[1]-a[1]
            vx, vy, vz = c[0].x()-a[0].x(), c[0].y()-a[0].y(), c[1]-a[1]
            # Shade from the projected normal; depth uses the same screen scale.
            scale = min(self.width(), self.height()) * .82 * self.zoom
            uz *= scale; vz *= scale
            nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            light = abs((nx*.2 + ny*-.4 + nz*.9) / length) if length else .5
            shade = int(48 + min(light, 1) * 55)
            painter.setBrush(QColor(shade, shade+9, shade+18))
            painter.drawPolygon(QPolygonF([a[0], b[0], c[0]]))
        painter.end()
        self.mesh_cache = pixmap

    def paintEvent(self, event):
        if self.show_mesh and self.mesh_cache is None:
            self.render_mesh()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#101923'))
        if self.show_mesh:
            painter.drawPixmap(0, 0, self.mesh_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        points = self.projected(self.bones)
        for i, (point, _) in enumerate(points):
            color = QColor('#d7a767' if i in self.deform else '#68b8d8')
            color.setAlpha(125)
            painter.setPen(QPen(color, 1))
            parent = self.model.bones[i].parent
            if 0 <= parent < len(points):
                painter.drawLine(points[parent][0], point)
            painter.setBrush(color)
            painter.drawEllipse(point, 3, 3)
        if self.selected is not None and 0 <= self.selected < len(points):
            point = points[self.selected][0]
            painter.setPen(QPen(QColor('#ffdf65'), 3))
            parent = self.model.bones[self.selected].parent
            if 0 <= parent < len(points):
                painter.drawLine(points[parent][0], point)
            painter.setBrush(QColor('#ffdf65'))
            painter.drawEllipse(point, 6, 6)
            painter.drawText(QPointF(12, self.height()-16),
                             f'#{self.selected}  {self.model.bones[self.selected].name}')
        painter.setPen(QColor('#9caec1'))
        painter.drawText(QPointF(12, 22), '灰模预览 · 骨骼透视显示')
        painter.end()

    def pick_bones(self, position):
        points = self.projected(self.bones)
        hits = []
        for i, (point, depth) in enumerate(points):
            distance = math.hypot(point.x()-position.x(), point.y()-position.y())
            if distance <= 10:
                hits.append((distance, depth, i))
        # Prefer joint markers. Fall back to a parent connection segment.
        if not hits:
            for i, (point, depth) in enumerate(points):
                parent = self.model.bones[i].parent
                if not 0 <= parent < len(points): continue
                start = points[parent][0]
                dx, dy = point.x()-start.x(), point.y()-start.y()
                denom = dx*dx + dy*dy
                if denom < 1: continue
                t = max(0, min(1, ((position.x()-start.x())*dx + (position.y()-start.y())*dy)/denom))
                distance = math.hypot(position.x()-start.x()-t*dx, position.y()-start.y()-t*dy)
                if distance <= 5:
                    hits.append((distance, depth, i))
        return [i for _, _, i in sorted(hits)]

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.press_pos = self.last_pos = event.position()
            self.dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self.press_pos is None: return
        delta = event.position() - self.last_pos
        if (event.position() - self.press_pos).manhattanLength() > 4:
            self.dragged = True
        if self.dragged:
            if event.buttons() & Qt.MouseButton.RightButton:
                self.pan += delta
            else:
                self.yaw += delta.x() * .01
                self.pitch = max(-1.5, min(1.5, self.pitch + delta.y() * .01))
            self.invalidate()
        self.last_pos = event.position()

    def mouseReleaseEvent(self, event):
        if self.press_pos is not None and not self.dragged and event.button() == Qt.MouseButton.LeftButton:
            self.bonesPicked.emit(self.pick_bones(event.position()))
        self.press_pos = None

    def wheelEvent(self, event):
        self.zoom = max(.2, min(8, self.zoom * 1.15 ** (event.angleDelta().y()/120)))
        self.invalidate()
        event.accept()
