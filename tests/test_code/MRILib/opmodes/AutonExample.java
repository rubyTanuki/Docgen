package MRILib.opmodes;

import static MRILib.BotValues.*;
import MRILib.managers.*;
import MRILib.motion.*;
import MRILib.statemachine.*;
import java.util.*;

import com.qualcomm.robotcore.eventloop.opmode.Disabled;
import com.qualcomm.robotcore.eventloop.opmode.LinearOpMode;
import com.qualcomm.robotcore.eventloop.opmode.Autonomous;
import com.qualcomm.robotcore.hardware.DcMotor;
import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;
import org.firstinspires.ftc.robotcore.external.navigation.DistanceUnit;
import org.firstinspires.ftc.robotcore.external.navigation.Pose2D;

@Autonomous(name = "AutonExample")

public class AutonExample extends LinearOpMode {

    //public ArmBotEasy bot;
    public Bot bot;
    public PIDController pid;
    public DriveFSM dsm;
    //public ArmFSM asm;
    
    //make these your intended dropping position for buckets
    private static final double BUCKET_X = 55.5;
    private static final double BUCKET_Y = 52.5;
    private static final double BUCKET_HEADING = 135;

    
    @Override
    public void runOpMode() {
//init
    //hardwaremaps and init methods
        
        
        bot = new Bot(hardwareMap);
        //bot = new ArmBotEasy(hardwareMap);
        //asm = new ArmFSM(bot, gamepad1, gamepad2);
        
        bot.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);
        bot.enableBrakeMode(true);
        
        // tune these gains to adjust acceleration, decceleration, and tune out wobble
        // for reference of how to adjust these and what they represent, check out page 30 (chapter 2) of
        // this book: https://file.tavsys.net/control/controls-engineering-in-frc.pdf
        // github link for the book: https://github.com/calcmogul/controls-engineering-in-frc?tab=readme-ov-file
        PID xPid = new PID(.7, .08, .02);// default = (.1,0.08,.01);
        
        // yPid needs a bit more p because strafing is a bit slower than driving forward and back
        PID yPid = new PID(.8, .08, .02);// default = (.12,0.08,.01);

        PID thetaPID = new PID(1.5,0.98,.09);// default = (2, 0.98, 0.08);
        thetaPID.errorSumTotal = .1;


        pid = new PIDController(bot, telemetry);
        
        pid.setPID(xPid, yPid);
        pid.setTurnPID(thetaPID);
        pid.maxAngSpeed = .4;
        pid.maxSpeed = .3;
        
        dsm = new DriveFSM(bot, pid);
        
        
        
        telemetry.addData("Status", "Initialized");
        telemetry.update();
        
//init_loop
    //choosing settings with controller
        
        // in development
        
        
        waitForStart();
//start
    //adding all the movement paths

        //setting the starting position
        Pose2D startPos = new Pose2D(DistanceUnit.INCH, 24, 64, AngleUnit.DEGREES, 180);
        bot.setPosition(startPos);
        dsm.moveTo(startPos);
        
        dsm.waitForSeconds(2, ()->asm.setState("ARM_UP")); //move arm up to drop preload
        
        dsm.moveTo(BUCKET_X, BUCKET_Y, BUCKET_HEADING); //move to bucket
        
        dsm.waitForSeconds(1, ()->asm.setState("DROP")); //drop preload
        
        dsm.moveTo(50, 52, 120, ()->asm.setState("ARM_PICKUP")); //pick up first ground sample
        
        dsm.waitForSeconds(2); //ensure it intakes properly
        
        dsm.moveTo(BUCKET_X, BUCKET_Y, BUCKET_HEADING, ()->asm.setState("ARM_UP")); //move to bucket and set arm to proper state
        
        dsm.waitForSeconds(3); //wait for arm
        
        dsm.waitForSeconds(1, ()->asm.setState("DROP")); //drop sample
        
        
        
        dsm.waitForSeconds(30);
        
        dsm.start();
        
    
        
//loop
    //repeating while active
        while (opModeIsActive()) {
            
            //bot.getFR().setPower(.5);
            // localization with a webcam with autobot
            // comment out if using ArmBotFF or ArmBotEasy
            try{
                // List<AprilTagDetection> currentDetections = bot.aprilTag.getDetections();
                // for (AprilTagDetection detection : currentDetections) {
                //     //set odometry
                //     double range = detection.ftcPose.range;
                //     double bearing = detection.ftcPose.bearing;
                //     double yaw = detection.ftcPose.yaw;
                //     double tagx = detection.metadata.fieldPosition.get(0);
                //     double tagy = detection.metadata.fieldPosition.get(1);
                //     double theta = Math.toRadians(odo.getHeading() + bearing);
                //     double fx = tagx - Math.cos(theta) * range;
                //     fx -= 26;
                //     double fy = tagy - Math.sin(theta) * range;
                //     fy += 4;
                //     //bot.resetEncoders();
                //     //bot.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);
                //     //od.setFieldXY(fx, fy);
                //     telemetry.addLine("seeing april tag " + detection.id + " from " + fx + ", " + fy);
                // }
            }
            catch( Exception e){
                
            }

            // updating all helper objects
            bot.update();
            dsm.update();
            asm.update();
            
            // saving current position for displaying on telemetry
            Pose2D currentPos = bot.getPosition();
            
            //displaying telemetry to the drivers hub
            telemetry.addData("Status", "Running");
            telemetry.addLine();
            telemetry.addData("target Degrees", pid.getTargetRadians());
            telemetry.addData("current Degrees", pid.getCurrentRadians());
            telemetry.addData("target x", pid.getTargetX());
            telemetry.addData("target y", pid.getTargetY());
            telemetry.addData("position x", currentPos.getX(DistanceUnit.INCH));
            telemetry.addData("position y", currentPos.getY(DistanceUnit.INCH));
            telemetry.addData("heading", -bot.getHeading());
            telemetry.update();
            
            
            
        }
        //Stop multithread if using ArmBotFF
        //bot.stopMultiThread();
    }


}

