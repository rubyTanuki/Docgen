package MRILib.statemachine;

// Note: These imports were present but not used in the provided code.
// import com.qualcomm.robotcore.hardware.Gamepad;
// import java.util.HashMap;

/**
 * <b>Base class for states within a Finite State Machine (FSM).</b>
 *
 * <p>Provides a fundamental structure for individual states used in state machines
 * like {@link DriveFSM} or {@link ArmFSM}. It includes lifecycle methods that
 * subclasses can override to define specific behavior.</p>
 *
 * @see ArmFSM
 * @see DriveFSM
 * @see ArmState // Example of a subclass
 */
public class BotState{
    /** The name identifier for this state, used for debugging and retrieval. */
    public String name;

    /**
     * Constructor to create a state with a specific name.
     * @param n The desired name for this state instance.
     */
    public BotState(String n){
        name = n;
    }

    /**
     * Default constructor. Creates a state with the name "DEFAULT".
     */
    public BotState(){
        name = "DEFAULT";
    }

    /**
     * Called once when this state becomes the active state in the FSM.
     * Override this method in subclasses to implement state-specific initialization logic.
     */
    void start(){}; // Default implementation does nothing.

    /**
     * Called repeatedly in the FSM's update loop while this state is active.
     * Override this method in subclasses to implement the main logic of the state,
     * including checking for transition conditions.
     */
    void update(){}; // Default implementation does nothing.

    /**
     * Called once when this state is about to be deactivated (e.g., before transitioning
     * to another state).
     * Override this method in subclasses to implement state-specific cleanup logic.
     */
    void end(){}; // Default implementation does nothing.

    /**
     * Provides a string representation of the state, which is its name.
     * Useful for logging and debugging.
     * @return The name of the state.
     */
    @Override
    public String toString(){
        return name;
    }
}