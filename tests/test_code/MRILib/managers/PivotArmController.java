package MRILib.managers;

import MRILib.motion.*;
import org.firstinspires.ftc.robotcore.external.Telemetry;
import static MRILib.BotValues.*;
import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;
import com.qualcomm.robotcore.util.ElapsedTime;
import com.qualcomm.robotcore.util.Range;

public class PivotArmController implements Runnable{
    private ArmBotFF bot;

    private Telemetry telemetry;
    
    private final double kG = 0.00089; //gravity gain
    private final double kG2 = -0.003; //gravity gain 2
    
    private double currentSlidePosition = 0;
    private double currentSlideLength = 350;
    
    private double armPos = 0;
    
    private final double g = .009810; // gravity constant in mm/second^2
    double m_slide  = 1.4; //kg
    double m_claw   = .27; //kg
    double m_motor  = .9; //kg
    double d_motor  = 85; //mm
    double d_slide = 350; //mm
    double d_slideOffset = -85; //mm
    
    
    double m_total = m_slide+m_claw+m_motor; //kg
    double armCoM = (m_slide*(d_slide+d_slideOffset)/2 + m_motor*d_motor + m_claw*(d_slide+d_slideOffset))/m_total;
    
    private double armMountOffset = 90;
    private double thetaOffset = 0; //set in botvalues
    
    public enum PivotMode{
        HOLD_POSITION,
        RUN_TO_POSITION,
        RUN_WITH_POWER
    }
    public volatile PivotMode pivotMode = PivotMode.RUN_TO_POSITION;
    
    private volatile double inputPower = 0;
    
    
    private PID positionPID = new PID(1.5, 0.01, 0.046); //2.5, 0.002, 0.23

    private volatile double targetTheta; //radians
    private volatile double targetAngularVelocity;

    private volatile double currentArmTheta;
    private volatile double currentArmAngularVelocity;
    private double previousArmTheta;
    private double previousArmAngularVelocity;

    private volatile boolean running = true;

    public PivotArmController(ArmBotFF bot){
        //constructor
        this.bot = bot;
        telemetry = bot.getTelemetry();
    }


    @Override 
    public void run(){
        long loopTime = 10;
        long nextLoopTime = System.nanoTime() + loopTime * 1_000_000;
        ElapsedTime timer = new ElapsedTime();
        double previousTime = timer.seconds();
        
        
        while(running){
            
            //init variables
            double currentTime = timer.seconds();
            double deltaTime = currentTime-previousTime;
            previousTime = currentTime;
            double positionPIDValue = positionPID.update(currentArmTheta);
            
            currentSlideLength = d_slide+(currentSlidePosition*DISTANCE_PER_TICK_SLIDE)+d_slideOffset;
            armCoM = (m_slide*(currentSlideLength+d_slideOffset)/2 + m_motor*d_motor + m_claw*(d_slide+d_slideOffset))/m_total;
            
            // FF compensation
            
            double u_ff = calculateFeedForward(); //calculate u feedforward
            
            
            // FB control
            
            double error = Math.toDegrees(currentArmTheta)-Math.toDegrees(targetTheta);
            double u_fb = positionPIDValue;
            // //making sure it doesnt stall when close to target
            if(Math.abs(error)>1){
                u_fb = Math.max(.1, Math.abs(u_fb));
                u_fb*=Math.signum(positionPIDValue);
            }else{
                u_fb = 0;
            }
            
            if(u_fb<0&&Math.toDegrees(currentArmTheta)>0) u_fb*=.53;
            //power by mode
            
            double u = 0;
            switch(pivotMode){
                case RUN_TO_POSITION:
                    double fbMulti = Math.min(.5, Math.PI/5/currentArmTheta*.5); //slowing down past ~65 degrees proportionately
                    u = u_ff + u_fb;
                    break;
                case HOLD_POSITION:
                    u = u_ff;
                    break;
                case RUN_WITH_POWER:
                    u = u_ff*.3 + inputPower;
                    break;
            }
            double power = setMotorPower(u);
            

            while(System.nanoTime() < nextLoopTime){
                //wait until next loop time
            }
            nextLoopTime += loopTime * 1_000_000;
        }
        
    }

    public double setMotorPower(double power){
        //use voltage sensor to clamp volts to 0-12
        double clampMulti = 12.0/bot.getVoltage();
        //calculate 0-1 relative to current voltage output and the target voltage
        double powerValue = (power)*clampMulti;
        if(powerValue>0)powerValue*=1.5;

        bot.setPivotPower(Range.clip(powerValue, -.9, 1)); //apply power value to motor
        return powerValue;
    }
    
    private double calculateFeedForward(){
        double gravityFeedForward1 = kG * armCoM * Math.cos(currentArmTheta);
        if(currentArmTheta-targetTheta>0 && gravityFeedForward1>0 &&Math.toDegrees(currentArmTheta)>0&&targetTheta>=0) gravityFeedForward1*=1.93;
        else if(currentArmTheta>targetTheta && Math.toDegrees(currentArmTheta)<0)gravityFeedForward1*=.83;
        double gravityFeedForward2 = kG2 * armMountOffset * Math.sin(currentArmTheta);
        double gravityFeedForward = (gravityFeedForward1 + gravityFeedForward2);
        return gravityFeedForward;
    }

    public synchronized double updateCurrentState(double armPos, double velocity, double slidePosition){
        previousArmTheta = currentArmTheta;
        previousArmAngularVelocity = currentArmAngularVelocity;
        currentArmTheta = Math.toRadians(armPos/TICKS_PER_DEGREE_ARM)+thetaOffset;
        this.armPos = armPos;
        currentArmAngularVelocity = Math.toRadians(velocity/TICKS_PER_DEGREE_ARM); 
        currentSlidePosition = slidePosition;
        return Math.toDegrees(currentArmTheta);
    }
    public synchronized void updateCurrentState(double armPos, double velocity){
        updateCurrentState(armPos, velocity, 0);
    }

    public synchronized void setPivotMode(PivotMode mode){
        pivotMode = mode;
    }
    public synchronized void setInputPower(double input){
        inputPower = input;
    }

    public void setTargetTheta(double theta, AngleUnit unit){
        targetTheta = unit==AngleUnit.DEGREES?Math.toRadians(theta):theta;
        positionPID.setTarget(targetTheta);
    }
    public void setTargetTheta(double theta)
    { // overload to default to degrees if not specified
        setTargetTheta(theta, AngleUnit.DEGREES);
    }
    public void setThetaOffset(double theta){
        thetaOffset = Math.toRadians(theta);
    }

    public void stop(){
        running = false;
    }
}
