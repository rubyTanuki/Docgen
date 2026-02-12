package MRILib.managers;

import com.qualcomm.robotcore.hardware.DcMotor;
import com.qualcomm.robotcore.hardware.Servo;
import com.qualcomm.robotcore.hardware.DcMotorEx;
import com.qualcomm.robotcore.hardware.HardwareMap;
import static MRILib.BotValues.*;
import java.lang.Thread;

/**
 * <b>Extends Bot to manage arm-specific hardware (motors, servos) for a Pivoting Slide Arm robot.</b>
 *
 * <p>This class initializes and provides control methods for slide and pivot motors,
 * and claw servos. It also integrates a {@link PivotArmController} running in a separate thread
 * for complex arm control logic (like feedforward and motion profiling).</p>
 *
 * @see Bot
 * @see PivotArmController
 */
public class ArmBotFF extends Bot{

    // Declaring OpMode members
    /** The motor controlling the linear slide extension. */
    private DcMotorEx slide;
    /** The motor controlling the arm pivot rotation. */
    private DcMotorEx pivot;

    /** The servo controlling the claw grip. */
    private Servo claw;
    /** The servo controlling the pitch (up/down tilt) of the claw. */
    private Servo claw_pitch;
    /** The servo controlling the roll (side-to-side rotation) of the claw. */
    private Servo claw_roll;

    /** Controller instance for managing pivot arm movements, potentially with feedforward. */
    private PivotArmController armController;
    /** Thread dedicated to running the armController logic concurrently. */
    private Thread armThread;

    /** Current encoder position of the slide motor. */
    int slidePos = 0;
    /** Current encoder position of the pivot motor. */
    int pivotPos = 0;

    /** Previous encoder position of the slide motor (from the last update). */
    int slidePosPrev = 0;
    /** Previous encoder position of the pivot motor (from the last update). */
    int pivotPosPrev = 0;

    /**
     * Constructor: Initializes the ArmBotFF.
     * Calls the parent Bot constructor, initializes arm motors and servos,
     * and starts the PivotArmController thread.
     * @param hm The HardwareMap from the OpMode.
     * @param telemetry The Telemetry object from the OpMode.
     */
    public ArmBotFF(HardwareMap hm, org.firstinspires.ftc.robotcore.external.Telemetry telemetry)
    { //constructor method
        super(hm, telemetry); // Pass telemetry to parent Bot constructor
        initMotors(hm);
        initServos(hm);
        armController = new PivotArmController(this); // Assumes PivotArmController takes ArmBotFF
        armThread = new Thread(armController);
        armThread.start();
        //resetEncoders(); // Resetting encoders is done within initMotors now
    }

    /**
     * Initializes slide and pivot motors from the hardware map.
     * Sets modes, directions, and resets encoders.
     * @param hm The HardwareMap from the OpMode.
     */
    private void initMotors(HardwareMap hm)
    { //initialising motors
        slide = hm.get(DcMotorEx.class, "slide");
        pivot = hm.get(DcMotorEx.class, "pivot");

        // Reset encoders first to ensure starting from 0
        slide.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        pivot.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);

        // Set target position tolerance (optional but recommended for RUN_TO_POSITION)
        // slide.setTargetPositionTolerance(SLIDE_TOLERANCE); // Example tolerance value
        // pivot.setTargetPositionTolerance(PIVOT_TOLERANCE); // Example tolerance value

        // Set motor directions
        slide.setDirection(SLIDEDIR); // Assumes SLIDEDIR is defined in BotValues
        pivot.setDirection(PIVOTDIR); // Assumes PIVOTDIR is defined in BotValues

