package MRILib.opmodes;

import MRILib.util.*;
import java.util.*;

@TeleOp(name = "Servo Zero")
public class ServoZero extends OpMode{
    private Bpad gpad;

    Servo elbow;
    Servo wrist;
    Servo roll;
    Servo claw;

    Servo[] servoList;
    double[] positionList;

    

    public void init(){
        elbow = hardwareMap.get(Servo.class, "elbow");
        wrist = hardwareMap.get(Servo.class, "wrist");
        roll = hardwareMap.get(Servo.class, "roll");
        claw = hardwareMap.get(Servo.class, "claw");
        servoList = {elbow, wrist, roll, claw};
        positionList = new double[4];

    }

    int index = 0;
    public void loop(){
        if(gpad.get("db_dpad_up")&&index<servoList.length()-1) index++;
        if(gpad.get("db_dpad_down")&&index>0) index--;

        if(gpad.get("db_a"))positionList[index]+=.1;
        if(gpad.get("db_y"))positionList[index]-=.1;

        if(positionList[index]>1)positionList[index]-=1;
        if(positionList[index]<0)positionList[index]+=1;

        if(gpad.get("left_trigger")){
            for(int i=0;i<servoList.length();i++){
                servoList[i].setPosition(positionList[i]);
            }
        }
        if(gpad.get("right_trigger"))servoList[index].setPosition(positionList[index]);

        telemetry.addData(index==0?">":" "+"elbow", positionList[0]);
        telemetry.addData(index==1?">":" "+"wrist", positionList[1]);
        telemetry.addData(index==2?">":" "+"roll", positionList[2]);
        telemetry.addData(index==3?">":" "+"claw", positionList[3]);
        telemetry.update();
    }
}
