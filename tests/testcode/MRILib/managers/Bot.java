package MRILib.managers;

import com.qualcomm.robotcore.hardware.DcMotor;
import org.firstinspires.ftc.robotcore.external.Telemetry;
import com.qualcomm.robotcore.hardware.VoltageSensor;
import com.qualcomm.robotcore.hardware.DcMotorEx;
import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;
import org.firstinspires.ftc.robotcore.external.navigation.DistanceUnit;
import org.firstinspires.ftc.robotcore.external.navigation.Pose2D;
import com.qualcomm.hardware.rev.RevHubOrientationOnRobot;
import com.qualcomm.robotcore.hardware.IMU;
import com.qualcomm.robotcore.hardware.HardwareMap;

import MRILib.util.GoBildaPinpointDriver;
import static MRILib.BotValues.*;


/**
 * <b>Base Robot Hardware Manager and Controller</b>
 *
 * <p>This class manages the core hardware components of a typical FTC robot, focusing on the
 * drivetrain, odometry, IMU, and essential utilities. It provides a standardized interface
 * for initializing and interacting with these components.</p>
 *
 * <p>This implementation specifically uses a 4-motor Mecanum drive train and the
 * {@link GoBildaPinpointDriver} for odometry via an I2C device. It can be adapted for
 * different odometry systems (e.g., wheel encoders, 3-wheel dead odometry) by modifying
 * the {@code odo} variable initialization and ensuring method compatibility.</p>
 *
 * <p>This class serves as a superclass for more specific robot configurations, like {@link ArmBotEasy},
 * which adds control for manipulators (arms, claws, etc.). While subclasses handle unique mechanisms,
 * this base {@code Bot} class aims to remain consistent across different robot designs,
 * requiring only adjustments to initialization parameters in {@link BotValues}.</p>
 *
 * @see ArmBotEasy
 * @see GoBildaPinpointDriver
 * @see BotValues
 * @author Avery
 * @version 1.0.1 - Added Javadoc comments
 */
public class Bot{

    // Drive Motors - Not documented as per user request
    private DcMotorEx frontLeft;
    private DcMotorEx backLeft;
    private DcMotorEx frontRight;
    private DcMotorEx backRight;

    /**
     * The GoBilda Pinpoint Odometry Computer driver instance.
     * Provides access to the robot's position and heading via the Pinpoint device.
     * @see GoBildaPinpointDriver
     */
    public GoBildaPinpointDriver odo;

    /**
     * The Control Hub/Expansion Hub IMU (Inertial Measurement Unit) instance.
     * Provides access to the robot's orientation (yaw, pitch, roll).
     * @see IMU
     */
    public IMU imu;

    // Voltage Sensor - Not documented as per user request
    private VoltageSensor voltageSensor;

    // Current Position - Not documented as per user request
    private Pose2D currentPosition;
    // Last Position - Not documented as per user request
    private Pose2D lastPosition;

    // Telemetry - Not documented as per user request
    private Telemetry telemetry;


    // --- Package-Private Encoder Position Tracking ---
    /** Current encoder position of the front left drive motor. Updated by {@link #updateEncoders()}. */
    int frontLeftPos  = 0;
    /** Current encoder position of the front right drive motor. Updated by {@link #updateEncoders()}. */
    int frontRightPos = 0;
    /** Current encoder position of the back left drive motor. Updated by {@link #updateEncoders()}. */
    int backLeftPos   = 0;
    /** Current encoder position of the back right drive motor. Updated by {@link #updateEncoders()}. */
    int backRightPos  = 0;

    /** Previous encoder position of the front left drive motor (from the last {@link #updateEncoders()} call). */
    int frontLeftPosPrev  = 0;
    /** Previous encoder position of the front right drive motor (from the last {@link #updateEncoders()} call). */
    int frontRightPosPrev = 0;
    /** Previous encoder position of the back left drive motor (from the last {@link #updateEncoders()} call). */
    int backLeftPosPrev   = 0;
    /** Previous encoder position of the back right drive motor (from the last {@link #updateEncoders()} call). */
    int backRightPosPrev  = 0;
    // --- End Encoder Position Tracking ---


     /**
     * Constructs a Bot instance, initializing drive motors, IMU, odometry, and voltage sensor.
     * Uses default hardware map names ("frontLeft", "frontRight", etc.).
     *
     * @param hm The {@link HardwareMap} from the OpMode, used to retrieve hardware devices.
     */
    public Bot(HardwareMap hm)
    { //constructor
        // Removed telemetry parameter as it was unused in this version
        voltageSensor = hm.voltageSensor.iterator().next();
        initMotors(hm);
        initIMU(hm);
        initOdo(hm);
        // Initialize position to avoid null pointers before first update
        odo.update(); // Initial read
        currentPosition = getOdoPosition();
        lastPosition = currentPosition;
    }