        // Set default run mode (e.g., run without encoder or run using encoder)
        slide.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);
        pivot.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);

        // Set zero power behavior (BRAKE or FLOAT)
        slide.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);
        pivot.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);

        // Reset internal position tracking variables
        resetPrevEncoders(); // Resets slidePosPrev, pivotPosPrev
        updateEncoders();    // Reads initial positions into slidePos, pivotPos
    }

    /**
     * Initializes claw servos from the hardware map.
     * @param hm The HardwareMap from the OpMode.
     */
    private void initServos(HardwareMap hm)
    { //initialising servos
        claw_pitch = hm.get(Servo.class, "clawPitch");
        claw_roll = hm.get(Servo.class, "claw_roll");
        claw = hm.get(Servo.class, "claw");
        // Consider setting initial servo positions here if needed
        // claw_pitch.setPosition(CLAW_PITCH_INIT);
        // claw_roll.setPosition(CLAW_ROLL_INIT);
        // claw.setPosition(CLAW_OPEN);
    }

    /**
     * Sets the {@link DcMotor.RunMode} for both slide and pivot motors.
     * @param mode The desired RunMode (e.g., RUN_TO_POSITION, RUN_WITHOUT_ENCODER).
     */
    public void setArmMode(DcMotor.RunMode mode)
    {
        slide.setMode(mode);
        pivot.setMode(mode);
    }

    /**
     * Resets encoders for drive motors (via superclass) and arm motors.
     * Preserves the current RunMode after resetting.
     */
    @Override
    public void resetEncoders()
    { //Resetting encoders to 0, keeping current mode
        super.resetEncoders(); // Reset drive train encoders

        // Store current modes
        DcMotor.RunMode slideMode = slide.getMode();
        DcMotor.RunMode pivotMode = pivot.getMode();

        // Reset arm motor encoders
        slide.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        pivot.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);

        // Restore original modes
        slide.setMode(slideMode);
        pivot.setMode(pivotMode);

        // Reset internal position tracking variables
        resetPrevEncoders();
        updateEncoders(); // Update current positions after reset
    }

    /**
     * Resets the internal previous encoder position trackers for arm motors.
     */
    public void resetPrevEncoders() {
        super.resetPrevEncoders(); // Reset drive train previous positions
        slidePosPrev = 0;
        pivotPosPrev = 0;
    }


    /**
     * Updates the arm controller with current pivot state.
     * Should be called in the main OpMode loop after {@link #updateEncoders()}.
     */
    public void updateControllerState(){
        // Pass necessary state info to the controller thread
        // This might involve thread-safe mechanisms if PivotArmController modifies shared state
        if (armController != null) {
             armController.updateCurrentState(pivotPos, getPivotVelocity());
        }
    }

    /**
     * Updates current and previous encoder positions for drive and arm motors.
     * Should be called once per loop in the OpMode.
     */
    @Override
    public void updateEncoders()
    { //updates current and last encoder positions
        super.updateEncoders(); // Update drive train encoders

        // Update previous positions
        slidePosPrev = slidePos;
        pivotPosPrev = pivotPos;

        // Read current positions
        slidePos = slide.getCurrentPosition();
        pivotPos = pivot.getCurrentPosition();
    }

    // --- Getter methods ---
    /** @return The slide motor instance. */
    public DcMotorEx getSlideMotor()    { return slide;     }
    /** @return The pivot motor instance. */
    public DcMotorEx getPivotMotor()    { return pivot;     }
    /** @return The current slide encoder position. */
    public int getSlidePos()            { return slidePos;  }
    /** @return The current pivot encoder position. */
    public int getPivotPos()            { return pivotPos;  }
    /** @return The current slide motor velocity (encoder ticks per second). */
    public double getSlideVelocity()    { return slide.getVelocity(); }
    /** @return The current pivot motor velocity (encoder ticks per second). */
    public double getPivotVelocity()    { return pivot.getVelocity(); }


    /** @return The claw pitch servo instance. */
    public Servo getClawPitch()         { return claw_pitch;    }
    /** @return The claw roll servo instance. */
    public Servo getClawRoll()          { return claw_roll;     }
    /** @return The claw grip servo instance. */
    public Servo getClaw()              { return claw;          }
    /** @return The current position of the claw pitch servo (0.0 to 1.0). */
    public double getClawPitchPos()     { return claw_pitch.getPosition();  }
    /** @return The current position of the claw roll servo (0.0 to 1.0). */
    public double getClawRollPos()      { return claw_roll.getPosition();   }
    /** @return The current position of the claw grip servo (0.0 to 1.0). */
    public double getClawPos()          { return claw.getPosition();        }

    // --- Setter methods ---

    /**
     * Sets the target position for the claw pitch servo.
     * @param pos Target position (0.0 to 1.0).
     */
    public void setClawPitch(double pos){
        // Add clamping or validation if necessary
        claw_pitch.setPosition(Math.max(0.0, Math.min(1.0, pos)));
    }
    /**
     * Sets the target position for the claw roll servo.
     * @param pos Target position (0.0 to 1.0).
     */
    public void setClawRoll(double pos){
        claw_roll.setPosition(Math.max(0.0, Math.min(1.0, pos)));
    }
    /**
     * Sets the target position for the claw grip servo.
     * @param pos Target position (0.0 to 1.0).
     */
    public void setClaw(double pos){
        claw.setPosition(Math.max(0.0, Math.min(1.0, pos)));
    }

    /**
     * Sets the pivot motor to run to a target encoder position.
     * Switches mode to RUN_TO_POSITION and sets a velocity.
     * @param target The target encoder tick count.
     */
    public void setPivot(int target){
        pivot.setTargetPosition(target);
        pivot.setMode(DcMotor.RunMode.RUN_TO_POSITION);
        // Consider making velocity configurable or using PIDF coefficients
        pivot.setVelocity(PIVOT_VELOCITY); // Example: Use a constant from BotValues
    }

    /**
     * Sets the pivot motor power directly.
     * Switches mode to RUN_WITHOUT_ENCODER.
     * @param pow The desired power (-1.0 to 1.0).
     */
    public void setPivotPower(double pow){
        pivot.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);
        pivot.setPower(pow);
    }

    /**
     * Sets the slide motor to run to a target encoder position.
     * Switches mode to RUN_TO_POSITION and sets a velocity.
     * @param target The target encoder tick count.
     */
    public void setSlides(int target){
        slide.setTargetPosition(target);
        slide.setMode(DcMotor.RunMode.RUN_TO_POSITION);
        slide.setVelocity(SLIDE_VELOCITY); // Example: Use a constant from BotValues
    }

    /**
     * Sets both pivot and slide motors to run to target positions simultaneously.
     * @param pivotTarget The target encoder position for the pivot motor.
     * @param slideTarget The target encoder position for the slide motor.
     */
    public void setArm(int pivotTarget, int slideTarget){
        setPivot(pivotTarget);
        setSlides(slideTarget);
    }

    /**
     * Stops the background arm controller thread safely.
     * Should be called at the end of the OpMode to clean up resources.
     */
    public void stopMultiThread(){
        if (armController != null) {
            armController.stop(); // Signal the controller thread to stop
        }
        if (armThread != null && armThread.isAlive()) {
            try {
                armThread.join(100); // Wait for the control thread to finish (with timeout)
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt(); // Re-interrupt the current thread
                System.err.println("Interrupted while waiting for arm thread to stop.");
            }
            if (armThread.isAlive()) {
                 System.err.println("Warning: Arm thread did not stop cleanly.");
                 // Consider armThread.interrupt() as a last resort if needed,
                 // but ensure PivotArmController handles interruption gracefully.
            }
        }
    }
}

