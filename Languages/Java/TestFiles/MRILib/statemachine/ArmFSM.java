/*
 * This file contains the finite state machine for controlling your robot's arm with states and transitions
 *
 * The init method contains the initialization of all states, which can then be accessed at runtime
 * by DriveFSM in order to control the arm, or controlled by teleop with individual setState() calls
 *
 * The protected class ArmState is implemented at the bottom, extending BotState with a transition system
 * and a way to save initialized states for later use
 *
 * In order for the state machine to react to dynamic information throughout the match (i.e. encoder changes and method calls),
 * you must call armSM.update() in your opMode in the loop, after calling bot.update() to update the opMode member manager class
 *
 * For a robot with a transfer system, or multiple arms, I suggest creating multiple ArmFSM classes and seperating the logic between them,
 * as this allows for the easiest management of two seperate systems without making your state machines difficult to read and implement
 * You can also make a manager class for both state machines that will call setState on both classes at once for QOL and readability
 *
 * to see an example of the intended usage of this class, see MRILib.opmodes.AutonExample
 */

package MRILib.statemachine;

import com.qualcomm.robotcore.hardware.Gamepad;
import java.util.HashMap;
import java.util.function.Supplier;
import java.util.ArrayList;

import MRILib.managers.*;


/**
 * <b>Finite State Machine for controlling robot arm mechanisms.</b>
 *
 * <p>Manages different arm states ({@link ArmState}) and transitions between them.
 * Integrates with {@link ArmBotEasy} for hardware control and can be used in
 * both Autonomous (via {@link DriveFSM}) and TeleOp modes.</p>
 *
 * <p>Requires calling {@link #update()} in the OpMode loop to process state logic and transitions.
 * Supports conditional actions via {@link #addConditional(Supplier, Runnable)}.</p>
 *
 * @see ArmState
 * @see ArmBotEasy
 * @see DriveFSM
 * @see Conditional
 */
public class ArmFSM
{
    /** The robot's arm hardware and methods manager. */
    private ArmBotEasy bot;

    /** The currently active arm state. */
    private ArmState currentState;

    /** List to hold conditional actions to be checked each loop. */
    private ArrayList<Conditional> conditionalList = new ArrayList<>();

    /** Reference to gamepad 1 for TeleOp control. */
    Gamepad gpad1;
    /** Reference to gamepad 2 for TeleOp control. */
    Gamepad gpad2;

    /** Flag indicating if the FSM is running in Autonomous mode. */
    boolean auton;

    /**
     * Constructor for Autonomous usage (no gamepads needed).
     * Initializes the FSM, loads states, and sets the default state.
     * @param bot The ArmBotEasy instance.
     */
    public ArmFSM(ArmBotEasy bot){
        auton = true;
        this.bot = bot;
        init();
        currentState = ArmState.getState("DEFAULT");
    }

    /**
     * Constructor for TeleOp usage (includes gamepads).
     * Initializes the FSM, loads states, sets the default state, and stores gamepad references.
     * @param bot The ArmBotEasy instance.
     * @param gpad1 The first gamepad.
     * @param gpad2 The second gamepad.
     */
    public ArmFSM(ArmBotEasy bot, Gamepad gpad1, Gamepad gpad2){
        auton = false;
        this.bot = bot;
        this.gpad1 = gpad1;
        this.gpad2 = gpad2;
        init();
        currentState = ArmState.getState("DEFAULT"); //starting on default state
    }


    /**
     * Executes the start logic of the current state.
     */
    public void start()
    { // runs once at the state's initialization
        currentState.start();
    }
    /**
     * Executes the update logic of the current state and checks conditionals.
     */
    public void update()
    { // runs every repeat loop on the main thread
        checkConditionals(); // Check one-time conditionals first
        currentState.update();
    }
    /**
     * Executes the end logic of the current state.
     */
    public void end()
    { // runs once at the end of the state or before transitioning to another state
        currentState.end();
    }


