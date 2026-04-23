package MRILib.motion;

import com.qualcomm.robotcore.util.ElapsedTime;
import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;
import org.firstinspires.ftc.robotcore.external.navigation.DistanceUnit;
import org.firstinspires.ftc.robotcore.external.navigation.Pose2D;
import com.qualcomm.robotcore.util.Range;
import java.util.function.Supplier; // Added for Supplier type
import org.firstinspires.ftc.robotcore.external.Telemetry;

import MRILib.managers.*;

/**
 * Manages three independent {@link PID} controllers (for X, Y, and Theta/Heading)
 * to guide a robot towards a target {@link Pose2D} using field-centric control.
 * <p>
 * This controller version calculates field-relative X, Y, and Theta PID outputs.
 * It then directly passes these outputs (scaled by {@code maxSpeed} and {@code maxAngSpeed})
 * to the {@link Bot#driveFieldXYW(double, double, double)} method. The {@code driveFieldXYW}
 * method is responsible for handling the necessary coordinate transformations and Mecanum kinematics
 * to achieve the desired field-centric movement and rotation.
 * <p>
 * Maximum speeds can be set dynamically using {@link Supplier} objects.
 *
 * @see PID
 * @see Bot#driveFieldXYW(double, double, double)
 * @see Pose2D
 * @see Supplier
 */
public class PIDController {
    /** The robot hardware interface ({@link Bot} or subclass) providing access to sensors and motors. */
    private Bot bot = null;
    /** Telemetry object for displaying debug information. */
    private Telemetry telemetry;

    /** The PID controller for the X-axis movement (field-centric). */
    public PID xPID;
    /** The PID controller for the Y-axis movement (field-centric). */
    public PID yPID;
    /** The PID controller for the rotational (Theta/Heading) movement. */
    public PID thetaPID; // Should ideally be HeadingPID for angle wrapping if used directly on heading

    /** The current target X-coordinate (inches) set via {@link #moveTo(double, double, double)}. */
    public double targetX = 0;
    /** The current target Y-coordinate (inches) set via {@link #moveTo(double, double, double)}. */
    public double targetY = 0;
    /** The current target heading (radians) set via {@link #moveTo(double, double, double)}. */
    public double targetRadians = 0; //radians

    /**
     * Supplier for the maximum allowable angular (rotational) speed component.
     * Allows dynamic speed limits. Defaults to a supplier returning 0.6.
     */
    public Supplier<Double> maxAngSpeed = ()-> 0.6; // Default supplier
    /**
     * Supplier for the maximum allowable translational speed component.
     * Allows dynamic speed limits. Defaults to a supplier returning 0.5 in the constructor.
     */
    public Supplier<Double> maxSpeed;
    /** Scaling factor for power, declared but currently unused. */
    public double POWER_SCALE = 1; // Potentially unused field


    /** Timer object, declared but apparently unused in the current implementation. */
    ElapsedTime timer = null; // Potentially unused field

    /** Flag, declared but apparently unused in the current implementation. */
    public boolean nextState = false; // Potentially unused field

    /**
     * Constructs a PIDController associated with a generic {@link Bot}.
     * Initializes maxSpeed supplier to return 0.5 by default.
     *
     * @param bot The {@link Bot} instance providing hardware access (odometry, motors).
     * @param telemetry The {@link Telemetry} instance for outputting debug data.
     */
    public PIDController(Bot bot, Telemetry telemetry){
        maxSpeed = ()->0.5; // Default translational speed supplier
        this.bot = bot;
        this.telemetry = telemetry;
        // timer = new ElapsedTime(); // Initialize if timer is intended to be used
    }

    // Constructor for ArmBotEasy removed as it's redundant with the Bot constructor

    /**
     * Sets the PID controllers for the X and Y axes (translational).
     *
     * @param x The {@link PID} instance for X-axis control.
     * @param y The {@link PID} instance for Y-axis control.
     */
    public void setPID(PID x, PID y){
        xPID = x;
        yPID = y;
    }

