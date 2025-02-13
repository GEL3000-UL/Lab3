####################################################################################################

# User-modifiable variables
PORT = 'COM4'
BATCH_LENGTH = 200 # Number of elements per bulk transfer
PLOT_LENGTH = 10*BATCH_LENGTH # Number of values to display at once
FULL_DIR_PATH = r"." # Where the csv files will be written

#####################################################################################################

from collections import deque
import serial 
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import csv
import os

class ArduinoPlotter:
    HANDSHAKE_START = 0x7fff
    HANDSHAKE_STOP = 0x7ffe
    
    def __init__(self, p_com_port, p_save_dir):
        self.com_port = p_com_port
        self.f = open(
            self.getFileName( p_save_dir ),
            'w',
            newline=''
        )
        self.writer = csv.writer(self.f)
        self.writeEntryToSave("Time","Value")

        self.serial_object = None

        self.time = deque(np.arange(0, PLOT_LENGTH, 1), maxlen=PLOT_LENGTH)
        self.data = deque(np.zeros(PLOT_LENGTH), maxlen=PLOT_LENGTH)

        self.fig, self.ax = plt.subplots()
        self.line = self.ax.plot(self.time, self.data)[0]
        plt.show(block=False)

        plt.xlabel("Time (ms)")
        plt.ylabel("Digital value")
        plt.title("Arduino Data")
        plt.legend(["Raw signal"])
        plt.ylim([0, 1024])

        self.ani = animation.FuncAnimation(
            self.fig,
            self.animate, 
            save_count=PLOT_LENGTH, 
            interval=200, 
            blit=False
        )

        return
    
    # Function to update the plot data and limits. 
    def animate(self, i):
        self.line.set_data(self.time, self.data)
        self.ax.set_xlim((min(self.time),max(self.time)))
        return self.line
    
    def connect(self):
        self.serial_object = serial.Serial(
            port=self.com_port,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout = 5
        )               
        print("Opening the Serial connection with the Arduino.")

    def disconnect(self):
        if self.serial_object is None:
            return True
        
        self.serial_object.close()
        return True

    def getFileName(self, p_dir):
        try:
            os.chdir(p_dir)
        except Exception as e:
            raise Exception("Le chemin pour sauvegarder le données n'est pas valide")

        i = 0
        file_name = f"Arduino_recording_{i}.csv"
        while os.path.exists( file_name ):
            i += 1
            file_name = f"Arduino_recording_{i}.csv"

        return file_name
    
    def writeEntryToSave(self, p_time, p_value):
        self.writer.writerow([p_time, p_value])
        return True

    def closeCSVWriter(self):
        if self.writer is None:
            return True
        
        self.f.close()
        return True
    
    def resetData(self):
        self.time.clear()
        self.data.clear()

    def readSerialLine(self):
        msg = self.serial_object.readline().decode().strip().split(',')
        return int(msg[0]), int(msg[1])

    def run(self):
        if self.serial_object is None:
            print("Serial port is not open")
            return False
        
        run_loop = True

        print("Press CTRL-C to exit.")

        time_since_start = 0
        while run_loop:
            try:
                
                # Mettre a jour plot si moins de 10 message dans le buffer
                if self.serial_object.inWaiting() < 10:
                    plt.draw()
                    plt.pause(0.5)
                    continue 

                # lire buffer jusqu'au caracter '\n'
                # ne rien faire en cas d'erreur de la lecture
                try:
                    handsake1, handshake2 = self.readSerialLine()
                except:
                    continue

                # attendre debut d'un buffer
                if handsake1 != ArduinoPlotter.HANDSHAKE_START:
                    continue
                
                safety_net = BATCH_LENGTH+2
                while safety_net > 0:
                    time, data = self.readSerialLine()
                    
                    # arreter de boucler si reception du handshake de fin
                    if time == ArduinoPlotter.HANDSHAKE_STOP:
                        break

                    if time == 0:
                        time_since_start = self.time[-1]
                    
                    self.time.append(time_since_start+time)
                    self.data.append(data)

                    self.writeEntryToSave(time, data)

            except KeyboardInterrupt:
                run_loop = False
                self.closeCSVWriter()
                self.disconnect()
        print("Loop has ended safely")
        return True

        
if __name__=="__main__":
    plot = ArduinoPlotter("COM4", "./Recordings")
    plot.connect()
    plot.run()