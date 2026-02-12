package MRILib.managers;

import com.qualcomm.robotcore.hardware.DcMotor;
import com.qualcomm.robotcore.hardware.Servo;
import com.qualcomm.robotcore.hardware.DcMotorEx;
import com.qualcomm.robotcore.hardware.HardwareMap;
import static MRILib.BotValues.*;

/**
 * Extends the base {@link Bot} class to include specific hardware and control logic
 * for a robot arm mechanism consisting of a slide, pivot, and claw assembly.
 * Provides methods for controlling the arm components and reading their states.
 * Assumes specific hardware names ("slide", "pivot", "clawPitch", "claw_roll", "claw").
 *
 * @see Bot
 * @see BotValues
 */
public class ArmBotEasy extends Bot{

    // Declaring OpMode members - Not documented as per user request
    private DcMotorEx slide;
    private DcMotorEx pivot;

    private Servo claw;
    private Servo claw_pitch;
    private Servo claw_roll;


    int slidePos = 0; // Package-private current slide encoder position
    int pivotPos = 0; // Package-private current pivot encoder position

    int slidePosPrev = 0; // Package-private previous slide encoder position
    int pivotPosPrev = 0; // Package-private previous pivot encoder position

    /**
     * Constructor for ArmBotEasy.
     * Initializes the base Bot functionalities and the specific arm motors and servos.
     *
     * @param hm The {@link HardwareMap} from the OpMode, used to retrieve hardware devices.
     */
    public ArmBotEasy(HardwareMap hm)
    { //constructor method
        super(hm); // Call the parent Bot constructor
        initMotors(hm);
        initServos(hm);
        // resetEncoders(); // Encoders are reset within initMotors
    }

    /**
     * Initializes the slide and pivot motors.
     * Retrieves them from the hardware map, sets their direction, and resets encoders.
     * Sets the initial RunMode to STOP_AND_RESET_ENCODER.
     * @param hm The HardwareMap to retrieve motors from.
     */
    private void initMotors(HardwareMap hm)
    { //initialising motors
        slide = hm.get(DcMotorEx.class, "slide");
        pivot = hm.get(DcMotorEx.class, "pivot");

        // Reset encoders at startup
        slide.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        pivot.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);

        // Set motor directions based on constants from BotValues
        slide.setDirection(SLIDEDIR);
        pivot.setDirection(PIVOTDIR);

        // Set target position tolerance (optional, depends on DcMotorEx implementation)
        // slide.setTargetPositionTolerance(SLIDE_TOLERANCE);
        // pivot.setTargetPositionTolerance(PIVOT_TOLERANCE);

        // Set motors to run using encoders after reset
        slide.setMode(DcMotor.RunMode.RUN_USING_ENCODER);
        pivot.setMode(DcMotor.RunMode.RUN_USING_ENCODER);

