from PyQt5.QtWidgets import QOpenGLWidget
import numpy as np
from OpenGL.GL import *
import time
# Try to import metalgpu for Metal integration (pip install metalgpu)
try:
    import metalgpu as mg
    METALGPU_AVAILABLE = True
except ImportError:
    METALGPU_AVAILABLE = False



class SimulationGLWidget(QOpenGLWidget):
    def __init__(self, G, pos, parent=None):
        super().__init__(parent)
        self.G = G
        self.pos = pos
        self.simState = {}
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.zoom = 1.0

        self.min_x = min(p[0] for p in pos.values())
        self.max_x = max(p[0] for p in pos.values())
        self.min_y = min(p[1] for p in pos.values())
        self.max_y = max(p[1] for p in pos.values())
        self.setMinimumSize(800, 600)

        edges_list = []
        for u, v in G.edges():
            edges_list.extend([pos[u][0], pos[u][1], pos[v][0], pos[v][1]])
        self.edges = np.array(edges_list, dtype=np.float32)
        self.edge_vbo = None

        self.node_list = sorted(list(pos.keys()))
        self.node_to_index = {node: i for i, node in enumerate(self.node_list)}
        self.node_positions = np.array([pos[node] for node in self.node_list], dtype=np.float32)
        self.node_vbo = None
        self.node_color_vbo = None
        self.node_colors = np.full((len(self.node_list), 3), 0.3, dtype=np.float32)

        # Initialize Metal GPU for animation handling (if available)
        if METALGPU_AVAILABLE:
            self.mg_device = mg.Interface()  # Initialise the Metal instance
            # A simple kernel that computes a pulse factor using sin(time)
            kernel_code = """
            #include <metal_stdlib>
            using namespace metal;
            kernel void pulse(const device float* timeVal,
                              device float* outVal,
                              uint id [[thread_position_in_grid]]) {
                if (id == 0) {
                    outVal[0] = sin(timeVal[0]);
                }
            }
            """
            self.mg_device.load_shader_from_string(kernel_code)
            self.mg_device.set_function("pulse")
        else:
            self.mg_device = None

    def updateProjection(self):
        aspect = self.width() / self.height() if self.height() > 0 else 1
        center_x = ((self.min_x + self.max_x) / 2.0) + self.pan_offset_x
        center_y = ((self.min_y + self.max_y) / 2.0) + self.pan_offset_y
        half_width = (self.max_x - self.min_x) / 2.0 * self.zoom
        half_height = (self.max_y - self.min_y) / 2.0 * self.zoom
        if half_width / half_height < aspect:
            half_width = half_height * aspect
        else:
            half_height = half_width / aspect
        left = center_x - half_width
        right = center_x + half_width
        bottom = center_y - half_height
        top = center_y + half_height
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(left, right, bottom, top, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        self.updateProjection()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120
        factor = 0.9 ** delta
        self.zoom *= factor
        self.updateProjection()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos is not None:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            view_width = (self.max_x - self.min_x) * self.zoom
            view_height = (self.max_y - self.min_y) * self.zoom
            self.pan_offset_x -= dx * (view_width / self.width())
            self.pan_offset_y += dy * (view_height / self.height())
            self.last_mouse_pos = event.pos()
            self.updateProjection()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = None

    def setSimulationState(self, state):
        self.simState = state
        self.update()

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        self.updateProjection()

        self.edge_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.edge_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.edges.nbytes, self.edges, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.node_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.node_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.node_positions.nbytes, self.node_positions, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.node_color_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.node_color_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.node_colors.nbytes, self.node_colors, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glBegin(GL_QUADS)
        glColor3f(0.1, 0.1, 0.3)
        glVertex2f(self.min_x, self.min_y)
        glVertex2f(self.max_x, self.min_y)
        glColor3f(0.0, 0.0, 0.0)
        glVertex2f(self.max_x, self.max_y)
        glVertex2f(self.min_x, self.max_y)
        glEnd()

        self.updateProjection()

        pulse_factor = 0.0
        if self.mg_device:
            time_val = np.array([time.time()], dtype=np.float32)
            output_val = np.zeros(1, dtype=np.float32)
            buffer_in = self.mg_device.array_to_buffer(time_val)
            buffer_out = self.mg_device.create_buffer(1, "float")
            self.mg_device.run_function(1, [buffer_in, None, buffer_out])
            pulse_factor = np.frombuffer(buffer_out.contents, dtype=np.float32)[0]

        glLineWidth(1.5)
        glColor3f(0.7, 0.7, 0.7)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.edge_vbo)
        glVertexPointer(2, GL_FLOAT, 0, None)
        glDrawArrays(GL_LINES, 0, len(self.edges) // 2)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)

        colors = np.full((len(self.node_list), 3), 0.3, dtype=np.float32)
        visited = set(self.simState.get('visited', []))
        current = self.simState.get('current')
        if current is not None and current in self.node_to_index:
            colors[self.node_to_index[current]] = [1.0, 1.0, 0.0]
        for node in visited:
            if node in self.node_to_index:
                colors[self.node_to_index[node]] = [0.0, 0.0, 1.0]

        glBindBuffer(GL_ARRAY_BUFFER, self.node_color_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, colors.nbytes, colors)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        base_size = 5.0
        pulsing_size = base_size * (1.0 + 0.3 * pulse_factor)
        glPointSize(pulsing_size)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.node_vbo)
        glVertexPointer(2, GL_FLOAT, 0, None)
        glEnableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.node_color_vbo)
        glColorPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_POINTS, 0, len(self.node_list))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        route = self.simState.get('route')
        if route is not None and len(route) > 1:
            glLineWidth(3.0)
            glColor3f(1.0, 0.0, 0.0)
            glBegin(GL_LINES)
            for i in range(len(route) - 1):
                a = self.pos.get(route[i])
                b = self.pos.get(route[i+1])
                if a and b:
                    glVertex2f(a[0], a[1])
                    glVertex2f(b[0], b[1])
            glEnd()
