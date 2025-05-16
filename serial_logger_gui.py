import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import csv
from datetime import datetime

class SerialLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial to CSV Logger")

        self.serial_thread = None
        self.running = False
        self.ser = None

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value='115200')
        self.output_file = "output.csv"

        self.build_ui()

    def build_ui(self):
        # Serial Port
        ttk.Label(self.root, text="Serial Port:").grid(row=0, column=0, sticky='e')
        self.port_menu = ttk.Combobox(self.root, textvariable=self.port_var, width=20)
        self.port_menu['values'] = [port.device for port in serial.tools.list_ports.comports()]
        self.port_menu.grid(row=0, column=1)

        # Baud Rate
        ttk.Label(self.root, text="Baud Rate:").grid(row=1, column=0, sticky='e')
        ttk.Entry(self.root, textvariable=self.baud_var).grid(row=1, column=1)

        # File selection
        ttk.Button(self.root, text="Select Output File", command=self.select_file).grid(row=2, column=0, columnspan=2, pady=5)

        # Start/Stop Buttons
        ttk.Button(self.root, text="Start Logging", command=self.start_logging).grid(row=3, column=0, pady=10)
        ttk.Button(self.root, text="Stop Logging", command=self.stop_logging).grid(row=3, column=1, pady=10)

        # Output Display
        self.output_text = tk.Text(self.root, height=10, width=50)
        self.output_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    def select_file(self):
        self.output_file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])

    def start_logging(self):
        if self.running:
            return
        try:
            self.ser = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return
        self.running = True
        self.serial_thread = threading.Thread(target=self.read_serial)
        self.serial_thread.daemon = True
        self.serial_thread.start()

    def stop_logging(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.output_text.insert(tk.END, "Stopped logging.\n")

    def read_serial(self):
      with open(self.output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'State', 'Raw', 'Current'])  # Updated header
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    timestamp = datetime.now().isoformat()

                    # Parse the line assuming format: "State: <state>, Raw: <raw>, Current: <current>"
                    try:
                        parts = dict(part.strip().split(': ') for part in line.split(', '))
                        state = parts.get('State', '')
                        raw = parts.get('Raw', '')
                        current = parts.get('Current', '')
                        writer.writerow([timestamp, state, raw, current])
                        self.output_text.insert(tk.END, f"{timestamp}: State={state}, Raw={raw}, Current={current}\n")
                    except Exception as parse_error:
                        self.output_text.insert(tk.END, f"{timestamp}: Unparsed line: {line}\n")

                    self.output_text.see(tk.END)

            except Exception as e:
                self.output_text.insert(tk.END, f"Error: {e}\n")
                self.running = False
                break


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialLoggerApp(root)
    root.mainloop()
