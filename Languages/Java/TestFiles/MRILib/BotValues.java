package MRILib;
import com.qualcomm.robotcore.hardware.DcMotor;
import com.qualcomm.hardware.rev.RevHubOrientationOnRobot.LogoFacingDirection;
import com.qualcomm.hardware.rev.RevHubOrientationOnRobot.UsbFacingDirection;

public class BotValues{
    public static DcMotor.Direction LEFTDIR = DcMotor.Direction.FORWARD;
    public static DcMotor.Direction RIGHTDIR = DcMotor.Direction.REVERSE;
    public static DcMotor.Direction SLIDEDIR = DcMotor.Direction.FORWARD;
    public static DcMotor.Direction PIVOTDIR = DcMotor.Direction.FORWARD;
    public static LogoFacingDirection LOGO_DIR = LogoFacingDirection.UP;
    public static UsbFacingDirection USB_DIR = UsbFacingDirection.LEFT;

    // define robot-specific motor/wheel constants
    public static final double TICKS_PER_REVOLUTION = 384.5; //384.5
    public static final double GEAR_RATIO = 1.0;
    public static final double WHEEL_DIAMETER = 3.78; //3.78

    // define calculated constants
    public static final double WHEEL_CIRCUMFERENCE =
          WHEEL_DIAMETER * Math.PI;
    public static final double DISTANCE_PER_REVOLUTION =
          WHEEL_CIRCUMFERENCE * GEAR_RATIO * 1.7;

    public static final DcMotor.ZeroPowerBehavior BRAKE = DcMotor.ZeroPowerBehavior.BRAKE;
    public static final DcMotor.ZeroPowerBehavior FLOAT = DcMotor.ZeroPowerBehavior.FLOAT;

    public static final double TICKS_PER_REVOLUTION_ARM = 384.5;
    public static final double GEAR_RATIO_ARM = 1.0;
    public static final double TICKS_PER_DEGREE_ARM = TICKS_PER_REVOLUTION_ARM/(GEAR_RATIO_ARM*360);
}