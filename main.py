from Languages.Java import JavaFile
from llm_client import GeminiClient
import asyncio
import time
import os

java = b"""
package com.hyperion.core;

import com.hyperion.hardware.FluxCapacitor;
import com.hyperion.hardware.ResonanceField;
import com.hyperion.managers.GlobalEntropyPool;
import com.hyperion.network.SubspaceTransmitter;
import com.hyperion.utils.CalibrationStruct;

/**
 * COORDINATOR CLASS
 * This class is intentionally opaque. It orchestrates hardware that the LLM cannot see.
 */
public class HyperionCoordinator {

    private final FluxCapacitor capacitor;
    private final ResonanceField resonance;
    private final SubspaceTransmitter uplink;
    
    // Obscure state tracking
    private int cycleCount = 0;
    private boolean isCritical = false;

    public HyperionCoordinator(FluxCapacitor capacitor, ResonanceField resonance, SubspaceTransmitter uplink) {
        this.capacitor = capacitor;
        this.resonance = resonance;
        this.uplink = uplink;
    }

    /**
     * This method is the ultimate test. 
     * It relies entirely on the side effects of 'capacitor.inject()' and 'resonance.getHarmonic()'.
     * Without knowing what '0x5F' or 'mode 3' does, the LLM is guessing.
     */
    public boolean synchronizeFlux(int stabilizationSeed) {
        // 1. Dependency on static global state
        if (GlobalEntropyPool.getCurrentLevel() > 85.5) {
            uplink.broadcastWarning("ENTROPY_CRITICAL");
            return false;
        }

        // 2. Opaque magic numbers and bitwise logic on external return values
        int currentHarmonic = resonance.getHarmonic(3); // What is mode 3?
        if ((currentHarmonic & 0x0F) != stabilizationSeed) {
            
            // 3. Void method with unknown side effects
            capacitor.inject(0x5F, stabilizationSeed * 2); 
            
            // 4. Recursive dependency check
            if (!capacitor.isStable()) {
                isCritical = true;
                emergencyShutdown(); // Internal call
                return false;
            }
        }

        cycleCount++;
        return true;
    }

    /**
     * A method that looks simple but acts on a "Context Object" (struct).
     * The LLM doesn't know what 'config.delta' maps to physically.
     */
    public void calibrate(CalibrationStruct config) {
        if (config.isValid()) {
            // Does this move a motor? Delete a file?
            resonance.adjust(config.delta, config.vector); 
            
            // This updates a field in the PASSED object. 
            // The LLM should catch this side effect if it's smart.
            config.markDirty(); 
        }
    }

    private void emergencyShutdown() {
        // Heavy side effects
        GlobalEntropyPool.reset();
        uplink.transmit(new byte[]{0x00, 0x00, 0xFF}); // Magic packet
        capacitor.scram();
    }
}
"""

if __name__ == "__main__":
    start_time = time.perf_counter()
    file = JavaFile.from_source("MRILib/util/mathf.java", java)
    class_obj = file.classes[0]
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"created AST in {elapsed_time:.4f} seconds.")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise ValueError("API key not found. Set the GEMINI_API_KEY environment variable.")

    llm = GeminiClient(api_key=GEMINI_API_KEY)
    
    start_time = time.perf_counter()
    class_obj.resolve_descriptions(llm, file.imports)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Generated descriptions in {elapsed_time:.4f} seconds.")
    
    
    # for i in range(1):
    #     start_time = time.perf_counter()
    #     response =  llm.generate_description(class_obj, [])
    #     end_time = time.perf_counter()
    #     elapsed_time = end_time - start_time

    #     print(response)
    #     print(f"responded in {elapsed_time:.4f} seconds.")
    
    
    