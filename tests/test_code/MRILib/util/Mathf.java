package MRILib.util;

public final class Mathf {

    public static final double TAU = Math.PI * 2;
    
    public static double angleWrap(double radian){
        double angle = radian % TAU;
        angle = (angle + TAU) % TAU;
        if(angle > Math.PI)
            angle -= TAU;
        return angle;
    }
}