        // Initialize position variables
        slidePos = slide.getCurrentPosition();
        pivotPos = pivot.getCurrentPosition();
        slidePosPrev = slidePos;
        pivotPosPrev = pivotPos;
    }

    /**
     * Initializes the claw, claw pitch, and claw roll servos.
     * Retrieves them from the hardware map.
     * @param hm The HardwareMap to retrieve servos from.
     */
    private void initServos(HardwareMap hm)
    { //initialising servos
        claw_pitch = hm.get(Servo.class, "clawPitch");
        claw_roll = hm.get(Servo.class, "claw_roll");
        claw = hm.get(Servo.class, "claw");
    }

    /**
     * Sets the {@link DcMotor.RunMode} for both the slide and pivot motors simultaneously.
     * Useful for switching between modes like RUN_USING_ENCODER and RUN_TO_POSITION.
     *
     * @param mode The desired {@link DcMotor.RunMode}.
     */
    public void setArmMode(DcMotor.RunMode mode)
    {
        slide.setMode(mode);
        pivot.setMode(mode);
    }

    /**
     * Resets the encoders for all drive motors (via superclass) and the arm motors (slide, pivot).
     * This sets the current position of these motors to 0 without changing their RunMode.
     *
     * @see Bot#resetEncoders()
     */
    @Override
    public void resetEncoders()
    { //Resetting encoders to 0, preserving RunMode
        super.resetEncoders(); // Reset drive motor encoders first

        // Store the current modes
        DcMotor.RunMode slideMode = slide.getMode();
        DcMotor.RunMode pivotMode = pivot.getMode();

        // Reset encoders
        slide.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        pivot.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);

        // Restore the original modes
        slide.setMode(slideMode);
        pivot.setMode(pivotMode);

        // Update position variables after reset
        updateEncoders();
    }


    /**
     * Updates the stored encoder positions for all drive motors (via superclass)
     * and the arm motors (slide, pivot). Stores the previous values as well.
     * This should be called periodically (e.g., in the loop) to get fresh encoder readings.
     *
     * @see Bot#updateEncoders()
     */
    @Override
    public void updateEncoders()
    { //updates current and last encoder positions
        super.updateEncoders(); // Update drive motor encoders first

        // Store previous arm positions
        slidePosPrev = slidePos;
        pivotPosPrev = pivotPos;

        // Get current arm positions
        slidePos = slide.getCurrentPosition();
        pivotPos = pivot.getCurrentPosition();
    }

    // --- Getter Methods ---

    /**
     * Gets the slide motor instance.
     * @return The {@link DcMotorEx} object for the slide.
     */
    public DcMotorEx getSlideMotor()    { return slide;     }

    /**
     * Gets the pivot motor instance.
     * @return The {@link DcMotorEx} object for the pivot.
     */
    public DcMotorEx getPivotMotor()    { return pivot;     }

    /**
     * Gets the last updated encoder position of the slide motor.
     * Call {@link #updateEncoders()} beforehand for the latest value.
     * @return The slide motor's encoder position.
     */
    public int getSlidePos()            { return slidePos;  }

    /**
     * Gets the last updated encoder position of the pivot motor.
     * Call {@link #updateEncoders()} beforehand for the latest value.
     * @return The pivot motor's encoder position.
     */
    public int getPivotPos()            { return pivotPos;  }

    /**
     * Gets the claw pitch servo instance.
     * @return The {@link Servo} object for the claw pitch.
     */
    public Servo getClawPitch()         { return claw_pitch;    }

    /**
     * Gets the claw roll servo instance.
     * @return The {@link Servo} object for the claw roll.
     */
    public Servo getClawRoll()          { return claw_roll;     }

    /**
     * Gets the main claw grip servo instance.
     * @return The {@link Servo} object for the claw grip.
     */
    public Servo getClaw()              { return claw;          }

    /**
     * Gets the current commanded position of the claw pitch servo.
     * Note: This returns the last commanded position, not necessarily the physical position if the servo is still moving.
     * @return The claw pitch servo position (typically 0.0 to 1.0).
     */
    public double getClawPitchPos()     { return claw_pitch.getPosition();  }

    /**
     * Gets the current commanded position of the claw roll servo.
     * @return The claw roll servo position (typically 0.0 to 1.0).
     */
    public double getClawRollPos()      { return claw_roll.getPosition();   }

    /**
     * Gets the current commanded position of the main claw grip servo.
     * @return The claw grip servo position (typically 0.0 to 1.0).
     */
    public double getClawPos()          { return claw.getPosition();        }


    // --- Setter Methods ---

    /**
     * Sets the target position for the claw pitch servo.
     * @param pos The target position (typically 0.0 to 1.0).
     */
    public void setClawPitch(double pos){
        claw_pitch.setPosition(pos);
    }

    /**
     * Sets the target position for the claw roll servo.
     * @param pos The target position (typically 0.0 to 1.0).
     */
    public void setClawRoll(double pos){
        claw_roll.setPosition(pos);
    }

    /**
     * Sets the target position for the main claw grip servo.
     * @param pos The target position (typically 0.0 to 1.0).
     */
    public void setClaw(double pos){
        claw.setPosition(pos);
    }

    /**
     * Sets the pivot motor to run to a specific target encoder position.
     * Switches the motor mode to {@link DcMotor.RunMode#RUN_TO_POSITION} and sets a default velocity.
     *
     * @param target The target encoder position for the pivot motor.
     */
    public void setPivot(int target){
        pivot.setTargetPosition(target);
        pivot.setMode(DcMotor.RunMode.RUN_TO_POSITION);
        // Consider making velocity a parameter or a constant
        pivot.setVelocity(6000); // TODO: Use a constant from BotValues?
    }

    /**
     * Sets the slide motor to run to a specific target encoder position.
     * Switches the motor mode to {@link DcMotor.RunMode#RUN_TO_POSITION} and sets a default velocity.
     *
     * @param target The target encoder position for the slide motor.
     */
    public void setSlides(int target){
        slide.setTargetPosition(target);
        slide.setMode(DcMotor.RunMode.RUN_TO_POSITION);
         // Consider making velocity a parameter or a constant
        slide.setVelocity(6000); // TODO: Use a constant from BotValues?
    }

    /**
     * Convenience method to set both the pivot and slide motors to run to target positions simultaneously.
     * Calls {@link #setPivot(int)} and {@link #setSlides(int)}.
     *
     * @param pivotTarget The target encoder position for the pivot motor.
     * @param slideTarget The target encoder position for the slide motor.
     */
    public void setArm(int pivotTarget, int slideTarget){
        setPivot(pivotTarget);
        setSlides(slideTarget);
    }
}