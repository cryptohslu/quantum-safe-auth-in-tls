import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rc
import numpy as np
import os

# Define dictionary for replacing Signature Algorithm names
algorithm_names = {
    "ECDSAprime256v1": "ECDSA-P256",
    "RSA:3072": "RSA-3072",
    "dilithium2": "Dilithium2",
    "dilithium3": "Dilithium3",
    "dilithium5": "Dilithium5",
    "falcon512": "Falcon-512",
    "falcon1024": "Falcon-1024",
    "sphincssha2128fsimple": "SPHINCS-128f",
    "sphincssha2192fsimple": "SPHINCS-192f",
    "sphincssha2256fsimple": "SPHINCS-256f",
    "sphincssha2128ssimple": "SPHINCS-128s",
    "sphincssha2192ssimple": "SPHINCS-192s",
    "sphincssha2256ssimple": "SPHINCS-256s"
}

# Set Helvetica Font globally
rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
                
def create_plots(csv_file, output_folder, signature_algorithms):
    df = pd.read_csv(csv_file)

    unique_delays = df['Delay'].unique()
    
    # Initialize variables to store global minimum and maximum values for x and y axes
    global_min_x = float('inf')
    global_max_x = float('-inf')
    global_min_y = float('inf')
    global_max_y = float('-inf')

    num_rows = (len(unique_delays) + 1) // 2
    fig, axs = plt.subplots(num_rows, 2, figsize=(12, 5.5 * num_rows), sharex='all', sharey='all')
    axs = axs.flatten()
    
    # Iterate over all data to determine global minimum and maximum values
    for delay in unique_delays:
        for signature_algorithm in signature_algorithms:
            filtered_df = df[(df['Delay'] == delay) & (df['Signature Algorithm'] == signature_algorithm)]
            grouped = filtered_df.groupby('Packet Loss')

            median_handshake = grouped['Handshake Duration [ms]'].median()

            # Update global minimum and maximum values for x axis
            global_min_x = min(global_min_x, median_handshake.index.min())
            global_max_x = max(global_max_x, median_handshake.index.max())

            # Update global minimum and maximum values for y axis
            global_min_y = min(global_min_y, median_handshake.min())
            global_max_y = max(global_max_y, median_handshake.max()) + 500

    for i, delay in enumerate(unique_delays):               
        for signature_algorithm in signature_algorithms:
            filtered_df = df[(df['Delay'] == delay) & (df['Signature Algorithm'] == signature_algorithm)]
            grouped = filtered_df.groupby('Packet Loss')

            colors = plt.cm.viridis(signature_algorithms.index(signature_algorithm) / len(signature_algorithms))

            median_color = colors

            median_handshake = grouped['Handshake Duration [ms]'].median()

            axs[i].plot(median_handshake.index, median_handshake.values, label=f'{algorithm_names.get(signature_algorithm, signature_algorithm)}', color=median_color)
            
            # Add text box to the plot
            axs[i].text(0.5, 0.96, f'Delay = {delay}ms', fontsize=12, horizontalalignment='center', verticalalignment='top', transform=axs[i].transAxes, bbox=dict(facecolor='white', alpha=0.5))
                        
            # Set same scales for x and y axes using global minimum and maximum values
            axs[i].set_xlim(global_min_x, global_max_x)
            axs[i].set_ylim(global_min_y, global_max_y)
            
            axs[i].set_xticks(np.arange(global_min_x, global_max_x + 1, step=1))
            axs[i].set_xticklabels(np.arange(global_min_x, global_max_x + 1, step=1), rotation=0)
            
            axs[i].set_yticks(np.arange(0, int(np.round(global_max_y, -3)) + 1000, step=1000))
            axs[i].set_yticklabels(np.arange(0, int(np.round(global_max_y, -3)) + 1000, step=1000), rotation=0)
            
            
            
            handles, labels = axs[i].get_legend_handles_labels()
            

    for i, delay in enumerate(unique_delays):        
        
        zoom_ax = axs[i].inset_axes([0.2,0.535,0.4,0.215], facecolor='Wheat')
        
        for signature_algorithm in signature_algorithms:
            filtered_df = df[(df['Delay'] == delay) & (df['Signature Algorithm'] == signature_algorithm)]
            grouped = filtered_df.groupby('Packet Loss')

            colors = plt.cm.viridis(signature_algorithms.index(signature_algorithm) / len(signature_algorithms))

            median_color = colors

            median_handshake = grouped['Handshake Duration [ms]'].median()
            
            zoom_ax.plot(median_handshake.index, median_handshake.values, label=f'{algorithm_names.get(signature_algorithm, signature_algorithm)}', color=median_color)
            
            zoom_ax.set_ylim(0, 2000)
        
        if delay == 0.0:
            zoom_ax.set_xlim(12, 17)
        if delay == 5.0:
            zoom_ax.set_xlim(9, 14)
        if delay == 25.0:
            zoom_ax.set_xlim(3, 8)
        if delay == 50.0:
            zoom_ax.set_xlim(0, 5)
        
        axs[i].indicate_inset_zoom(zoom_ax, edgecolor='black', facecolor='Wheat')
        zoom_ax.grid()
                        
    fig.legend(handles, labels, loc=(0.46,0.95), fontsize=12) 
    fig.supxlabel('Packet Loss [%]')
    fig.supylabel('Median Handshake Duration [ms]')
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)
    plt.savefig(os.path.join(output_folder, f'combined_plots.png'))
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create line plots from CSV file.')
    parser.add_argument('csv_file', type=str, help='Path to the CSV file')
    parser.add_argument('output_folder', type=str, help='Path to the output folder')
    parser.add_argument('--signature_algorithms', nargs='+', type=str, default=['RSA:3072', 'ECDSAprime256v1'], help='List of Signature Algorithms')

    args = parser.parse_args()

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    create_plots(args.csv_file, args.output_folder, args.signature_algorithms)
