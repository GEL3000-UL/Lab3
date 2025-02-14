####################################################################################################

# User-modifiable variables
PORT = 'COM5'
BATCH_LENGTH = 200 # Number of elements per bulk transfer
PLOT_LENGTH = 10*BATCH_LENGTH # Number of values to display at once
DIR_PATH = r"./Recordings" # Where the csv files will be written

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
    
    def __init__(self, p_com_port : str, p_save_dir : str) -> None:
        """
        Constructeur de la classe ArduinoPlotter.
        p_com_port : str : Le port COM sur lequel l'Arduino est connecté.
        p_save_dir : str : Le chemin où les données seront sauvegardées.
        """

        self.com_port = p_com_port
        self.f = open(
            self.getFileName( p_save_dir ),
            'w',
            newline=''
        )

        # objet writer pour ecrire dans le fichier CSV
        self.writer = csv.writer(self.f)
        self.writeEntryToSave(["Time","Value"])

        # objet serial pour lire le port en serie
        self.serial_object = None

        # liste de sauvegarde des datas
        # permet de contenir les PLOT_LENGTH dernieres data recues
        self.time = deque(np.arange(0, PLOT_LENGTH, 1), maxlen=PLOT_LENGTH)
        self.data = deque(np.zeros(PLOT_LENGTH), maxlen=PLOT_LENGTH)

        return
    
    def animate(self, i):
        """
        Fonction d'animation pour le plot avec matplotlib.pyplot
        i : int : L'index de l'animation.
        """

        self.line.set_data(self.time, self.data)            # update data dans le plot
        self.ax.set_xlim((min(self.time),max(self.time)))   # update limites de l'axe x
        return self.line
    
    def connect(self, p_baudrate:int=115200) -> bool:
        """
        Ouvre la connexion avec le port en série
        p_baudrate : int : Le baudrate de la connexion
        Retourne True si la connexion est établie, False sinon
        """

        self.serial_object = serial.Serial(
            port=self.com_port,
            baudrate=p_baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout = 5
        )               
        
        return self.serial_object != None

    def disconnect(self):
        """
        Déconnecte le port en série
        """

        if self.serial_object is None:
            return
        
        self.serial_object.close()
        print("Serial port has been closed")
        return

    def getFileName(self, p_dir : str) -> str:
        """
        Trouve le nom du fichier où les données seront sauvegardées
        p_dir : str : Le chemin où les données seront sauvegardées
        Retourne le nom du fichier, ou None si le chemin n'est pas valide
        """
        
        try:
            os.chdir(p_dir)
        except Exception as e:
            return None
            #raise Exception("Le chemin pour sauvegarder le données n'est pas valide")

        # chercher index du dernier fichier enregistre
        i = 0
        r_file_name = f"Arduino_recording_{i}.csv"
        while os.path.exists( r_file_name ):
            i += 1
            r_file_name = f"Arduino_recording_{i}.csv"

        return r_file_name
    
    def writeEntryToSave(self, p_data:list):
        """
        Écrit une entrée dans le fichier CSV
        p_data : list : La liste des données a enregistrer
        Retourne True si l'écriture a réussi, False sinon
        """

        if self.writer is None:
            return False
        
        self.writer.writerow(p_data)
        return True

    def closeCSVWriter(self):
        """
        Ferme le fichier CSV
        """

        if self.writer is None:
            return
        
        self.f.close()
        print("CSV file has been closed")
        return
    
    def resetData(self):
        """
        Réinitialise les données du plot
        """

        self.time.clear()
        self.data.clear()

    def readSerialLine(self):
        """
        Lit une ligne du port en série dont la structure est la suivante:
            val1,val2,...,valN\n
        Retourne un iterateur (val1, val2, ...)
        """

        try:
            msg = self.serial_object.readline().decode().strip().split(',')
            for i in range(len(msg)):
                yield int(msg[i])
        except:
            return None
    
    def pltAnimation(self) -> bool:
        """
        Lit les valeurs retournées par le port en série et les affiche 
        dans un plot anime 
        Retourne True si l'animation a bien ete executee, False en cas d'erreur
        """

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

        return self.run(self.pltAnimationRefresh)
    
    def pltAnimationRefresh(self):
        """
        Rafraichit le plot
        """

        plt.draw()
        plt.pause(0.5)

    def run(self, p_refresh_cb) -> bool:
        """
        Boucle de lecture des données du port en série
        Retourne True si l'animation a bien ete executee, False en cas d'erreur
        """

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
                    p_refresh_cb()
                    continue 

                # lire buffer jusqu'au caracter '\n'
                # ne rien faire en cas d'erreur de la lecture
                handshake = self.readSerialLine()
                if handshake is None:
                    continue
                handshake = tuple(handshake)

                # attendre debut d'un buffer
                if handshake[0] != ArduinoPlotter.HANDSHAKE_START:
                    continue
                
                safety_net = BATCH_LENGTH+2 # impose une limite de lecture pour la boucle
                while safety_net > 0:

                    # lire buffer jusqu'au caracter '\n'
                    rcvd = self.readSerialLine()
                    if rcvd is None:
                        continue
                    time, data = rcvd
                    
                    # arreter de boucler si reception du handshake de fin
                    if time == ArduinoPlotter.HANDSHAKE_STOP:
                        break

                    # calculer le temps depuis le debut des mesures en compensant
                    # l'indice de temps max dans l'arduino
                    if time == 0:
                        time_since_start = self.time[-1]+1
                    
                    # ajout des donnees dans la liste de sauvegarde
                    self.time.append(time_since_start+time)
                    self.data.append(data)

                    # ecriture des donnees dans le fichier CSV
                    self.writeEntryToSave(rcvd)

                    safety_net -= 1

            # arret de la boucle si CTRL-C
            except KeyboardInterrupt:
                run_loop = False
        
        print("Loop has ended")
        return True
    
    def __del__(self):
        """
        Destructeur de la classe ArduinoPlotter
        """

        self.closeCSVWriter()
        self.disconnect()
        return

        
if __name__=="__main__":
    plot = ArduinoPlotter(PORT, DIR_PATH)
    plot.connect()
    plot.pltAnimation()