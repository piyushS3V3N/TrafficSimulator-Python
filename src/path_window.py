from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QProgressBar, QPushButton

class PathWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visited Path Log")
        self.setGeometry(100, 100, 400, 600)
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background: #333;
                color: white;
            }
            QProgressBar::chunk {
                background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                            stop: 0 #66e, stop: 1 #bbf);
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progressBar)
        self.closeButton = QPushButton("Close")
        self.closeButton.clicked.connect(self.close)
        layout.addWidget(self.closeButton)

    def updateState(self, state):
        self.textEdit.append(f"Visited: {state['current']}")
        self.progressBar.setValue(int(state['progress']))
