class MachineState:
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2
    SLEEPING = 3
    CRASHED = 4

    NAMES = {0: "Off", 1: "Running", 2: "Paused", 3: "Sleeping", 4: "Crashed"}
    COLORS = {0: "#9aa0a6", 1: "#34a853", 2: "#fbbc04", 3: "#4285f4", 4: "#ea4335"}