/**
 * Placeholder interface/class for the arm controller.
 * Replace with your actual implementation.
 */
interface RunnableStoppable extends Runnable {
    void stop();
    void updateCurrentState(int currentPos, double currentVel);
}

class PivotArmController implements RunnableStoppable {
    private volatile boolean running = true;
    private ArmBotFF robot; // Reference to the robot hardware
    private int currentPivotPos;
    private double currentPivotVel;

    public PivotArmController(ArmBotFF robot) {
        this.robot = robot;
    }

    @Override
    public void run() {
        while (running && !Thread.currentThread().isInterrupted()) {
            // --- Arm Control Logic ---
            // Example: Apply feedforward based on current state
            // double feedforwardPower = calculateFeedforward(currentPivotPos, currentPivotVel);
            // robot.setPivotPower(feedforwardPower); // Or combine with PID output

            // Ensure loop doesn't run too fast
            try {
                Thread.sleep(20); // Adjust sleep time as needed
            } catch (InterruptedException e) {
                running = false; // Exit loop if interrupted
                Thread.currentThread().interrupt(); // Preserve interrupt status
            }
        }
        // Cleanup if needed when thread stops
        robot.setPivotPower(0); // Ensure motor stops
    }

    @Override
    public void stop() {
        running = false;
    }

    // Method to receive state updates from the main thread
    // Consider making this thread-safe if complex data is shared
    @Override
    public synchronized void updateCurrentState(int currentPos, double currentVel) {
        this.currentPivotPos = currentPos;
        this.currentPivotVel = currentVel;
    }

    // Example feedforward calculation (replace with actual logic)
    private double calculateFeedforward(int position, double velocity) {
        // double kG = 0.1; // Example gravity compensation constant
        // double kV = 0.01; // Example velocity constant
        // double kS = 0.05; // Example static friction constant
        // return kG * Math.cos(Math.toRadians(position * DEGREES_PER_TICK)) + kV * velocity + Math.signum(velocity) * kS;
        return 0; // Placeholder
    }
}