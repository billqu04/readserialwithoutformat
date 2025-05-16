import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import time
import queue

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

        self.timestamps = deque(maxlen=20000)      # ~10 seconds at 2kHz
        self.data_points = deque(maxlen=20000)

        self.start_time = None
        self.log_queue = queue.Queue()             # Queue for thread-safe logging

        self.build_ui()
        self.setup_plot()

        # Start processing the log queue for safe UI updates
        self.root.after(100, self.process_log_queue)

    def build_ui(self):
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Serial Port:").grid(row=0, column=0, sticky='e')
        self.port_menu = ttk.Combobox(control_frame, textvariable=self.port_var, width=20)
        self.port_menu['values'] = [port.device for port in serial.tools.list_ports.comports()]
        self.port_menu.grid(row=0, column=1)

        ttk.Label(control_frame, text="Baud Rate:").grid(row=1, column=0, sticky='e')
        ttk.Entry(control_frame, textvariable=self.baud_var).grid(row=1, column=1)

        ttk.Button(control_frame, text="Select Output File", command=self.select_file).grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(control_frame, text="Start Logging", command=self.start_logging).grid(row=3, column=0, pady=10)
        ttk.Button(control_frame, text="Stop Logging", command=self.stop_logging).grid(row=3, column=1, pady=10)

        self.paned = tk.PanedWindow(self.root, orient='horizontal')
        self.paned.pack(fill='both', expand=True, padx=10, pady=5)

        self.output_text = tk.Text(self.paned, wrap='none')
        self.paned.add(self.output_text)

        self.plot_frame = ttk.Frame(self.paned)
        self.paned.add(self.plot_frame)

    def setup_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.line, = self.ax.plot([], [], 'r-')
        self.ax.set_title("Live Serial Data")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Data")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.update_plot()

    def update_plot(self):
        self.ax.clear()
        self.ax.set_title("Live Serial Data")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Data")
        self.ax.grid(True)

        if self.timestamps:
            self.ax.plot(self.timestamps, self.data_points, 'r-')
            max_time = max(self.timestamps)
            if self.running:
                left = max(0, max_time - 10)
                self.ax.set_xlim(left, left + 10)
            else:
                if max_time <= 10:
                    self.ax.set_xlim(0, 10)
                else:
                    self.ax.set_xlim(max_time - 10, max_time)
        else:
            self.ax.set_xlim(0, 10)

        self.canvas.draw()
        self.root.after(100, self.update_plot)

    def process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.output_text.insert(tk.END, msg + "\n")
            self.output_text.see(tk.END)
        self.root.after(100, self.process_log_queue)

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
        self.start_time = datetime.now()

    def stop_logging(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.log_queue.put("Stopped logging.")

    def read_serial(self):
        with open(self.output_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Data'])

            while self.running:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8').strip()
                        timestamp = datetime.now()

                        # Write to file
                        writer.writerow([timestamp.strftime('%H:%M:%S.%f')[:-3], line])
                        file.flush()

                        # Update GUI safely via queue
                        self.log_queue.put(f"{timestamp.strftime('%H:%M:%S.%f')[:-3]}: {line}")

                        # Store for plotting
                        try:
                            value = float(line)
                            elapsed = (timestamp - self.start_time).total_seconds()
                            self.timestamps.append(elapsed)
                            self.data_points.append(value)
                        except ValueError:
                            continue
                except Exception as e:
                    self.log_queue.put(f"Error: {e}")
                    self.running = False
                    break

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialLoggerApp(root)
    root.mainloop()
