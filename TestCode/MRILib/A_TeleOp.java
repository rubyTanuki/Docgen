import MRILib.*;
import MRILib.managers.*;
import MRILib.statemachine.*;

@TeleOp(name = "A_Teleop (in development)")
public class A_TeleOp extends LinearOpMode{
    public ArmBotFF bot;
    public ArmFSM asm;

    @Override
    public void runOpMode(){
        init();

        waitForStart();
        bot.startMultiThread();

        while(opModeIsActive()){
            bot.update();
            asm.update();

            double multi = gamepad1.left_trigger;
            double jx = -gamepad1.left_stick_y;
            double jy = -gamepad1.left_stick_x;
            double jw = -gamepad1.right_stick_x;

            if(gamepad1.start) { bot.resetHeading(); }
            if(gamepad1.dpad_up){ bot.imu.resetYaw(); }

            double clampedMulti = Math.max(.25, (1-multi));
            bot.driveFieldXYW(jx*clampedMulti, jy*clampedMulti, jw*clampedMulti);

            //add arm commands here
            if(gamepad1.x){
                asm.setState("IDLE");
            }


            Pose2D pos = odo.getPosition();

            telemetry.addData("Status", "Run Time: " + runtime.toString());
            telemetry.addLine();
            telemetry.addData("X ", pos.getX(DistanceUnit.INCH));
            telemetry.addData("Y ", pos.getY(DistanceUnit.INCH));
            telemetry.addData("Heading", pos.getHeading(AngleUnit.DEGREES));
            telemetry.addLine();
            telemetry.addData("Current State", asm.toString());

            telemetry.update();

        }

        bot.stopMultiThread();
    }

    public void init(){
        bot = new ArmBotFF(hardwareMap, telemetry);
        bot.setMode(DcMotor.RunMode.RUN_WITHOUT_ENCODER);
        bot.enableBrakeMode(true);

        asm = new ArmFSM(bot, gamepad1, gamepad2);
    }

}
