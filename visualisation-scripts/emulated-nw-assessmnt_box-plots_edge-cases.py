import pandas as pd
import matplotlib.pyplot as plt
import argparse
from brokenaxes import brokenaxes
import numpy as np
from matplotlib import rc
import matplotlib.ticker as ticker

def plot_boxplots(df, output_folder):
    # Define the (Delay, Packet Loss) pairs
    delay_packet_loss_pairs = [(0, 0), (100, 0), (0, 20), (100, 20)]
    
    # Set Helvetica Font globally
    rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})

    # Get the unique list of Signature Algorithms in the order they appear in the DataFrame
    sorted_algorithms = list(algorithm_names.keys())[::-1]  # Reverse the order

    # Create a single figure and subplot grid for all four plots
    fig, axs = plt.subplots(4, 1, figsize=(12, 18))
    
    for i, (delay, loss) in enumerate(delay_packet_loss_pairs):

        # Filter data for current (Delay, Packet Loss) pair
        filtered_data = df[(df['Delay'] == delay) & (df['Packet Loss'] == loss)]

        # Extract Handshake Duration data for each Signature Algorithm
        data_to_plot = [filtered_data[filtered_data['Signature Algorithm'] == algo]['Handshake Duration [ms]'].values
                        for algo in sorted_algorithms]
        
        # Box plot without outliers
        bp = axs[i].boxplot(data_to_plot, patch_artist=True, vert=False, showfliers=False, widths=0.4)
        
        # Get and show median values             
        j = len(sorted_algorithms) - 1.4
        for median in [median.get_xdata()[0] for median in bp["medians"]]:
            axs[i].text(median, len(sorted_algorithms) - j, f"{median:.2f}", ha='center', va='center')
            j = j - 1
        
        # Add a title displaying delay and packet loss information
        axs[i].text(0.99, 0.03, f'Delay: {delay}ms\nPacket Loss: {loss}%', fontsize=12, horizontalalignment='right', verticalalignment='bottom', transform=axs[i].transAxes, bbox=dict(facecolor='white', alpha=1.0))

        # Add Algorithm labels to y-axis
        axs[i].set_yticklabels([algorithm_names[algo] for algo in sorted_algorithms], fontsize=12)            
        
        
        # X-Axis formatting for the first plot
        if i == 0:
            axs[i].set_xlim(-50,1350)
            axs[i].set_xticks(np.arange(0, 1400, step=100))
            axs[i].set_xticklabels(np.arange(0, 1400, step=100), rotation=0)
            axs[i].set_xlabel('Handshake\nDuration [ms]', x=-0.01, horizontalalignment='right', verticalalignment='bottom')
            
            for label in axs[i].xaxis.get_ticklabels()[1::2]:
                label.set_visible(False)
        
        # X-Axis formatting for the second plot
        if i == 2:
            axs[i].set_xlim(-1250,33750)
            axs[i].set_xticks(np.arange(0, 35000, step=2500))
            axs[i].set_xticklabels(np.arange(0, 35000, step=2500), rotation=0)
            axs[i].set_xlabel('Handshake\nDuration [ms]', x=-0.01, horizontalalignment='right', verticalalignment='bottom')
            
            for label in axs[i].xaxis.get_ticklabels()[1::2]:
                label.set_visible(False)
        
        # X-Axis formatting for the third plot
        if i == 1:
            axs[i].set_xlim(-50,1350)
            axs[i].set_xticks(np.arange(0, 1400, step=100))
            axs[i].set_xticklabels(np.arange(0, 1400, step=100), rotation=0)
            axs[i].xaxis.set_ticks_position("top")
            
            for label in axs[i].xaxis.get_ticklabels()[::2]:
                label.set_visible(False)
        
        # X-Axis formatting for the fourth plot
        if i == 3:
            axs[i].set_xlim(-1250,33750)
            axs[i].set_xticks(np.arange(0, 35000, step=2500))
            axs[i].set_xticklabels(np.arange(0, 35000, step=2500), rotation=0)
            axs[i].xaxis.set_ticks_position("top")
            
            for label in axs[i].xaxis.get_ticklabels()[::2]:
                label.set_visible(False)
        
        # Add whitespace to the y-axis
        axs[i].set_ylim(axs[i].get_ylim()[0] - 0.05*(axs[i].get_ylim()[1]-axs[i].get_ylim()[0]), 
        axs[i].get_ylim()[1] + 0.05*(axs[i].get_ylim()[1]-axs[i].get_ylim()[0]))
        
                       
        # Zoom-In Section for first subplot
        if i == 0:
            # Create zoomed-in subplot within the main subplot
            zoom_algs = ['falcon1024', 'falcon512','dilithium5','dilithium3','dilithium2','RSA:3072','ECDSAprime256v1']
            
            zoom_pos = [0.607, 0.4658, 0.3565, 0.489]
            zoom_pos_2 = [0.3215, 0.326, 0.215, 0.139]
            
            # Add placeholder for zoom area
            placeholder_ax = axs[i].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(-4,9)
            axs[i].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)
            
            # Add placeholder for second zoom area
            placeholder_ax_2 = axs[i].inset_axes(zoom_pos_2)
            placeholder_ax_2.set_xticklabels([])
            placeholder_ax_2.set_xticks([])
            placeholder_ax_2.set_yticklabels([])
            placeholder_ax_2.set_yticks([])
            placeholder_ax_2.set_ylim(4.8,6.2)
            placeholder_ax_2.set_xlim(10,35)
            axs[i].indicate_inset_zoom(placeholder_ax_2, edgecolor='black', facecolor='palegreen', zorder=0, alpha=0.3)

            # First zoom area
            zoom_ax = axs[i].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot([filtered_data[filtered_data['Signature Algorithm'] == algo]['Handshake Duration [ms]'].values
                for algo in zoom_algs], patch_artist=True, vert=False, showfliers=False)
            zoom_ax.set_xlim(2, 7)
            zoom_ax.set_xticks(np.arange(2, 8, step=1))
            zoom_ax.yaxis.set_ticks_position('none')
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.grid()
            
            # Second zoom area
            zoom_algs = ['sphincssha2192fsimple', 'sphincssha2128fsimple']
            zoom_ax_2 = axs[i].inset_axes(zoom_pos_2, facecolor='palegreen')
            zoom_ax_2.boxplot([filtered_data[filtered_data['Signature Algorithm'] == algo]['Handshake Duration [ms]'].values
                for algo in zoom_algs], patch_artist=True, vert=False, showfliers=False, widths=(0.5))
            zoom_ax_2.set_xlim(17, 30)
            zoom_ax_2.set_xticks(np.arange(15, 35, step=5))
            zoom_ax_2.yaxis.set_ticks_position('none')
            plt.setp(zoom_ax_2.get_xticklabels(), backgroundcolor="white")
            zoom_ax_2.set_yticklabels([])
            zoom_ax_2.grid()
            
                    
        # Zoom-In Section for second subplot
        if i == 1:            
            
            # Create zoomed-in subplot within the main subplot
                       
            zoom_pos_1 = [0.036, 0.4658, 0.214, 0.489]
            zoom_pos_2 = [0.679, 0.605, 0.142, 0.139]
            
            # Add placeholder for first zoom area
            placeholder_ax_1 = axs[i].inset_axes(zoom_pos_1)
            placeholder_ax_1.set_xticklabels([])
            placeholder_ax_1.set_xticks([])
            placeholder_ax_1.set_yticklabels([])
            placeholder_ax_1.set_yticks([])
            placeholder_ax_1.set_ylim(6.8,13.2)
            placeholder_ax_1.set_xlim(405,420)
            axs[i].indicate_inset_zoom(placeholder_ax_1, edgecolor='black', facecolor='lightcyan', zorder=0, alpha=0.5)
            
            # Add placeholder for second zoom area
            placeholder_ax_2 = axs[i].inset_axes(zoom_pos_2)
            placeholder_ax_2.set_xticklabels([])
            placeholder_ax_2.set_xticks([])
            placeholder_ax_2.set_yticklabels([])
            placeholder_ax_2.set_yticks([])
            placeholder_ax_2.set_ylim(8.8,10.2)
            placeholder_ax_2.set_xlim(600,615)
            axs[i].indicate_inset_zoom(placeholder_ax_2, edgecolor='black', facecolor='thistle', zorder=0, alpha=0.3)
           
            # First zoom area
            zoom_algs = ['falcon1024', 'falcon512','dilithium5','dilithium3','dilithium2','RSA:3072','ECDSAprime256v1']
            zoom_ax_1 = axs[i].inset_axes(zoom_pos_1, facecolor='lightcyan')
            zoom_ax_1.boxplot([filtered_data[filtered_data['Signature Algorithm'] == algo]['Handshake Duration [ms]'].values
                for algo in zoom_algs], patch_artist=True, vert=False, showfliers=False)
            zoom_ax_1.set_xlim(405, 420)
            zoom_ax_1.set_xticks(np.arange(405, 425, step=5))

            zoom_ax_1.yaxis.set_ticks_position('none')
            plt.setp(zoom_ax_1.get_xticklabels(), backgroundcolor="white")
            zoom_ax_1.set_yticklabels([])
            zoom_ax_1.grid()
            
            # Second zoom area
            zoom_algs = ['dilithium5', 'dilithium3']
            zoom_ax_2 = axs[i].inset_axes(zoom_pos_2, facecolor='thistle')
            zoom_ax_2.boxplot([filtered_data[filtered_data['Signature Algorithm'] == algo]['Handshake Duration [ms]'].values
                for algo in zoom_algs], patch_artist=True, vert=False, showfliers=False, widths=(0.5))
            zoom_ax_2.set_xlim(605, 615)
            zoom_ax_2.set_xticks(np.arange(605, 620, step=5))
            zoom_ax_2.yaxis.set_ticks_position('none')
            plt.setp(zoom_ax_2.get_xticklabels(), backgroundcolor="white")
            zoom_ax_2.set_yticklabels([])
            zoom_ax_2.grid()
            
        if i > 1:
            # Create a light coloured box in the higher-scale plots to incidate the range of the lower-scale plots
            
            zoom_pos_1 = [0.036, 0.0, 0.038, 1.0]
            placeholder_ax_1 = axs[i].inset_axes(zoom_pos_1, zorder=1, facecolor='lightgray', alpha=0.4)
            placeholder_ax_1.set_xticklabels([])
            placeholder_ax_1.set_xticks([])
            placeholder_ax_1.set_yticklabels([])
            placeholder_ax_1.set_yticks([])



        
        axs[i].grid()
        axs[i].set_axisbelow(True)
                
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.08, wspace=0.1)

    # Save the combined plot
    plt.savefig(f'{output_folder}/box_plots_zoom-in_adjusted.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description='Create box plots from CSV data.')
    parser.add_argument('input_file', type=str, help='Path to the input CSV file.')
    parser.add_argument('output_folder', type=str, help='Path to the output folder for storing plots.')
    args = parser.parse_args()

    # Read CSV file
    df = pd.read_csv(args.input_file)

    # Plot boxplots
    plot_boxplots(df, args.output_folder)

# Dictionary mapping Signature Algorithm names to corresponding values
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

if __name__ == "__main__":
    main()
