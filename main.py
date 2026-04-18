from configure.config import Config
from configure.config_gui import configure_with_gui
from agents.drone_agent import DroneAgent
from simulation.simulator import Simulator
from agents.belief_state import BeliefState
from environment.environment_engine import Environment

def main():
    config = Config()
    config = configure_with_gui(config)
    if config is None:
        print("Simulation cancelled.")
        return

    agents = []
    env = Environment(config)

    for i in range(config.NUM_DRONES):
        if config.SIMULATION_MODE == "grid":
            start_pos = (0, i * 2)
        else:
            start_pos = env.get_spawn_position(i)

        agent = DroneAgent(i, start_pos, config)
        agent.belief = BeliefState(config)
        agent.belief.record_visit(agent.position)

        env.add_agent(agent)
        agents.append(agent)

    # run simulation
    sim = Simulator(env, agents, config)
    sim.run()


if __name__ == "__main__":
    main()