    /**
     * Sets the current state by name.
     * @param name The name of the target state (must have been initialized).
     * @see #setState(ArmState)
     */
    public void setState(String name)
    { // setting currentState to another saved state
        setState(ArmState.getState(name));
    }
    /**
     * Sets the current state to the provided ArmState instance.
     * Handles ending the previous state and starting the new one.
     * @param state The target ArmState instance.
     */
    public void setState(ArmState state)
    { // setting currentState to another saved state
        if(state != null && state != currentState){ // Added null check
            currentState.end();
            currentState = state;
            start();
        }
    }

    /**
     * Checks all transition conditions defined in the current state.
     * If a condition is met, transitions to the corresponding target state.
     * Should be called within the {@code update()} method of each {@link ArmState}.
     */
    public void transition()
    {
        HashMap<String, Boolean> transitions = currentState.getTransitions();
        for(String targetState : transitions.keySet()){
            // Use getOrDefault to avoid NullPointerException if key exists but value is null
            if(transitions.getOrDefault(targetState, false)){
                setState(targetState);
                break; // Transition to the first valid state found
            }
        }
    }

    /**
     * Adds a conditional action to be checked once per loop.
     * The command runs only once when the condition first becomes true.
     * @param condition A Supplier that returns true when the condition is met.
     * @param command A Runnable containing the code to execute when the condition is met.
     * @see Conditional
     * @see #checkConditionals()
     */
    public void addConditional(Supplier<Boolean> condition, Runnable command)
    { // adding a conditional to the list to be checked each loop until successful
        conditionalList.add(new Conditional(condition, command));
    }

    /**
     * Checks all stored conditionals. If a condition is met, executes its command
     * and removes it from the list so it doesn't run again.
     * Called automatically at the beginning of the main {@link #update()} method.
     */
    public void checkConditionals()
    { // parsing all currently saved conditional statements and removing them once called
        // Iterate backwards to allow safe removal during iteration
        for(int i = conditionalList.size() - 1; i >= 0; i--){
            Conditional cond = conditionalList.get(i);
            // Check condition safely
            Boolean conditionResult = false;
            try {
                conditionResult = cond.condition.get();
            } catch (Exception e) {
                // Handle potential exceptions from the supplier, e.g., log error
                System.err.println("Error evaluating conditional: " + e.getMessage());
                conditionalList.remove(i); // Remove problematic conditional
                continue; // Skip to next conditional
            }

            if(Boolean.TRUE.equals(conditionResult)){ // Safe check for true
                try {
                    cond.command.run(); // Execute the command
                } catch (Exception e) {
                    // Handle potential exceptions from the command runnable
                     System.err.println("Error executing conditional command: " + e.getMessage());
                }
                conditionalList.remove(i); // Remove after execution
            }
        }
    }


    /**
     * Initializes all the arm states.
     * New {@link ArmState} instances automatically register themselves.
     * Define state logic (start, update, end) and transitions here.
     */
    private void init(){
        // initializing and saving all arm states

        // ArmState constructor adds them to a static hashmap, so they can be created at init but
        // referenced at runtime, also helps with readability

        new ArmState("DEFAULT"){ //replace "DEFAULT" with any string, becomes the name of the state
            // declare variables here
            // i.e. ElapsedTime timer;

            @Override
            void start(){
                // logic to be run once at first loop of the state
                // initialize variables and transitions here
                // i.e. timer = new ElapsedTime();
                // i.e. setTransition("SOME_OTHER_STATE", false); // Initialize transition condition
            }
            @Override
            void update(){
                // update transition conditions here based on sensor values, time, etc.
                // i.e. setTransition("SOME_OTHER_STATE", timer.seconds() > 2.0);
                // i.e. setTransition("ANOTHER_STATE", bot.getSomeSensorValue() > 100);

                transition(); // checking all transitions to see if the state machine should move to another

                // logic to be run every loop while state is active
                // i.e. bot.setArmPower(0.5);
            }
            @Override
            void end(){
                // logic to be run once after the last loop of the state
                // i.e. bot.setArmPower(0.0); // Stop motors when leaving state
            }
        };

        // --- Add more ArmState definitions here ---
        /* Example:
        new ArmState("RAISE_ARM"){
            @Override void start() { bot.setArmTargetPosition(ARM_UP_POS); }
            @Override void update() {
                setTransition("HOLD_ARM", bot.isArmAtTarget());
                transition();
            }
            @Override void end() { } // Nothing specific needed on exit
        };

        new ArmState("HOLD_ARM"){
             @Override void start() { bot.holdArmPosition(); } // Assumes a method to hold position
             @Override void update() {
                 // Example transition based on gamepad button
                 // setTransition("LOWER_ARM", gpad1 != null && gpad1.a);
                 transition();
             }
             @Override void end() { }
        };
        */
    }

}

