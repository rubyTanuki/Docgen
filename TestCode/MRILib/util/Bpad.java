package MRILib.util;

import java.util.*;

public class Bpad {
    private HashMap<String, Boolean> map = new HashMap<>();

    public double left_stick_x;
    public double left_stick_y;
    public double right_stick_x;
    public double right_stick_y;

    public double left_trigger;
    public double right_trigger;

    public boolean get(String button){
        return map.containsKey(button)?map.get(button):false;
    }

    public void update(Gamepad gpad) {

        left_stick_x = gpad.left_stick_x;
        left_stick_y = gpad.left_stick_y;
        right_stick_x = gpad.right_stick_x;
        right_stick_y = gpad.right_stick_y;

        left_trigger = gpad.left_trigger;
        right_trigger = gpad.right_trigger;

        //letter buttons
        map.put("last_a", map.get("a"));
        map.put("a", gpad.a);
        map.put("db_a", gpad.a && !map.get("last_a"));

        map.put("last_b", map.get("b"));
        map.put("b", gpad.b);
        map.put("db_b", gpad.b && !map.get("last_b"));

        map.put("last_x", map.get("x"));
        map.put("x", gpad.x);
        map.put("db_x", gpad.x && !map.get("last_x"));

        map.put("last_y", map.get("y"));
        map.put("y", gpad.y);
        map.put("db_y", gpad.y && !map.get("last_y"));
        

        //dpads
        map.put("last_dpad_up", map.get("dpad_up"));
        map.put("dpad_up", gpad.dpad_up);
        map.put("db_dpad_up", gpad.dpad_up && !map.get("last_dpad_up"));

        map.put("last_dpad_down", map.get("dpad_down"));
        map.put("dpad_down", gpad.dpad_down);
        map.put("db_dpad_down", gpad.dpad_down && !map.get("last_dpad_down"));

        map.put("last_dpad_left", map.get("dpad_left"));
        map.put("dpad_left", gpad.dpad_left);
        map.put("db_dpad_left", gpad.dpad_left && !map.get("last_dpad_left"));

        map.put("last_dpad_right", map.get("dpad_right"));
        map.put("dpad_right", gpad.dpad_right);
        map.put("db_dpad_right", gpad.dpad_right && !map.get("last_dpad_right"));
        

        //bumper/trigger
        map.put("last_left_bumper", map.get("left_bumper"));
        map.put("left_bumper", gpad.left_bumper);
        map.put("db_left_bumper", gpad.left_bumper && !map.get("last_left_bumper"));

        map.put("last_right_bumper", map.get("right_bumper"));
        map.put("right_bumper", gpad.right_bumper);
        map.put("db_right_bumper", gpad.right_bumper && !map.get("last_right_bumper"));

        map.put("last_left_trigger", map.get("left_trigger"));
        map.put("left_trigger", gpad.left_trigger != 0);
        map.put("db_left_trigger", gpad.left_trigger && !map.get("last_left_trigger"));

        map.put("last_right_trigger", map.get("right_trigger"));
        map.put("right_trigger", gpad.right_trigger != 0);
        map.put("db_right_trigger", gpad.right_trigger && !map.get("last_right_trigger"));
        

        //util
        map.put("last_start", map.get("start"));
        map.put("start", gpad.start);
        map.put("db_start", gpad.start && !map.get("last_start"));

        map.put("last_back", map.get("back"));
        map.put("back", gpad.back);
        map.put("db_back", gpad.back && !map.get("last_back"));

        map.put("last_guide", map.get("guide"));
        map.put("guide", gpad.guide);
        map.put("db_guide", gpad.guide && !map.get("last_guide"));
        

        //stick buttons
        map.put("last_left_stick_button", map.get("left_stick_button"));
        map.put("left_stick_button", gpad.left_stick_button);
        map.put("db_last_left_stick_button", gpad.left_stick_button && !map.get("last_left_stick_button"));

        map.put("last_right_stick_button", map.get("right_stick_button"));
        map.put("right_stick_button", gpad.right_stick_button);
        map.put("db_right_stick_button", gpad.right_stick_button && !map.get("last_right_stick_button"));


        //sticks
        map.put("last_left_stick_x", map.get("left_stick_x"));
        map.put("left_stick_x", gpad.left_stick_x != 0);
        map.put("db_left_stick_x", gpad.left_stick_x && map.get("last_left_stick_x"));

        map.put("last_left_stick_y", map.get("left_stick_y"));
        map.put("left_stick_y", gpad.left_stick_y != 0);
        map.put("db_left_stick_y", gpad.left_stick_y && map.get("last_left_stick_y"));

        map.put("last_right_stick_x", map.get("right_stick_x"));
        map.put("right_stick_x", gpad.right_stick_x != 0);
        map.put("db_right_stick_x", gpad.right_stick_x && map.get("last_right_stick_x"));

        map.put("last_right_stick_y", map.get("right_stick_y"));
        map.put("right_stick_y", gpad.right_stick_y != 0);
        map.put("db_right_stick_x", gpad.right_stick_x && map.get("last_right_stick_x"));
    }
}