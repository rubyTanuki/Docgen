package MRILib.motion;

import com.qualcomm.robotcore.util.ElapsedTime;

/**
 * Implements a standard Proportional-Integral-Derivative (PID) controller.
 * <p>
 * A PID controller calculates an "error" value as the difference between a measured process variable
 * and a desired setpoint. The controller attempts to minimize the error over time by adjustment
 * of a control variable (output).
 * <p>
 * This implementation includes:
 * <ul>
 *     <li>Proportional (P) term: Proportional to the current error.</li>
 *     <li>Integral (I) term: Accumulates past errors (integrates) to eliminate steady-state error. Includes an integral windup limit ({@link #iLimit}) and clamping ({@link #errorSumTotal}).</li>
 *     <li>Derivative (D) term: Based on the rate of change of the error, used to dampen oscillations.</li>
 * </ul>
 * This version also includes an overload for the `update` method that selects between two input values.
 *
 * @see <a href="https://en.wikipedia.org/wiki/PID_controller">PID Controller (Wikipedia)</a>
 * @see ElapsedTime
 */
public class PID {

    /** Proportional gain (kP). Determines the reaction to the current error. Typically positive. */
    public double kP;
    /** Integral gain (kI). Determines the reaction based on the sum of recent errors. Typically positive. */
    public double kI;
    /** Derivative gain (kD). Determines the reaction based on the rate at which the error has been changing. Typically positive. */
    public double kD;
    /**
     * Integral limit (I-Zone). The absolute error must be less than this value
     * for the integral term to accumulate. Helps prevent integral windup when the error is large.
     * Must be non-negative. Defaults to 1.
     */
    public double iLimit = 1;

    /** The desired setpoint or target value for the controller. */
    public double targetVal = 0;

    /** The accumulated integral error sum. */
    double errorSum = 0; // Package-private state
    /**
     * The maximum absolute value the integral error sum ({@link #errorSum}) is allowed to reach.
     * Helps prevent integral windup by clamping the accumulated error. Must be non-negative. Defaults to 0.1.
     */
    public double errorSumTotal = .1;

    /** Timestamp of the last {@link #update(double)} call, used for calculating delta time. */
    double lastTime = 0; // Package-private state
    /** The error calculated during the previous {@link #update(double)} call, used for calculating the derivative term. */
    double lastError = 0; // Package-private state

    /** Timer used to calculate the time difference (deltaTime) between updates. */
    ElapsedTime timer = null; // Package-private state

    /**
     * Constructs a new PID controller with specified gains.
     * Initializes the internal timer.
     *
     * @param p The proportional gain (kP).
     * @param i The integral gain (kI).
     * @param d The derivative gain (kD).
     */
    public PID(double p, double i, double d){
        // Assign gains directly as fields are public in this version
        kP = p;
        kI = i;
        kD = d;
        timer = new ElapsedTime();
        // Ensure timer starts immediately for accurate first delta time
        start();
    }

    /**
     * Resets the PID controller's internal state.
     * Zeros the integral sum and last error, and resets the timer.
     * Should be called before starting a new control sequence or after significant changes
     * (like changing the target value drastically, depending on the application).
     */
    public void start(){
        errorSum = 0;
        lastError = 0;
        lastTime = 0; // Reset lastTime for accurate first deltaTime
        timer.reset();
    }

    /**
     * Updates the PID controller calculation based on a single measured value.
     * Calculates the P, I, and D terms based on the current measurement and the target value,
     * and returns the calculated control output.
     *
     * @param current The current measured value of the process variable.
     * @return The calculated control output value (e.g., motor power, servo position adjustment).
     */
    public double update(double current){
        // Calculate the current error
        double error = targetVal - current;

        // Calculate the time elapsed since the last update
        double currentTime = timer.seconds();
        double deltaTime = currentTime - lastTime;

        // Prevent division by zero or unstable derivative on first loop or if timer resets
        // A very small positive deltaTime avoids division by zero in errorRate calculation.
        if (deltaTime <= 0) {
            deltaTime = 0.0001; // Use a small default value
        }

        // --- Integral Term (with Anti-Windup) ---
        // Accumulate error sum only if error is within the iLimit
        if (Math.abs(error) < iLimit) {
            errorSum += error * deltaTime;
        }
        // Clamp the integral sum to prevent excessive windup
        errorSum = Math.max(-errorSumTotal, Math.min(errorSumTotal, errorSum));


        // --- Derivative Term ---
        // Calculate the rate of change of the error
        double errorRate = (error - lastError) / deltaTime;


        // --- PID Calculation ---
        // Calculate the total control output
        double value = (kP * error) + (kI * errorSum) + (kD * errorRate);


        // --- Update State for Next Iteration ---
        lastTime = currentTime;
        lastError = error;

        return value;
    }

    /**
     * Updates the PID controller calculation by choosing between two measured values.
     * It selects the input value (`current1` or `current2`) that is closer (smaller absolute difference)
     * to the `targetVal` and then calls the primary {@link #update(double)} method with the selected value.
     *
     * @param current1 The first possible measured value.
     * @param current2 The second possible measured value.
     * @return The calculated control output based on the input value closer to the target.
     */
    public double update(double current1, double current2){
        // Compare absolute errors to find which input is closer to the target
        if (Math.abs(current1 - targetVal) < Math.abs(current2 - targetVal)) {
            // current1 is closer, use it for the PID update
            return update(current1);
        } else {
            // current2 is closer or they are equidistant, use current2
            return update(current2);
        }
    }

    /**
     * Sets the desired target value (setpoint) for the PID controller.
     *
     * @param target The new target value.
     */
    public void setTarget(double target){
        // Optional: Consider resetting integral term when target changes significantly?
        // start(); // Uncomment this if you want a full reset on target change
        targetVal = target;
    }

    /**
     * Sets the integral limit (I-Zone).
     * The integral term will only accumulate when the absolute error is below this limit.
     * Ensures the limit is non-negative.
     *
     * @param limit The maximum absolute error for integral accumulation.
     */
    public void setILimit(double limit){
        iLimit = Math.abs(limit); // Ensure limit is non-negative
    }

    /**
     * Sets the clamping limit for the integral sum.
     * The absolute value of the accumulated integral error (errorSum) will not exceed this limit.
     * Ensures the limit is non-negative.
     *
     * @param limit The maximum absolute value for the integral sum.
     */
    public void setIntegralSumLimit(double limit) {
        errorSumTotal = Math.abs(limit); // Ensure limit is non-negative
    }
}