    /**
     * Initializes the drive motors using default hardwareMap names ("frontLeft", "frontRight", "backLeft", "backRight").
     * Calls the overloaded version {@link #initMotors(HardwareMap, String, String, String, String)}.
     * @param hm OpMode's {@link HardwareMap}.
     */
    private void initMotors(HardwareMap hm){
        initMotors(hm, "frontLeft", "frontRight", "backLeft", "backRight");
    }

    /**
     * Initializes the drive motors with specified hardwareMap names and sets their directions.
     * Motors are typically set to {@link DcMotor.RunMode#RUN_WITHOUT_ENCODER} initially,
     * but directions are set based on {@link BotValues}.
     *
     * @param hm OpMode's {@link HardwareMap}.
     * @param fl Front left drive motor name in the configuration file.
     * @param fr Front right drive motor name in the configuration file.
     * @param bl Back left drive motor name in the configuration file.
     * @param br Back right drive motor name in the configuration file.
     */
    private void initMotors(HardwareMap hm, String fl, String fr, String bl, String br)
    { //initializing drive motors
        frontLeft = hm.get(DcMotorEx.class, fl);
        frontRight = hm.get(DcMotorEx.class, fr);
        backLeft = hm.get(DcMotorEx.class, bl);
        backRight = hm.get(DcMotorEx.class, br);

        // Setting the direction of the motors so all go forward when set to positive power
        setDirections(); // Based on BotValues constants

        // Optional: Set default run mode if needed (e.g., RUN_USING_ENCODER)
        // setMode(DcMotor.RunMode.RUN_USING_ENCODER);

        // Initialize encoder readings
        resetEncoders(); // Resets positions to 0
        updateEncoders(); // Populates current and previous position variables
    }

    /**
     * Initializes the Control Hub's IMU using the default hardwareMap name ("imu").
     * Calls the overloaded version {@link #initIMU(HardwareMap, String)}.
     * @param hm OpMode's {@link HardwareMap}.
     */
    public void initIMU(HardwareMap hm){
        initIMU(hm, "imu");
    }

    /**
     * Initializes the Control Hub's IMU with a specified hardwareMap name and orientation parameters
     * defined in {@link BotValues} (LOGO_DIR, USB_DIR).
     *
     * @param hm OpMode's {@link HardwareMap}.
     * @param name The name of the IMU device in the hardware configuration file.
     */
    public void initIMU(HardwareMap hm, String name)
    { //initializing on board IMU
        imu = hm.get(IMU.class, name);

        /*
         * Setting up the orientation of the control hub on the robot.
         * This is crucial for correctly interpreting the yaw, pitch, and roll angles.
         * Parameters define the direction the REV logo faces and the direction the USB ports face.
         */
        IMU.Parameters params = new IMU.Parameters(
            new RevHubOrientationOnRobot(LOGO_DIR, USB_DIR)); // Directions set in BotValues

        imu.initialize(params);
        imu.resetYaw(); // Start with a 0 heading relative to initialization orientation
    }

    /**
     * Initializes the GoBilda Pinpoint Odometry Computer using the default hardwareMap name ("odo").
     * Calls the overloaded version {@link #initOdo(HardwareMap, String)}.
     * @param hm OpMode's {@link HardwareMap}.
     */
    public void initOdo(HardwareMap hm){
        initOdo(hm, "odo");
    }

    /**
     * Initializes the GoBilda Pinpoint Odometry Computer with a specified hardwareMap name.
     * Sets necessary parameters like offsets, resolution, and encoder directions based on hardware setup.
     * Resets the initial pose to (0, 0) with 0 heading.
     *
     * @param hm OpMode's {@link HardwareMap}.
     * @param name The name of the Pinpoint device in the hardware configuration file.
     */
    public void initOdo(HardwareMap hm, String name)
    {
        odo = hm.get(GoBildaPinpointDriver.class,name);

        // TODO: These values might need tuning or constants in BotValues
        // Setting the initialization parameters of the two odometry wheels
        // Refer to GoBildaPinpointDriver documentation or examples for determining these values.
        odo.setOffsets(96.0, 75.0); // Example offsets
        odo.setEncoderResolution(GoBildaPinpointDriver.GoBildaOdometryPods.goBILDA_SWINGARM_POD);
        odo.setEncoderDirections(GoBildaPinpointDriver.EncoderDirection.FORWARD, GoBildaPinpointDriver.EncoderDirection.FORWARD); // Example directions

        // Resetting the position and heading to zero. Use setPosition() to start elsewhere.
        odo.resetPosAndIMU();
    }

