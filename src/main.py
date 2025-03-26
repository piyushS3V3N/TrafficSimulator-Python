import sys
import random
from PyQt5.QtWidgets import QApplication
import osmnx as ox
from main_window import MainWindow
from path_window import PathWindow
from simulation_thread import SimulationThread

def main():
    app = QApplication(sys.argv)

    try:
        G = ox.graph_from_place("Delhi, India", network_type='drive')
        #G = ox.simplify_graph(G)  # Simplify the graph for performance
        pos = {node: (G.nodes[node]['x'], G.nodes[node]['y']) for node in G.nodes}
        source = random.choice(list(G.nodes))
        print("Source node:", source)
    except Exception as e:
        print("Error loading map data:", e)
        sys.exit(1)

    mainWindow = MainWindow(G, pos)
    pathWindow = PathWindow()

    simThread = SimulationThread(G, source)
    mainWindow.simThread = simThread
    simThread.updateState.connect(mainWindow.updateState)
    simThread.updateState.connect(pathWindow.updateState)
    simThread.finishedSimulation.connect(lambda: print("Simulation Complete"))
    simThread.start()

    mainWindow.show()
    pathWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