    /**
     * Sets the PID controller for the Theta (heading/turn) axis.
     * Consider using {@link HeadingPID} if this PID directly controls absolute heading
     * to handle angle wrapping correctly within the PID update.
     *
     * @param theta The {@link PID} instance for rotational control.
     */
    public void setTurnPID(PID theta){
        thetaPID = theta;
    }

    /**
     * Initializes the PID controllers.
     * Resets the internal state (integral sum, last error) of the X, Y, and Theta PIDs.
     * Sets the initial target for the Theta PID based on the last call to `moveTo` (or 0 initially).
     */
    public void start(){
        if (xPID != null) xPID.start();
        if (yPID != null) yPID.start();
        if (thetaPID != null) {
            // Target is set in moveTo, just reset state here
            thetaPID.setTarget(targetRadians); // Ensure PID starts with the correct target
            thetaPID.start();
        }
    }

    /**
     * Updates the PID controllers and commands the robot using field-centric drive.
     * <p>
     * 1. Reads the current robot pose (X, Y, Heading).
     * 2. Updates the X, Y, and Theta PIDs based on the current pose and their respective targets.
     * 3. Retrieves the maximum speed limits from the suppliers.
     * 4. Normalizes the translational PID outputs (X, Y) if their combined magnitude exceeds 1.0.
     * 5. Calls {@link Bot#driveFieldXYW(double, double, double)} with the scaled, field-centric
     *    X, Y, and Theta PID outputs.
     * </p>
     */
    public void update() {
        // Get the current pose and heading (field-centric)
        Pose2D curPos = bot.getPosition();
        double curX = curPos.getX(DistanceUnit.INCH);
        double curY = curPos.getY(DistanceUnit.INCH);
        double botHeadingRad = Math.toRadians(bot.getHeading());  // current heading in radians

        // Get field-centric PID outputs for x and y (translation)
        // PID target is set to the desired field coordinate in moveTo()
        double xVal = xPID.update(curX);  // Error correction for X
        double yVal = yPID.update(curY);  // Error correction for Y

        // Get PID output for theta (rotation)
        // Theta PID target is set to targetRadians in moveTo()
        // Assumes thetaPID handles angle wrapping if it's a HeadingPID, or if error is calculated correctly before passing to standard PID
        double thetaVal = thetaPID.update(botHeadingRad); // Error correction for heading
        // Clip theta output (potentially redundant if maxAngSpeed handles magnitude)
        thetaVal = Range.clip(thetaVal, -1.0, 1.0); // Clip raw PID output first

        // Retrieve dynamic speed limits
        double currentMaxSpeed = maxSpeed.get();
        double currentMaxAngSpeed = maxAngSpeed.get();

        // --- Normalize translational vector and apply speed limits ---
        // Calculate the magnitude of the translational vector
        double translationalMagnitude = Math.sqrt(xVal * xVal + yVal * yVal);
        double scaledX = xVal;
        double scaledY = yVal;

        // If magnitude is non-zero, scale it by maxSpeed.
        // If magnitude is zero, outputs remain zero.
        if (translationalMagnitude > 1e-6) { // Avoid division by zero / operating on tiny values
            // Scale the components proportionally to match maxSpeed at full PID output
            scaledX = (xVal / translationalMagnitude) * currentMaxSpeed * translationalMagnitude; // Simplified: xVal * currentMaxSpeed? No, this scales magnitude.
            scaledY = (yVal / translationalMagnitude) * currentMaxSpeed * translationalMagnitude; // Simplified: yVal * currentMaxSpeed?
            // Let's rethink: Scale the raw PID output by maxSpeed, then clip *if needed* by driveFieldXYW or ensure PID outputs are within [-1,1] effectively.
            // The original logic scaled based on the *larger* of xVal/yVal if > 1.

             // Alternative approach: Scale raw PID outputs by maxSpeed directly
             scaledX = xVal * currentMaxSpeed;
             scaledY = yVal * currentMaxSpeed;
             // Clipping might still be necessary depending on PID tuning and maxSpeed value.
             // Let driveFieldXYW handle final clipping/normalization.
        }


        // Scale rotational output
        double scaledTheta = thetaVal * currentMaxAngSpeed;

        // Send field-centric power commands to the Bot's drive method
        // The driveFieldXYW method handles rotation to robot-centric and applies powers.
        // Pass the *scaled* field-centric X, Y, and Theta commands.
        bot.driveFieldXYW(scaledX, scaledY, scaledTheta);


        // Original normalization logic (for reference):
        // double max = Math.max(Math.abs(xVal), Math.abs(yVal)); // Find max absolute component
        // if(max > 1.0) {
        //     // Normalize translation vector if max component > 1, then scale by maxSpeed
        //     bot.driveFieldXYW((xVal / max) * currentMaxSpeed, (yVal / max) * currentMaxSpeed, scaledTheta);
        // } else {
        //     // Scale by maxSpeed directly if within [-1, 1]
        //     bot.driveFieldXYW(xVal * currentMaxSpeed, yVal * currentMaxSpeed, scaledTheta);
        // }

    }