/**
 * Represents a single state for the arm FSM, extending {@link BotState}.
 * Manages its own transitions to other states based on conditions.
 * States are stored statically for easy retrieval by name.
 */
class ArmState extends BotState{

    /** Static map storing all initialized ArmState instances by name. */
    private static HashMap<String, ArmState> states = new HashMap<>();

    /**
     * Retrieves a previously initialized ArmState by its name.
     * @param s The name of the state to retrieve.
     * @return The requested ArmState, or the "DEFAULT" state if not found.
     */
    public static ArmState getState(String s)
    { // returning a previously saved state
        // Return default only if requested state is truly absent
        return states.getOrDefault(s, states.get("DEFAULT"));
    }
    /**
     * Clears all statically stored ArmState instances.
     * Useful for resetting between OpModes if necessary.
     */
    public static void clearSavedStates()
    { // clearing the hashmap of all saved states for static garbage collecting
        states.clear();
    }

    /**
     * Default constructor. Creates a state named "DEFAULT" and saves it.
     */
    public ArmState(){
        super(); // Call BotState constructor
        states.put("DEFAULT", this);
    }
    /**
     * Constructor creating a state with a specific name and saving it.
     * @param name The name to register this state under.
     */
    public ArmState(String name){
        super(name); // Call BotState constructor with name
        states.put(name, this);
    }
    /**
     * Constructor creating a state with a specific name, optionally saving it.
     * @param name The name of the state.
     * @param save Whether to save this state in the static map (true by default).
     */
    public ArmState(String name, boolean save){
        super(name);
        if(save) states.put(name, this);
    }

    /**
     * Sets the state that {@link #getState(String)} returns when a requested state is not found.
     * @param stateName The name of the existing state to set as the default fallback.
     */
    public void setDefault(String stateName)
    { // setting the default state to any initialized state
        if (states.containsKey(stateName)) {
            states.put("DEFAULT", states.get(stateName));
        }
    }


    /** Map storing transition conditions (Target State Name -> Condition Met?). */
    private HashMap<String, Boolean> transitions = new HashMap<>();

    /**
     * Defines or updates a transition condition from this state to another.
     * This should be called within the state's {@code update()} method.
     * @param targetState The name of the state to potentially transition to.
     * @param condition The boolean condition (true = transition, false = don't).
     */
    public void setTransition(String targetState, boolean condition){
        transitions.put(targetState, condition);
    }
    /**
     * Gets the map of currently evaluated transition conditions for this state.
     * Used by {@link ArmFSM#transition()}.
     * @return The HashMap of target state names to their boolean conditions.
     */
    public HashMap<String, Boolean> getTransitions(){
        return transitions;
    }

    // Default implementations for start, update, end are inherited from BotState (empty methods)
    // Override them in specific state definitions as needed.
}

/**
 * Helper class to store a condition (Supplier returning Boolean) and
 * an action (Runnable) to be executed when the condition is met.
 * Used by {@link ArmFSM#addConditional(Supplier, Runnable)}.
 */
class Conditional{
    /** The condition to check (returns true when met). */
    public Supplier<Boolean> condition;
    /** The command to run when the condition is met. */
    public Runnable command;

    /**
     * Creates a new Conditional holder.
     * @param condition The condition logic.
     * @param command The command logic.
     */
    public Conditional(Supplier<Boolean> condition, Runnable command){
        this.condition = condition;
        this.command = command;
    }
}