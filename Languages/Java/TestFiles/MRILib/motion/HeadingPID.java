package MRILib.motion;

import MRILib.util.*;
// Unused import: com.qualcomm.robotcore.util.ElapsedTime; // Inherited timer is used

/**
 * Extends the standard {@link PID} controller specifically for controlling heading or angles.
 * <p>
 * The key difference is the overridden {@link #update(double)} method, which uses
 * {@link Mathf#angleWrap(double)} to calculate the error. This ensures that the error
 * calculation correctly handles the discontinuity at +/- 180 degrees (or +/- PI radians),
 * always finding the shortest angular distance between the current heading and the target heading.
 * <p>
 * Assumes that both the target value ({@link #targetVal}) and the current measurement input
 * to {@code update} are in the same angular units (e.g., degrees or radians) consistent
 * with the {@code Mathf.angleWrap} implementation (which typically works with degrees).
 *
 * @see PID
 * @see Mathf#angleWrap(double)
 */
public class HeadingPID extends PID{

    /**
     * Constructs a new HeadingPID controller with specified gains.
     * Calls the superclass ({@link PID}) constructor.
     *
     * @param p The proportional gain (kP).
     * @param i The integral gain (kI).
     * @param d The derivative gain (kD).
     */
    public HeadingPID(double p, double i, double d){
        super(p,i,d); // Pass gains to the base PID constructor
    }

    /**
     * Updates the PID controller calculation specifically for angles/heading.
     * <p>
     * Calculates the error using {@link Mathf#angleWrap(double)} to find the shortest
     * angular distance between the target and current values. Otherwise, performs the standard
     * PID calculation (Integral with limits, Derivative) inherited from the {@link PID} class.
     * </p>
     *
     * @param current The current measured angle/heading value (in degrees, matching {@code Mathf.angleWrap}).
     * @return The calculated control output value (e.g., rotational power).
     */
    @Override
    public double update(double current){
        // Calculate the shortest angular error using angleWrap
        // Assumes targetVal and current are in degrees
        double error = Mathf.angleWrap(targetVal - current);

        // Calculate the time elapsed since the last update
        double currentTime = timer.seconds(); // Use timer inherited from PID
        double deltaTime = currentTime - lastTime;

        // Prevent division by zero or unstable derivative on first loop or if timer resets
        if (deltaTime <= 0) {
            // Handle potential zero or negative deltaTime. Using a small default or
            // returning previous value might be options.
            // Using a small positive value avoids division by zero in errorRate calculation.
            deltaTime = 0.0001;
            // Alternatively, could skip derivative calculation for this cycle:
            // double errorRate = 0;
            // Or return the previous output if deltaTime is invalid.
        }

        // --- Integral Term (Anti-Windup) ---
        // Accumulate error sum only if error is within the iLimit
        if (Math.abs(error) < iLimit) {
            errorSum += error * deltaTime;
        }
        // Clamp the integral sum
        if(errorSum < -errorSumTotal)
            errorSum = -errorSumTotal;
        if(errorSum > errorSumTotal)
            errorSum = errorSumTotal;


        // --- Derivative Term ---
        // Calculate the rate of change of the *wrapped* error
        double errorRate = (error - lastError) / deltaTime;


        // --- PID Calculation ---
        // Calculate the total control output
        double value = (kP * error) + (kI * errorSum) + (kD * errorRate);


        // --- Update State for Next Iteration ---
        lastTime = currentTime;
        lastError = error; // Store the wrapped error

        return value;
    }

    /*
     * Commented out overload - appears incomplete or experimental.
     * This method would need a clear definition of what current1 and current2 represent
     * and why one would be chosen over the other based on proximity to the target.
     */
    // public double update(double current1, double current2){
    //     // Calculate wrapped errors for both inputs
    //     double error1 = Mathf.angleWrap(targetVal - current1);
    //     double error2 = Mathf.angleWrap(targetVal - current2);
    //
    //     // Choose the input with the smaller absolute error and update using it
    //     if (Math.abs(error1) < Math.abs(error2)) {
    //         return update(current1); // Calls the primary update method
    //     } else {
    //         return update(current2); // Calls the primary update method
    //     }
    // }


}