    /**
     * Updates the robot's state. Called periodically in the main OpMode loop.
     * This method reads the latest data from the odometry device, updates the stored
     * {@link #currentPosition} and {@link #lastPosition}, and updates drive motor encoder readings.
     */
    public void update(){
        // Update robot position and encoder ticks in each opMode loop tick
        odo.update(); // Reads new data from the Pinpoint device
        lastPosition = currentPosition; // Store the pose from the *previous* update call
        currentPosition = getOdoPosition(); // Get the *newly updated* pose from the odo driver
        updateEncoders(); // Read drive motor encoders
    }

    /**
     * Updates the stored encoder positions for the drive train motors.
     * Saves the previous tick's values and reads the current values.
     * This method is called by {@link #update()}.
     */
    public void updateEncoders()
    { //updating current position numbers
        // Saving the current motor positions as the position in the last tick
        frontLeftPosPrev = frontLeftPos;
        frontRightPosPrev = frontRightPos;
        backLeftPosPrev = backLeftPos;
        backRightPosPrev = backRightPos;

        // Updating the current motor positions to their new values
        frontLeftPos = frontLeft.getCurrentPosition();
        frontRightPos = frontRight.getCurrentPosition();
        backLeftPos = backLeft.getCurrentPosition();
        backRightPos = backRight.getCurrentPosition();
    }


    // --- Getter Methods ---

    /** @return The front left drive motor instance ({@link DcMotorEx}). */
    public DcMotorEx getFL(){ return frontLeft;     }
    /** @return The front right drive motor instance ({@link DcMotorEx}). */
    public DcMotorEx getFR(){ return frontRight;    }
    /** @return The back left drive motor instance ({@link DcMotorEx}). */
    public DcMotorEx getBL(){ return backLeft;      }
    /** @return The back right drive motor instance ({@link DcMotorEx}). */
    public DcMotorEx getBR(){ return backRight;     }

    /** @return The last read encoder position of the front left motor. Call {@link #updateEncoders()} first for the latest value. */
    public int getFLPos(){ return frontLeftPos;  }
    /** @return The last read encoder position of the front right motor. Call {@link #updateEncoders()} first for the latest value. */
    public int getFRPos(){ return frontRightPos; }
    /** @return The last read encoder position of the back left motor. Call {@link #updateEncoders()} first for the latest value. */
    public int getBLPos(){ return backLeftPos;   }
    /** @return The last read encoder position of the back right motor. Call {@link #updateEncoders()} first for the latest value. */
    public int getBRPos(){ return backRightPos;  }

    /** @return The encoder position of the front left motor from the *previous* {@link #updateEncoders()} call. */
    public int getFLPosPrev() { return frontLeftPosPrev;  }
    /** @return The encoder position of the front right motor from the *previous* {@link #updateEncoders()} call. */
    public int getFRPosPrev() { return frontRightPosPrev; }
    /** @return The encoder position of the back left motor from the *previous* {@link #updateEncoders()} call. */
    public int getBLPosPrev() { return backLeftPosPrev;   }
    /** @return The encoder position of the back right motor from the *previous* {@link #updateEncoders()} call. */
    public int getBRPosPrev() { return backRightPosPrev;  }

    /**
     * Gets the robot's current heading (yaw) from the IMU.
     * Note: This value is negated to likely align with standard FTC coordinate systems (counter-clockwise positive).
     * @return The robot's heading in degrees.
     */
    public double getIMUHeading(){ return -imu.getRobotYawPitchRollAngles().getYaw(AngleUnit.DEGREES);}

    /** Resets the IMU's yaw angle to zero based on the current orientation. */
    public void resetIMUHeading(){ imu.resetYaw(); }

    /**
     * Gets the robot's current position and heading as estimated by the odometry system.
     * This value is updated during the {@link #update()} call.
     * @return The current {@link Pose2D} (position in inches, heading in degrees).
     */
    public Pose2D getPosition(){
        return currentPosition;
    }

    /**
     * Gets the robot's position and heading from the *previous* update cycle.
     * Useful for calculating displacement or velocity.
     * @return The {@link Pose2D} from the last call to {@link #update()}.
     */
    public Pose2D getLastPosition(){
        return lastPosition;
    }

