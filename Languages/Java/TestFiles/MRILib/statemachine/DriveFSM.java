/*
 * This file contains the finite state machine for controlling your robot's motion throughout autonomous
 *
 * The state machine operates by taking in a list of steps from the opmode at compile time and
 * iterating through the steps during the looping period. when either a waitForSeconds or MoveTo is called,
 * the state gets added to a list of states. Each of these states have a transition condition in the update
 * method which allows them to decide when to move to the next step.
 *
 * All coordinates input to MoveTo should be using the FTC standard x y grid, in which each unit corresponds to
 * one inch
 * This means that when creating a new autonomous, all you need to know is which tile the robot needs to go to,
 * and where the robot starts. I reccomend starting with excessive waitForSeconds after any arm movements
 * or large moveTo calls while testing until you are very comfortable with the timing of the movements, as well as
 * setting your PIDController's max speed to pretty low at first
 *
 * All states are overloaded with a Runnable parameter, which allows for multithreading of any turret/arm controls. This means
 * to put the method calls of controlling an arm in parallel to the DriveFSM operations, as well as lining up these commands with
 * the steps of your autonomous, eliminating the need for any timers on arm state control or position thresholds.
 * The runnables are primarily made easy by use of lambdas (runnable literals) in the opmode. Any method call or single line of code
 * can be entered here, so any type of arm control can feasibly be substituted for my ArmFSM easily.
 *
 * Examples of all the usage for this can be found in ExampleAuton and ExampleTeleop
 *
 *
 * @author Avery
 * @version 1.0.0
 *
 *
*/


package MRILib.statemachine;

import MRILib.managers.*;
import MRILib.motion.PIDController;
import MRILib.util.Mathf;

import org.firstinspires.ftc.robotcore.external.navigation.Pose2D;
import com.qualcomm.robotcore.util.ElapsedTime;
import org.firstinspires.ftc.robotcore.external.navigation.DistanceUnit;
import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;
import com.qualcomm.robotcore.hardware.Gamepad;
import java.util.ArrayList;

/**
 * <b>Controls robot motion during autonomous using a finite state machine.</b>
 *
 * <p>Manages a sequence of autonomous steps ({@link BotState}), executing them sequentially.
 * Supports moving to specific coordinates ({@link #moveTo}) and waiting ({@link #waitForSeconds}),
 * optionally running parallel commands ({@link Runnable}) during steps. Uses a {@link PIDController}
 * for motion control based on {@link Bot} odometry.</p>
 *
 * <p>Coordinates are in inches based on the FTC field standard.</p>
 *
 * @author Avery
 * @version 1.0.0
 */
public class DriveFSM
{
    /** The robot hardware and state manager. */
    private Bot bot;
    /** The PID controller for movement. */
    private PIDController pid = null;
    /** List of autonomous steps (states). */
    ArrayList<BotState> steps = new ArrayList<>();

    /** Index of the currently active step in the 'steps' list. */
    public int currentStep = 0;

    /**
     * Initializes the DriveFSM.
     * @param bot The robot instance.
     * @param pid The PID controller instance.
     */
    public DriveFSM(Bot bot, PIDController pid){
        this.bot = bot;
        this.pid = pid;
    }

    /**
     * Executes the start logic of the current step.
     */
    public void start()
    { // runs once at the state's initialization
        steps.get(currentStep).start();
    }

    /**
     * Executes the update logic of the current step.
     */
    public void update()
    { // runs every repeat loop on the main thread
        steps.get(currentStep).update();
    }

    /**
     * Executes the end logic of the current step.
     */
    public void end()
    { // runs once at the end of the state or before transitioning to next state
        steps.get(currentStep).end();
    }

    /**
     * Ends the current step and starts the next one.
     */
    public void nextState()
    { // transitioning to the next state once target condition is met
        if (currentStep >= steps.size() - 1) return; // Prevent index out of bounds after last step
        end();
        currentStep++;
        start();
    }

    //MOVETO OVERLOADS

    /**
     * Adds a moveTo step with a parallel command and default timeout.
     * @param x Target X coordinate (inches).
     * @param y Target Y coordinate (inches).
     * @param theta Target heading (degrees).
     * @param command Runnable command to execute in parallel.
     */
    public void moveTo(double x, double y, double theta, Runnable command){
        moveTo(x, y, theta, command, 5); }

    /**
     * Adds a moveTo step with a specific timeout and no parallel command.
     * @param x Target X coordinate (inches).
     * @param y Target Y coordinate (inches).
     * @param theta Target heading (degrees).
     * @param timeout Maximum time for this step (seconds).
     */
    public void moveTo(double x, double y, double theta, double timeout){
        moveTo(x, y, theta, null, timeout); }

