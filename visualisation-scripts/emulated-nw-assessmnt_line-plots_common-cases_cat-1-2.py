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
    
    # Exclude the delay=0 plot, as not realistic
    df = df[df['Delay'] != 0.0]

    unique_delays = df['Delay'].unique()

    num_rows = len(unique_delays)
    fig, axs = plt.subplots(num_rows, 1, figsize=(10, 14), sharex='all', sharey=False)
    axs = axs.flatten()
    

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
            
            #axs[i].set_xlim(-1250,33750)
            axs[i].set_xticks(np.arange(0, 1.1, step=0.1))
            
            axs[0].set_ylim(13.6,14.8)
            axs[0].set_yticks(np.arange(13.6, 15, step=0.2))
            
            axs[1].set_ylim(44,45.4)
            axs[1].set_yticks(np.arange(44, 45.5, step=0.2))
            
            axs[2].set_ylim(109.2,110.6)
            axs[2].set_yticks(np.arange(109.2, 110.7, step=0.2))
            
            axs[3].set_ylim(309.2,310.4)           
            axs[3].set_yticks(np.arange(309.2, 310.6, step=0.2))
            
            
            handles, labels = axs[i].get_legend_handles_labels()
            
                        
    fig.legend(handles, labels, loc=(0.86,0.5), fontsize=10) 
    fig.supxlabel('Packet Loss [%]')
    fig.supylabel('Median Handshake Duration [ms]')
    
    plt.tight_layout()
    plt.subplots_adjust(right=0.85)
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