    /**
     * Gets the raw position directly from the GoBilda Pinpoint driver.
     * Note: This might not be synchronized with the main {@link #update()} cycle.
     * Use {@link #getPosition()} for the synchronized pose.
     * @return The {@link Pose2D} currently reported by the odometry driver.
     */
    private Pose2D getOdoPosition(){
        // Kept private to encourage use of the synchronized getPosition()
        return odo.getPosition();
    }

    /**
     * Gets the current estimated X-coordinate of the robot.
     * Convenience method for {@code getPosition().getX(DistanceUnit.INCH)}.
     * @return The X-coordinate in inches.
     */
    public double getX(){
        return getPosition().getX(DistanceUnit.INCH);
    }

    /**
     * Gets the current estimated Y-coordinate of the robot.
     * Convenience method for {@code getPosition().getY(DistanceUnit.INCH)}.
     * @return The Y-coordinate in inches.
     */
    public double getY(){
        return getPosition().getY(DistanceUnit.INCH);
    }

    /**
     * Gets the current estimated heading of the robot.
     * Convenience method for {@code getPosition().getHeading(AngleUnit.DEGREES)}.
     * By default, this uses the heading from the {@link GoBildaPinpointDriver}.
     * @return The heading in degrees.
     */
    public double getHeading(){
        return getPosition().getHeading(AngleUnit.DEGREES);
    }

    /**
     * Gets the current battery voltage reported by the first available voltage sensor.
     * @return The current battery voltage in Volts.
     */
    public synchronized double getVoltage()
    { // returning the current output voltage from the battery
        return voltageSensor.getVoltage();
    }

    // Removed getTelemetry() as telemetry was removed from constructor


    // --- Setter/Configuration Methods ---

    /**
     * Sets the robot's current position and heading in the odometry system.
     * Overloads {@link #setPosition(Pose2D)} for convenience.
     *
     * @param x The desired X-coordinate (in inches).
     * @param y The desired Y-coordinate (in inches).
     * @param heading The desired heading (in degrees).
     */
    public void setPosition(double x, double y, double heading){
        setPosition(new Pose2D(x, y, AngleUnit.DEGREES.toRadians(heading))); // Create Pose2D correctly
    }

    /**
     * Overrides the current position tracked by the GoBilda Pinpoint Odometry Computer.
     * Useful for setting the starting pose at the beginning of autonomous.
     * @param pos The desired {@link Pose2D} to set as the current position.
     */
    public void setPosition(Pose2D pos)
    {
        odo.setPosition(pos);
        odo.update(); // Immediately update internal state after setting
        currentPosition = getOdoPosition(); // Sync Bot's position variable
        lastPosition = currentPosition;
    }

    /**
     * Sets the direction of the drive motors based on the constants defined in {@link BotValues}
     * (LEFTDIR, RIGHTDIR). Ensures positive power corresponds to forward motion for all wheels.
     */
    public void setDirections()
    { //setting the directions based on static BotValues
        frontLeft.setDirection(LEFTDIR);
        frontRight.setDirection(RIGHTDIR);
        backLeft.setDirection(LEFTDIR);
        backRight.setDirection(RIGHTDIR);
    }

    /**
     * Sets the {@link DcMotor.RunMode} for all four drive motors simultaneously.
     * @param mode The desired {@link DcMotor.RunMode} (e.g., RUN_USING_ENCODER, RUN_WITHOUT_ENCODER, STOP_AND_RESET_ENCODER).
     */
    public void setMode(DcMotor.RunMode mode)
    { //setting all drive motors to an input runmode
        frontLeft.setMode(mode);
        frontRight.setMode(mode);
        backLeft.setMode(mode);
        backRight.setMode(mode);
    }

    /**
     * Resets the drive motor encoders to 0 without changing their current {@link DcMotor.RunMode}.
     * Also resets the stored previous encoder tick values.
     */
    public void resetEncoders()
    { //Resetting encoders to 0, keeping current mode
        // Save the current run mode
        DcMotor.RunMode mode = frontLeft.getMode(); // Assuming all motors have the same mode

        // Stop and reset encoders
        frontLeft.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        frontRight.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        backLeft.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        backRight.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);

        // Reapply the original run mode
        setMode(mode);