    /**
     * Adds a moveTo step with default timeout and no parallel command.
     * @param x Target X coordinate (inches).
     * @param y Target Y coordinate (inches).
     * @param theta Target heading (degrees).
     */
    public void moveTo(double x, double y, double theta){
        moveTo(x, y, theta, null, 5); }

    /**
     * Adds a moveTo step using a Pose2D object with default timeout.
     * @param pose Target pose (containing X, Y, and heading).
     */
    public void moveTo(Pose2D pose){
        moveTo(pose.getX(DistanceUnit.INCH), pose.getY(DistanceUnit.INCH), pose.getHeading(AngleUnit.DEGREES)); }

    //MOVETO BASE METHOD

    /** Stores the last target X coordinate for hold position. */
    public double lastX = 0;
    /** Stores the last target Y coordinate for hold position. */
    public double lastY = 0;
    /** Stores the last target heading for hold position. */
    public double lastAngle = 0;

    /**
     * Adds a state to move to a target pose, optionally running a command.
     * @param x Target X coordinate (inches).
     * @param y Target Y coordinate (inches).
     * @param theta Target heading (degrees).
     * @param command Runnable command to execute in parallel (can be null).
     * @param timeout Maximum time allowed for this step (seconds).
     */
    public void moveTo(double x, double y, double theta, Runnable command, double timeout)
    {// Adding a new state to the step list to move to a position
        steps.add(new BotState("MOVE_TO:: (" + x + ", " + y + ") " + theta + "°")
        { // Overriding the base methods of BotState with logic specific to this state
            double tx = x;
            double ty = y;
            double tAngle = theta;
            ElapsedTime timer;

            @Override
            void start(){
                // Running parallel arm control
                if(command!=null)command.run();

                // Setting PID target position
                pid.moveTo(tx,ty,tAngle);

                // Saving old values
                lastX = tx;
                lastY = ty;
                lastAngle = tAngle;

                // Starting timer for timeout
                timer = new ElapsedTime();
            }
            @Override
            void update(){
                // Updating pid to set motor values
                pid.update();

                // Calculating distance from target position using odometry
                Pose2D curPos = bot.getPosition();
                double deltaX = tx - curPos.getX(DistanceUnit.INCH);
                double deltaY = ty - curPos.getY(DistanceUnit.INCH);
                double deltaAngle = tAngle - curPos.getHeading(AngleUnit.DEGREES); // Corrected angle difference
                deltaAngle = Mathf.angleWrap(deltaAngle);
                double dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY);


                // Declaring the acceptable error to allow moving onto the next step
                if(dist < 2 && Math.abs(deltaAngle) < 3){
                    nextState();
                }
                // Moving onto the next step if timer is above a timeout
                //      Mostly used to not get stuck indefinitely in the case of odometry not hitting its target
                //      or robot getting stuck on something
                if(timer.seconds() > timeout)
                    nextState();

            }
            // No end() override needed, default is empty
        });
    }

    //WAITFORSECONDS OVERLOADS

    /**
     * Adds a wait step with no parallel command.
     * @param seconds Duration to wait (seconds).
     */
    public void waitForSeconds(double seconds){
        waitForSeconds(seconds, null); }

    /**
     * Adds a step to run a command immediately (0-second wait).
     * @param command Runnable command to execute.
     */
    public void run(Runnable command){
        waitForSeconds(0, command); }

    //WAITFORSECONDS BASE METHOD

    /**
     * Adds a state to wait for a duration while holding position, optionally running a command.
     * @param seconds Duration to wait (seconds).
     * @param command Runnable command to execute in parallel (can be null).
     */
    public void waitForSeconds(double seconds, Runnable command)
    { // Adding a new state to the step list to wait for a specified time
        steps.add(new BotState("WAIT_FOR_SECONDS:: (" + seconds + ")")
        { // Overriding botstate with wait logic
            ElapsedTime timer;

            @Override
            void start(){
                // Running parallel arm command
                if(command!=null)command.run();

                // Setting pid target to the last target to hold position
                pid.moveTo(lastX,lastY,lastAngle);
                timer = new ElapsedTime();
            }
            @Override
            void update(){
                // Updating pid to move back to rest position if pushed out of it
                pid.update();

                // Moving to next state if wait value has elapsed
                if(timer.seconds() > seconds) nextState();
            }
            // No end() override needed, default is empty
        });
    }
}