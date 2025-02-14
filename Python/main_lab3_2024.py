# -*- coding: utf-8 -*-
"""
Python code for the laboratory 1 of GEL-3000

Displays in real-time the data sampled at 1kHz and 10 bits from an Arduino. 

The data structure used is a beginning and ending handshake of 0x7FFF and 
0x7FFE respectively. In between those handshakes, the data is transferred 
as 2 bytes for the time index, and 2 bytes for the data, repeated until the 
Arduino Buffer is depleted.

Filter the raw data using a 3 coefficients IIR notch filter. 

Written by Karim Bouzid, 2023
"""
####################################################################################################

# User-modifiable variables
PORT = 'COM4'
BATCH_LENGTH = 200 # Number of elements per bulk transfer
SAMP_FREQ = 1000 # Sampling frequency in Hz
PLOT_LENGTH = 20*BATCH_LENGTH # Number of values to display at once
FULL_DIR_PATH = r"." # Where the csv files will be written

#####################################################################################################
# Imports      
import serial
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import csv
import os

# Function to update the plot data and limits. 
def animate(i):
    line.set_data(time_serie, ecg_raw)
    line2.set_data(time_serie, ecg_notch)
    ax.set_xlim((min(time_serie),min(time_serie)+PLOT_LENGTH))
    return line,line2

fig, ax = plt.subplots()
plt.show(block=False)

# Create the coefficients for the notch filter
notch_freq = 60.0  # Frequency to be removed from signal (Hz)
quality_factor = 20.0
b_notch, a_notch = signal.iirnotch(notch_freq, quality_factor, SAMP_FREQ)
print("b_notch: ", b_notch)
print("a_notch: ", a_notch)

# Creating the deque objects to store the time, ecg values, and notch filter values. 
time_serie = deque(np.arange(0, BATCH_LENGTH, 1), maxlen=PLOT_LENGTH)
ecg_raw = deque(np.zeros(BATCH_LENGTH), maxlen=PLOT_LENGTH)
ecg_notch = deque(np.zeros(BATCH_LENGTH), maxlen=PLOT_LENGTH)
xs = deque(np.zeros(3), maxlen=3)
ys = deque(np.zeros(2), maxlen=2)

line,line2 = ax.plot(time_serie, ecg_raw, "r",  time_serie, ecg_notch, "b")

# Setting labels for the plot
plt.xlabel("Time (ms)")
plt.ylabel("Digital value")
plt.title("ECG measurement")
plt.legend(["Raw signal", "Notch filter"])
plt.ylim([0, 1024])

# Establish Serial object with COM port and BAUD rate to match Arduino Port/rate
serial_object = serial.Serial(
    port=PORT,
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 5
)               
print("Opening the Serial connection with the Arduino.")

ani = animation.FuncAnimation(
    fig, 
    animate, 
    save_count=PLOT_LENGTH, 
    interval=200, 
    blit=False
)

# Open a CSV file with incrementing name in write mode
i = 0
os.chdir(FULL_DIR_PATH)
while os.path.exists('Arduino_recording_%s.csv' % i):
    i += 1
f = open('Arduino_recording_%s.csv' % i, 'w', newline='')
writer = csv.writer(f)

# Global variables
breakCondition = False
idx = 0

print("Press CTRL-C to exit.")

# Main loop to sample the serial data and draw the plot. Stops with a CTRL-C. 
while not breakCondition:
    try:
        # Prevents reading the Serial too fast. Draws the sketch during downtimes.
        if (serial_object.inWaiting() < 10):
            plt.draw()
            plt.pause(0.5)
            continue

        # Reads the serial line. Continue if empty or errors happen.
        try:
            Received_message = int(serial_object.readline())
        except:
            continue

        #print(idx)
        # Read the full data buffer when the opening sequence 32767 is read, 
        # until the ending sequence 32766 is read.
        if Received_message == 32767:
            while True:
                Received_message = int(serial_object.readline())
                if Received_message == 32766:
                    break
                idx = Received_message
                Received_message = int(serial_object.readline())

                # Notch filter calculations
                xs.appendleft(Received_message)
                filtered_value = np.dot(b_notch, xs) - np.dot(a_notch[1:], ys)
                ys.appendleft(filtered_value)

                # Appends the time index and signals to the deque.
                time_serie.append(idx)
                ecg_raw.append(Received_message)
                ecg_notch.append(filtered_value)

                # write a row to the csv file
                writer.writerow([idx, Received_message, filtered_value])

                # Reset the real-time plot upon overflow.
                if idx <= 0:
                    time_serie.clear(); time_serie.append(idx); 
                    last_value = ecg_raw[0]; ecg_raw.clear(); ecg_raw.append(last_value); 
                    last_value = ecg_notch[0];  ecg_notch.clear(); ecg_notch.append(last_value); 

        else:
            continue
        
    except KeyboardInterrupt:
        breakCondition = True
        print("Closing the Serial connection with the Arduino.")
        
        serial_object.close()
        f.close()