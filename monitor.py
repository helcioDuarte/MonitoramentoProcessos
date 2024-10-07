import subprocess
import time
import os
import signal
import re
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, Label, Button, OptionMenu, StringVar, Frame, Text, Scrollbar, END
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def gui(): 
    
    # interface principal
    root = Tk()
    root.title("Analisador de Processos por CPU")


    global dark_mode, annotation, is_dragging, x_press, y_press

    dark_mode = True
    bg_color_dark = '#2e2e2e'
    label_color_dark = '#ffffff'
    button_bg_dark = '#4a4a4a'
    button_fg_dark = '#ffffff'
    entry_bg_dark = '#3e3e3e'
    entry_fg_dark = '#ffffff'

    bg_color_light = '#ffffff'
    label_color_light = '#000000'
    button_bg_light = '#d9d9d9'
    button_fg_light = '#000000'
    entry_bg_light = '#ffffff'
    entry_fg_light = '#000000'
    
    
    
    # setando a variável da CPU
    cpu_var = StringVar(root)
    cpu_var.set('0')
    global data
    data = pd.DataFrame(columns=['Processo', 'CPU', 'Acordado', 'Execução', 'Término'])
    data['CPU'] = data['CPU'].astype(str)
    data = data._append({'Processo': '', 'CPU': 0, 'Acordado': 0, 'Execução': 0, 'Término': 0}, ignore_index=True)
    
 

    # dropdown da CPU
    label = Label(root, text="Selecione a CPU:", bg=bg_color_dark, fg=label_color_dark)
    label.grid(row=0, column=0, sticky='w')



    # botão para monitorar processos
    monitor_button = Button(root, text="Iniciar Monitoramento Novamente", command=lambda: [monitor_processes(), load_data(), plot_graph()], bg=button_bg_dark, fg=button_fg_dark)
    monitor_button.grid(row=1, column=0, sticky='w')

    # botão para plotar o gráfico
    plot_button = Button(root, text="Gerar Gráfico", command=lambda: plot_graph(cpu_var.get()), state="active", bg=button_bg_dark, fg=button_fg_dark)
    plot_button.grid(row=1, column=1, sticky='w')

    def toggle_mode():
        global dark_mode
        if dark_mode:
            root.configure(bg=bg_color_light)
            label.configure(bg=bg_color_light, fg=label_color_light)
            cpu_menu.configure(bg=entry_bg_light)
            monitor_button.configure(bg=button_bg_light, fg=button_fg_light)
            plot_button.configure(bg=button_bg_light, fg=button_fg_light)
            output_text.configure(bg=entry_bg_light, fg=label_color_light)
            for widget in output_frame.winfo_children():
                # Configure apenas se o widget suportar fg
                if 'fg' in widget.configure():
                    widget.configure(bg=entry_bg_light, fg=label_color_light)
                else:
                    widget.configure(bg=entry_bg_light)
            dark_mode = False
            toggle_button.config(text="Ativar Modo Noturno")
        else:
            root.configure(bg=bg_color_dark)
            label.configure(bg=bg_color_dark, fg=label_color_dark)
            cpu_menu.configure(bg=entry_bg_dark)
            monitor_button.configure(bg=button_bg_dark, fg=button_fg_dark)
            plot_button.configure(bg=button_bg_dark, fg=button_fg_dark)
            output_text.configure(bg=entry_bg_dark, fg=label_color_dark)
            for widget in output_frame.winfo_children():
                # Configure apenas se o widget suportar fg
                if 'fg' in widget.configure():
                    widget.configure(bg=entry_bg_dark, fg=label_color_dark)
                else:
                    widget.configure(bg=entry_bg_dark)
            dark_mode = True
            toggle_button.config(text="Desativar Modo Noturno")

    # Legenda
    glossary_label = Label(root, text=(
        "Legenda: Acordado (bolas azuis), Execução (Xs laranjas), "
        "Término (quadrados verdes)\nZoom: Scroll do mouse. "
        "Arrastar: Clique esquerdo e movimento do mouse"
    ), bg=bg_color_dark, fg=label_color_dark)
    glossary_label.grid(row=4, column=0, columnspan=3, sticky='n')

    # Configurações de layout
    root.grid_rowconfigure(2, weight=1)
    root.grid_columnconfigure(1, weight=1)
    # botão para alternar entre os modos claro e escuro
    toggle_button = Button(root, text="Desativar Modo Noturno", command=toggle_mode, bg=button_bg_dark, fg=button_fg_dark)
    toggle_button.grid(row=0, column=2, sticky='ne')  # Posicionando no canto superior direito

    # frame do gráfico
    frame = Frame(root, bg=bg_color_dark)
    frame.grid(row=2, column=0, columnspan=3, sticky='nsew')

    # frame do scroll e do texto
    output_frame = Frame(root, bg=bg_color_dark)
    output_frame.grid(row=3, column=0, columnspan=3, sticky='nsew')

    # scrollbar
    scrollbar = Scrollbar(output_frame)
    scrollbar.pack(side='right', fill='y')
    
    
    # saida de texto
    output_text = Text(output_frame, wrap='word', bg=entry_bg_dark, fg=label_color_dark, yscrollcommand=scrollbar.set)
    output_text.pack(fill='both', expand=True)
    scrollbar.config(command=output_text.yview)

    def log_message(message):
        output_text.insert(END, message + '\n')
        output_text.see(END)  # Rola para a parte inferior do Text widget


    def monitor_processes():
        try:
            log_message("Iniciando monitoramento...")
            process = subprocess.Popen(
                ["sudo", "trace-cmd", "record", "-e", "sched_switch", "-e", "sched_wakeup", "-o", "trace.dat"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # tempo do monitoramento
            time.sleep(3)

            os.kill(process.pid, signal.SIGINT)
            process.wait()

            if process.returncode == 0 and os.path.exists("trace.dat"):
                log_message("Monitoramento concluído e arquivo trace.dat gerado.")
                convert_trace_file("trace.dat", "trace.txt")
                return True  # Retorna True se o monitoramento foi bem-sucedido
            else:
                log_message("Monitoramento concluído, mas o arquivo trace.dat não foi gerado.")
                return False  # Retorna False se não foi bem-sucedido
        except Exception as e:
            log_message(f"Ocorreu um erro: {e}")
            return False  # Retorna False em caso de erro

    # converter trace.dat para trace.txt
    def convert_trace_file(input_file, output_file):
        log_message("Convertendo trace.dat para trace.txt...")
        with open(output_file, "w") as txt_file:
            convert_process = subprocess.Popen(
                ["sudo", "trace-cmd", "report", "-i", input_file],
                stdout=txt_file,
                stderr=subprocess.PIPE
            )
            convert_process.wait()

        if convert_process.returncode == 0 and os.path.exists(output_file):
            log_message("Conversão concluída: trace.txt gerado com sucesso.")
            parse_trace_file(output_file, 'process_times.txt')
        else:
            log_message("Erro durante a conversão: trace.txt não foi gerado.")

    # converter trace.txt para process_times.txt
    def parse_trace_file(input_file, output_file):
        process_data = {}
        wakeup_pattern = re.compile(r'\s+(\S+.*?)\s+\[(\d+)\]\s+(\d+\.\d+): sched_wakeup:\s+(\S+.*?)\s+\[\d+\]\s+CPU:(\S+)')
        switch_pattern = re.compile(r'\s+(\S+.*?)\s+\[(\d+)\]\s+(\d+\.\d+): sched_switch:\s+(\S+.*?)\s+\[\d+\]\s+(\S)\s+==>\s+(\S+.*?)\s+\[\d+\]')
        
        wakeup_count = 0
        switch_count = 0

        with open(input_file, 'r') as f:
            for line in f:
                wakeup_match = wakeup_pattern.match(line)
                switch_match = switch_pattern.match(line)

                if wakeup_match:
                    wakeup_count += 1
                    timestamp = float(wakeup_match.group(3))
                    target_process = wakeup_match.group(4)
                    cpu = wakeup_match.group(2)
                    key = target_process

                    if key not in process_data:
                        process_data[key] = []
                    process_data[key].append({'CPU': cpu, 'wakeup_time': timestamp, 'start_time': None, 'end_time': None})

                elif switch_match:
                    switch_count += 1
                    cpu = switch_match.group(2)
                    old_process_name = switch_match.group(4)
                    new_process_name = switch_match.group(6)
                    timestamp = float(switch_match.group(3))

                    key_new = new_process_name
                    if key_new in process_data:
                        for instance in process_data[key_new]:
                            if instance['start_time'] is None and instance['wakeup_time'] is not None:
                                instance['start_time'] = timestamp
                                break
                    
                    else:
                        process_data[key_new] = []
                        process_data[key_new].append({'CPU': cpu, 'wakeup_time': None, 'start_time': timestamp, 'end_time': None})

                    key_old = old_process_name
                    if key_old in process_data:
                        for instance in process_data[key_old]:
                            if instance['start_time'] is not None and instance['end_time'] is None:
                                instance['end_time'] = timestamp
                                break
                    
                    else:
                        process_data[key_old] = []
                        process_data[key_old].append({'CPU': cpu, 'wakeup_time': None, 'start_time': None, 'end_time': timestamp})

        log_message(f"[DEBUG] Total de eventos sched_wakeup: {wakeup_count}")
        log_message(f"[DEBUG] Total de eventos sched_switch: {switch_count}")

        with open(output_file, 'w') as out_f:
            out_f.write("Processo\tCPU\tAcordado\tExecução\tTérmino\n")
            for key, instances in process_data.items():
                for instance in instances:
                    out_f.write(f"{key}\t{instance['CPU']}\t{instance['wakeup_time']}\t{instance['start_time']}\t{instance['end_time']}\n")

    def plot_graph(cpu):    # Função para plotar o gráfico filtrando pela CPU selecionada
        global is_dragging, x_press, y_press, annotation
        cpu_data = data[data['CPU'].astype(str) == str(cpu)]

        if cpu_data.empty:
            log_message(f"Nenhum dado encontrado para CPU {cpu}")
            return

        min_time = min(cpu_data[['Acordado', 'Execução', 'Término']].min())
        fig, ax = plt.subplots(figsize=(12, 8))
        processos = cpu_data.groupby('Processo')
        points = []

        for nome_processo, grupo in processos:
            acordado_plot, = ax.plot(grupo['Acordado'] - min_time, [nome_processo]*len(grupo), 'o', label='Acordado', color='blue', markersize=5)
            execucao_plot, = ax.plot(grupo['Execução'] - min_time, [nome_processo]*len(grupo), 'x', label='Execução', color='orange', markersize=5)
            termino_plot, = ax.plot(grupo['Término'] - min_time, [nome_processo]*len(grupo), 's', label='Término', color='green', markersize=5)

            for idx, row in grupo.iterrows():
                acordado_x = row['Acordado'] - min_time
                execucao_x = row['Execução'] - min_time
                termino_x = row['Término'] - min_time
                tempo_fila = execucao_x - acordado_x
                tempo_execucao = termino_x - execucao_x
                points.extend([
                    (acordado_plot, acordado_x, nome_processo, 'Acordado', None),
                    (execucao_plot, execucao_x, nome_processo, 'Execução', tempo_fila),
                    (termino_plot, termino_x, nome_processo, 'Término', tempo_execucao)
                ])

        ax.set_xlabel('Tempo relativo ao início (s)')
        ax.set_ylabel('Processos')
        ax.set_title(f'Processos na CPU {cpu}: Acordado, Execução e Término')
        ax.grid(True)

        
        def zoom(event):
            base_scale = 1.2
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()

            xdata = event.xdata
            ydata = event.ydata

            if event.button == 'up':
                scale_factor = 1 / base_scale
            elif event.button == 'down':
                scale_factor = base_scale
            else:
                return

            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

            ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
            ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
            canvas_plot.draw()

        def on_press(event):
            global is_dragging, x_press, y_press
            is_dragging = True
            x_press = event.xdata
            y_press = event.ydata

        def on_motion(event):
            global is_dragging
            if is_dragging and event.inaxes is not None:
                dx = event.xdata - x_press
                dy = event.ydata - y_press
                
                # Ajustar os limites do eixo com base no movimento do mouse
                cur_xlim = ax.get_xlim()
                cur_ylim = ax.get_ylim()
                ax.set_xlim([cur_xlim[0] - dx, cur_xlim[1] - dx])
                ax.set_ylim([cur_ylim[0] - dy, cur_ylim[1] - dy])
                canvas_plot.draw()

        def on_release(event):
            global is_dragging
            is_dragging = False

        def on_hover(event):
            global annotation
            hover_distance_threshold = 0.05

            if event.inaxes is None:
                return

            closest_point = None
            min_distance = float('inf')
            for plot, x, proc, tipo, tempo_adicional in points:
                dx = abs(event.xdata - x)
                dy = abs(ax.get_ybound()[1] - ax.get_ybound()[0]) / len(processos)
                if dx < hover_distance_threshold and dy < hover_distance_threshold:
                    distance = (dx*2 + dy*2)*0.5
                    if distance < min_distance:
                        min_distance = distance
                        closest_point = (x, proc, tipo, tempo_adicional)

            if closest_point:
                x, proc, tipo, tempo_adicional = closest_point
                if annotation:
                    annotation.remove()
                if tipo == 'Término':
                    if pd.isna(tempo_adicional):
                        annotation_text = (f"Processo: {proc}\nInstante relativo: {x:.6f}s\n"
                                           f"Fase: {tipo}\nTempo de Execução: Sem dados suficientes")
                    else:
                        annotation_text = (f"Processo: {proc}\nInstante relativo: {x:.6f}s\n"
                                           f"Fase: {tipo}\nTempo de Execução: {tempo_adicional:.6f}s")
                elif tipo == 'Execução':
                    if pd.isna(tempo_adicional):
                        annotation_text = (f"Processo: {proc}\nInstante relativo: {x:.6f}s\n"
                                           f"Fase: {tipo}\nTempo na Fila: Sem dados suficientes")
                    else:
                        annotation_text = (f"Processo: {proc}\nInstante relativo: {x:.6f}s\n"
                                            f"Fase: {tipo}\nTempo na Fila: {tempo_adicional:.6f}s")
                else:
                      annotation_text = f"Processo: {proc}\nInstante relativo: {x:.6f}s\nFase: {tipo}"

                annotation = ax.annotate(annotation_text, xy=(x, proc), 
                                        xytext=(10, 10), textcoords='offset points',
                                        bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.5),
                                        arrowprops=dict(arrowstyle="->", color='black'))
                canvas_plot.draw()
            else:
                if annotation:
                    annotation.remove()
                    annotation = None
                    canvas_plot.draw()

        for widget in frame.winfo_children():
            widget.destroy()

        canvas_plot = FigureCanvasTkAgg(fig, master=frame)
        canvas_plot.draw()
        canvas_plot.get_tk_widget().pack()

        canvas_plot.mpl_connect('motion_notify_event', on_hover)
        canvas_plot.mpl_connect('scroll_event', zoom)
        canvas_plot.mpl_connect('button_press_event', on_press)
        canvas_plot.mpl_connect('motion_notify_event', on_motion)
        canvas_plot.mpl_connect('button_release_event', on_release)


    # verificar se process_times.txt existe

    def load_data():
        global data
        data = pd.read_csv('process_times.txt', sep='\t', header=0)
        data.columns = ['Processo', 'CPU', 'Acordado', 'Execução', 'Término']
        data['Acordado'] = pd.to_numeric(data['Acordado'])
        data['Execução'] = pd.to_numeric(data['Execução'])
        data['Término'] = pd.to_numeric(data['Término'])

    if os.path.exists('process_times.txt'):
        load_data()
    else:
        if monitor_processes():
            load_data()

    cpus_disponiveis = sorted(data['CPU'].astype(str).unique())
    cpu_menu = OptionMenu(root, cpu_var, *cpus_disponiveis)
    cpu_menu.configure(bg=entry_bg_dark)
    cpu_menu.grid(row=0, column=1, sticky='w')  
    
    is_dragging = False
    x_press = None
    y_press = None
    annotation = None
    monitoring_successful = False  # Flag para verificar se o monitoramento foi realizado


    
    root.mainloop()

if __name__ == "__main__":
    gui()