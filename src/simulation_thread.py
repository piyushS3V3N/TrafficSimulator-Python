from PyQt5 import QtCore
import random

class SimulationThread(QtCore.QThread):
    updateState = QtCore.pyqtSignal(dict)
    finishedSimulation = QtCore.pyqtSignal()

    def __init__(self, G, source, parent=None):
        super().__init__(parent)
        self.G = G
        self.source = source
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        visited_nodes = []
        all_nodes = list(self.G.nodes)
        random.shuffle(all_nodes)
        for i, node in enumerate(all_nodes):
            if not self.running:
                break
            visited_nodes.append(node)
            state = {
                'visited': visited_nodes[:],
                'progress': ((i + 1) / len(all_nodes)) * 100,
                'current': node
            }
            self.updateState.emit(state)
            self.msleep(5)
        self.finishedSimulation.emit()