        // Reset internal position tracking
        resetPrevEncoders(); // Zero out previous values
        updateEncoders(); // Update current values (should be near zero)
    }

    /**
     * Resets the stored *previous* encoder tick values to zero.
     * Called internally by {@link #resetEncoders()}.
     */
    public void resetPrevEncoders(){
        frontLeftPosPrev = 0;
        frontRightPosPrev = 0;
        backLeftPosPrev = 0;
        backRightPosPrev = 0;
    }

    /**
     * Enables or disables the "brake" zero power behavior for all drive motors.
     * When enabled (true), motors will actively resist movement when commanded power is zero.
     * When disabled (false), motors will coast or "float".
     * Uses constants BRAKE and FLOAT from {@link BotValues}.
     *
     * @param enabled Set to true to enable brake mode, false to enable float mode.
     */
    public void enableBrakeMode(boolean enabled)
    { // turning on or off brake mode
        DcMotor.ZeroPowerBehavior state = enabled ? BRAKE : FLOAT; // Constants from BotValues
        frontLeft.setZeroPowerBehavior(state);
        frontRight.setZeroPowerBehavior(state);
        backLeft.setZeroPowerBehavior(state);
        backRight.setZeroPowerBehavior(state);
    }

    // --- Driving Methods ---

    /**
     * Drives the robot using robot-centric Cartesian coordinates (x, y) and rotation (w).
     * Calculates the required power for each Mecanum wheel based on the desired movement vector
     * and rotation rate. Powers are scaled to stay within [-1, 1] and adjusted for battery voltage.
     *
     * @param rx Forward/Backward power (-1 to 1). Positive is typically forward.
     * @param ry Strafe Left/Right power (-1 to 1). Positive is typically right.
     * @param rw Rotational power (-1 to 1). Positive is typically counter-clockwise.
     */
    public void driveXYW(double rx, double ry, double rw)
    { // sets proportional power to drive motors based on robot-centric inputs
        /*
           rx: Forward component
           ry: Strafe component
           rw: Rotation component

           Calculates wheel powers for Mecanum drive based on these inputs.
           Normalizes powers to prevent exceeding |1.0|.
           Compensates for battery voltage variations.
        */

        // Denominator for normalization. Ensures no motor power exceeds 1.0 while maintaining ratio.
        double denom = Math.max(Math.abs(rx) + Math.abs(ry) + Math.abs(rw), 1.0);

        // Voltage compensation factor. Reduces power slightly at higher voltages for consistency.
        double voltageMulti = Math.max(1.0, getVoltage() / 12.0); // Prevent division by zero or amplifying low voltage

        // Mecanum wheel power calculations
        // Assumes standard Mecanum wheel configuration and motor directions set correctly.
        double lfPower = (rx + ry + rw) / denom / voltageMulti; // Adjusted signs based on common config
        double rfPower = (rx - ry - rw) / denom / voltageMulti;
        double lbPower = (rx - ry + rw) / denom / voltageMulti;
        double rbPower = (rx + ry - rw) / denom / voltageMulti;

        // Apply calculated powers to each motor
        frontLeft.setPower(lfPower);
        frontRight.setPower(rfPower);
        backLeft.setPower(lbPower);
        backRight.setPower(rbPower);
    }
    /**
     * Drives the robot using field-centric Cartesian coordinates (x, y) and robot-centric rotation (w).
     * Takes desired movement relative to the field (forward, strafe) and desired rotation rate,
     * rotates the movement vector based on the robot's current heading, and then calls {@link #driveXYW}
     * with the robot-centric commands.
     *
     * @param fx Field Forward/Backward power (-1 to 1). Positive is away from the driver wall.
     * @param fy Field Strafe Left/Right power (-1 to 1). Positive is typically right relative to the field.
     * @param fw Robot Rotational power (-1 to 1). Positive is typically counter-clockwise.
     */
    public void driveFieldXYW(double fx, double fy, double fw)
    { // rotate field orientation inputs to robot orientation
        /*
           fx: Desired forward/backward motion relative to the field.
           fy: Desired strafe motion relative to the field.
           fw: Desired rotation rate relative to the robot.

           Calculates the robot-centric (rx, ry) commands needed to achieve the
           field-centric (fx, fy) motion, based on the current robot heading.
        */

        // Get the current robot heading in radians. Negated to match common field coordinate systems.
        double robotHeadingRad = Math.toRadians(-getHeading()); // Use odometry heading

        // Rotate the field-relative vector (fx, fy) into the robot's coordinate frame.
        // Standard 2D rotation matrix application.
        double rx = fx * Math.cos(robotHeadingRad) - fy * Math.sin(robotHeadingRad);
        double ry = fx * Math.sin(robotHeadingRad) + fy * Math.cos(robotHeadingRad);

        // Call the robot-centric drive function with the rotated vector and the original rotation command.
        // Rotation (fw) is already robot-centric.
        driveXYW(rx, ry, fw);
    }
}