    /**
     * Sets the target pose for the PID controllers.
     * Updates the target values for the X, Y, and Theta PIDs directly.
     *
     * @param x       The target X-coordinate (inches) on the field.
     * @param y       The target Y-coordinate (inches) on the field.
     * @param degrees The target heading (degrees) relative to the field.
     */
    public void moveTo(double x, double y, double degrees)
    { // sets the target position to move towards
        // Set targets for X and Y PIDs
        xPID.setTarget(x);
        targetX = x; // Update internal copy
        yPID.setTarget(y);
        targetY = y; // Update internal copy

        // Set target for Theta PID (convert degrees to radians)
        targetRadians = Math.toRadians(degrees);
        thetaPID.setTarget(targetRadians);
    }

    /**
     * Sets the maximum translational speed limit using a simple supplier.
     *
     * @param s The maximum speed multiplier (0.0 to 1.0).
     */
    public void setMaxSpeed(double s){
        final double clippedSpeed = Range.clip(s, 0.0, 1.0); // Ensure speed is valid
        maxSpeed = ()-> clippedSpeed; // Create a supplier that returns the constant value
    }

    /**
     * Sets the maximum angular (rotational) speed limit using a simple supplier.
     *
     * @param s The maximum angular speed multiplier (0.0 to 1.0).
     */
    public void setMaxAngSpeed(double s){
        final double clippedSpeed = Range.clip(s, 0.0, 1.0); // Ensure speed is valid
        maxAngSpeed = ()-> clippedSpeed; // Create a supplier that returns the constant value
    }


    // --- Getters ---

    /**
     * Gets the current target X-coordinate set by {@link #moveTo(double, double, double)}.
     * @return The target X-coordinate (inches).
     */
    public double getTargetX(){
        return targetX;
    }

    /**
     * Gets the current target Y-coordinate set by {@link #moveTo(double, double, double)}.
     * @return The target Y-coordinate (inches).
     */
    public double getTargetY(){
        return targetY;
    }

    /**
     * Gets the current target heading set by {@link #moveTo(double, double, double)}.
     * @return The target heading in radians.
     */
    public double getTargetRadians(){
        return targetRadians;
    }

    /**
     * Gets the current target heading in degrees.
     * Converts the internal radian target back to degrees.
     * Note: The original negation is removed as targets seem direct now. Verify consistency.
     * @return The target heading in degrees.
     */
    public double getTargetDegrees(){
        return Math.toDegrees(targetRadians);
    }

    /**
     * Gets the robot's current heading in degrees, based on odometry.
     * Note: The original negation is kept, assuming the odometry reading or coordinate system
     * requires it for the desired output convention. Verify this convention.
     * @return The current heading in degrees (potentially negated).
     */
    public double getCurrentDegrees(){
        // Negation might be needed depending on bot.getPosition().getHeading() convention vs desired output
        return -bot.getPosition().getHeading(AngleUnit.DEGREES);
    }

    /**
     * Gets the robot's current heading in radians, based on odometry.
     * Note: The original negation is kept, assuming the odometry reading or coordinate system
     * requires it for the desired output convention. Verify this convention.
     * @return The current heading in radians (potentially negated).
     */
    public double getCurrentRadians(){
         // Negation might be needed depending on bot.getPosition().getHeading() convention vs desired output
        return Math.toRadians(-bot.getPosition().getHeading(AngleUnit.DEGREES));
    }
}
