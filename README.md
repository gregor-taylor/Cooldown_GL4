For cooling down a Chase cryogenics GL4 cryocooler (http://www.chasecryogenics.com).</br>
Tested with GL4 installed on Sumitomo RDK101-D.</br>
Designed to be run on a raspsberry pi with touchscreen, but doesn't need to be.</br>
Interfaces with a SIM900 (with SIM922 for diodes/SIM921 AC R Bridge for CERNOX)for temperature readout of the various stages and a Keithley 2230G-30-3 power supply for control 
of the heaters/heat switches. Refer to the Chase documentation for details.</br>

Requirements:</br>
- PyQt5
- PyVisa
- hardware (Written by R Heath and bundled here)</br>

Rough guide:</br>
- Select Keithley and SIM900 address from opening page - NOTE SIM922/921 slots are hardcoded but will add option in Settings tab later.
- In settings tab logging can be enabled and a timer to switch on can be set. Also the temperatures at which the stages will kick in can be tuned. Refer to Chase documentation for explanation of tuning process.
- Begin cooldown will initiate Stage1.
- Stage2 can be manually jumped to if you don't want to wait for the ColdHead to cool fully. 

