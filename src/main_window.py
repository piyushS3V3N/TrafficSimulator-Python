from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QSplitter
from simulation_gl_widget import SimulationGLWidget

class MainWindow(QMainWindow):
    def __init__(self, G, pos):
        super().__init__()
        self.setWindowTitle("Traffic Simulation & Navigation Analysis")

        splitter = QSplitter(self)
        self.simWidget = SimulationGLWidget(G, pos)
        splitter.addWidget(self.simWidget)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(splitter)

        self.closeButton = QPushButton("Stop Simulation")
        self.closeButton.clicked.connect(self.closeApplication)
        layout.addWidget(self.closeButton)
        self.setCentralWidget(central)

    def updateState(self, state):
        self.simWidget.setSimulationState(state)

    def closeApplication(self):
        self.simThread.stop()
        self.simThread.wait()
        self.close()
