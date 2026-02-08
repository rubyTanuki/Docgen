import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import java.io.IOException;

// Edge Case: Static Import
import static java.lang.Math.max;
import static java.util.Collections.singletonList;

/**
 * A complex class to test the limits of the Docgen parser.
 */
@Deprecated
public class DataProcessor<T> implements Runnable {

    // Edge Case: Constants and Generics
    private static final int MAX_RETRIES = 5;
    protected Map<String, List<T>> cache;
    private final Object lock = new Object();

    // Edge Case: No Access Modifier (Package-Private)
    String workerName;

    // Edge Case: Constructor Overloading
    public DataProcessor() {
        this("DefaultWorker");
    }

    public DataProcessor(String name) {
        this.workerName = name;
        this.cache = new HashMap<>();
    }

    /**
     * Edge Case: Method Overloading and Throws
     */
    public void process(T data) throws IOException {
        process(data, false);
    }

    protected void process(T data, boolean force) {
        if (data == null) return; // Edge Case: One-line if
        
        synchronized(lock) {
            // Edge Case: Nested Generic Instantiation
            List<T> buffer = this.cache.getOrDefault(workerName, new ArrayList<>());
            buffer.add(data);
            
            // Edge Case: Static Method Call from Import
            int capacity = max(buffer.size(), 100); 
            
            // Edge Case: Method Chaining (The "Builder" pattern)
            String log = new StringBuilder()
                .append("Processed ")
                .append(data.toString())
                .append(" at capacity ")
                .append(capacity)
                .toString();
                
            System.out.println(log);
            
            // Edge Case: Internal dependency
            this.flush();
        }
    }

    private void flush() {
        // Edge Case: Accessing field directly vs getter
        if (!cache.isEmpty()) {
            cache.clear();
        }
    }

    @Override
    public void run() {
        try {
            // Edge Case: Passing 'this' reference
            ExecutionHelper.register(this);
            process(null);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // Edge Case: Nested Static Class
    public static class ExecutionHelper {
        public static void register(DataProcessor<?> dp) {
            System.out.println("Registered: " + dp.workerName);
        }
    }

    // Edge Case: Nested Enum
    private enum Status {
        IDLE,
        PROCESSING,
        FAILED
    }
}
