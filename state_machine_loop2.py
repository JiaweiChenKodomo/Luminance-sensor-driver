
# Description:

import sys
import time
import receive as rc #receive package for SLAB

# Constants
continue_run = 30; # No. of continue loops before asking whether to continue.

# Timer constants
loopStartTime = 0
loopEndTime = 0
loopWaitTime = 0
#loopTimeInSeconds = 300 # 5 minutes
#loopTimeInSeconds = 120 # 2 minutes
#loopTimeInSeconds = 60 # 1 minute
loopTimeInSeconds = 30 # 0.5 minute

CycleIntervalInMinutes = 15



#%%
def main():

    continue_run_local = continue_run # continue_run_local is Updated inside main(). So continue_run can't be used, unless we are willing to declare it a global.

    loopWaitTime = 0
    # The main is a state machine architecture

    STATE = "idle"
    RUNNING = [True,0,1]

    # Configurate the SLAB
    rc.config_system()

    # The actual Finite State Machine (FSM) while loop.
    while(RUNNING[0] == True):

        if("idle" == STATE):
            # Initialize the loop timer
            print('Waiting for next round...\n');
            if loopWaitTime > 0:
                time.sleep(loopWaitTime)

            print("Exiting IDLE... \n")

            # Change state to "LJ" for LabJack to get the illuminance measurement.
            STATE = "SLAB"

        elif("SLAB" == STATE):
            # Get one reading from the SLAB system
            rc.receive_one_data(rc.sensor_ip_list, False)
            STATE = "WAIT"
        elif ("WAIT" == STATE):
            if (RUNNING[1] < continue_run_local):
                STATE = "idle"
                continue
            cmd = input("Continue? Y/N\n")
            if cmd == "Y":
                STATE = "idle"
                continue_run_local += continue_run_local
            else:
                break

        # Increments the counter so we can see how many times the FSM "ticks".
        RUNNING[1] = RUNNING[1] + 1
        print("Cycle number: " + str(RUNNING[1]))

    """Stop the SLAB system and close socket."""
    rc.sensor_stop(rc.sensor_ip_list)
    rc.close_connection()

    sys.exit(0)

# Boiler plate used to run script as function.
if __name__ == "__main__":
    main()
