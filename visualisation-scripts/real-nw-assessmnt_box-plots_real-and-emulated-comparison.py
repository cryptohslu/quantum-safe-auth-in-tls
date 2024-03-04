import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rc
import numpy as np


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

def create_box_plots(csv_files, comparison_file, output_folder):
    # Set Helvetica Font globally
    rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
    
    # Create a figure with appropriate number of subplots
    fig, axes = plt.subplots(len(csv_files), 2, figsize=(12, 5.5 * len(csv_files)), sharex='all')
    plt.subplots_adjust(hspace=0.4)
    
    location_names = ['Windisch', 'Altdorf', 'Kemnitz']
    rtt_values = [5.246, 9.775, 29.731]

    # Read comparison data
    comparison_data = pd.read_csv(comparison_file)

    for i, (csv_file, ax_row) in enumerate(zip(csv_files, axes)):
        # Read the CSV file
        df = pd.read_csv(csv_file)

        # Group data by Signature Algorithm
        grouped_data = df.groupby('Signature Algorithm')

        # Prepare data for box plots
        data_to_plot = []
        labels = []
        for algorithm, data in grouped_data:
            # Replace algorithm name with shortened version
            algorithm = algorithm_names.get(algorithm, algorithm)
            data_to_plot.append(data['Handshake Duration [ms]'])
            labels.append(algorithm)

        # Sort data and labels based on algorithm_names dictionary values
        data_to_plot = [x for _, x in sorted(zip(labels, data_to_plot), key=lambda pair: list(algorithm_names.values()).index(pair[0]), reverse=True)]
        labels = sorted(labels, key=lambda x: list(algorithm_names.values()).index(x), reverse=True)

        # Plot box plots in the current subplot
        bp = ax_row[0].boxplot(data_to_plot, labels=labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
        ax_row[0].set_xlim(-50,950)
        ax_row[0].set_xticks(np.arange(0, 1000, step=100))
        
        # Get and show median values             
        j = len(labels) - 1.4
        for median in [median.get_xdata()[0] for median in bp["medians"]]:
            ax_row[0].text(median, len(labels) - j, f"{median:.2f}", ha='center', va='center')
            j = j - 1

        # Get comparison data for the current delay
        comparison_data_grouped = comparison_data.groupby('Signature Algorithm')
        comparison_data_to_plot = []
        comparison_labels = []
        for algorithm, comparison_data_group in comparison_data_grouped:
            # Replace algorithm name with shortened version
            algorithm = algorithm_names.get(algorithm, algorithm)
            comparison_data_filtered = comparison_data_group[comparison_data_group['Delay'] == delays[i]]
            if not comparison_data_filtered.empty:
                comparison_data_to_plot.append(comparison_data_filtered['Handshake Duration [ms]'].values)
                comparison_labels.append(algorithm)

        # Sort comparison data and labels based on algorithm_names dictionary values
        comparison_data_to_plot = [x for _, x in sorted(zip(comparison_labels, comparison_data_to_plot), key=lambda pair: list(algorithm_names.values()).index(pair[0]), reverse=True)]
        comparison_labels = sorted(comparison_labels, key=lambda x: list(algorithm_names.values()).index(x), reverse=True)

        # Plot box plots in the comparison subplot
        bp2 = ax_row[1].boxplot(comparison_data_to_plot, labels=comparison_labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
        ax_row[1].set_yticklabels([])
        
        # Get and show median values             
        j = len(comparison_labels) - 1.4
        for median in [median.get_xdata()[0] for median in bp2["medians"]]:
            ax_row[1].text(median, len(comparison_labels) - j, f"{median:.2f}", ha='center', va='center')
            j = j - 1
        
        # Add text box to the plot
        ax_row[0].text(0.02, 0.02, f'RTT: {rtt_values[i]} ms\nLocation: {location_names[i]}', fontsize=12, horizontalalignment='left', verticalalignment='bottom', transform=ax_row[0].transAxes, bbox=dict(facecolor='white', alpha=1.0))
        
        ax_row[1].text(0.02, 0.02, f'Delay: {delays[i]} ms\nPacket Loss: 0%', fontsize=12, horizontalalignment='left', verticalalignment='bottom', transform=ax_row[1].transAxes, bbox=dict(facecolor='white', alpha=1.0))
        
        ax_row[0].grid()
        ax_row[1].grid()
        
        # Add whitespace to the y-axis
        ax_row[0].set_ylim(ax_row[0].get_ylim()[0] - 0.05*(ax_row[0].get_ylim()[1]-ax_row[0].get_ylim()[0]), 
        ax_row[0].get_ylim()[1] + 0.05*(ax_row[0].get_ylim()[1]-ax_row[0].get_ylim()[0]))
        
        ax_row[1].set_ylim(ax_row[1].get_ylim()[0] - 0.05*(ax_row[1].get_ylim()[1]-ax_row[1].get_ylim()[0]), 
        ax_row[1].get_ylim()[1] + 0.05*(ax_row[1].get_ylim()[1]-ax_row[1].get_ylim()[0]))
        
        # Same position of zoom-area for all subplots
        zoom_pos = [0.45, 0.465, 0.5, 0.489]
        
        # Create zoomed-in subplots for first row
        if i == 0:           
            
            # Add placeholder for zoom area for real subplot
            placeholder_ax = ax_row[0].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(-10,40)
            ax_row[0].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[0].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(data_to_plot, labels=labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(10, 25)
            zoom_ax.set_xticks(np.arange(10, 28, step=3))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()

            
            # Add placeholder for zoom area for comparison subplot
            placeholder_ax = ax_row[1].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(-10,40)
            ax_row[1].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[1].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(comparison_data_to_plot, labels=comparison_labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(10, 22)
            zoom_ax.set_xticks(np.arange(10, 28, step=3))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()
        
        # Create zoomed-in subplots for second row
        if i == 1:           
            
            # Add placeholder for zoom area for real subplot
            placeholder_ax = ax_row[0].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(5,55)
            ax_row[0].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[0].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(data_to_plot, labels=labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(14, 45)
            zoom_ax.set_xticks(np.arange(14, 52, step=7))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()

            
            # Add placeholder for zoom area for comparison subplot
            placeholder_ax = ax_row[1].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(5,55)
            ax_row[1].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[1].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(comparison_data_to_plot, labels=comparison_labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(14, 45)
            zoom_ax.set_xticks(np.arange(14, 52, step=7))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()
        
        # Create zoomed-in subplots for third row
        if i == 2:           
            
            # Add placeholder for zoom area for real subplot
            placeholder_ax = ax_row[0].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(40,140)
            ax_row[0].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[0].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(data_to_plot, labels=labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(50, 130)
            zoom_ax.set_xticks(np.arange(50, 146, step=16))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()

            
            # Add placeholder for zoom area for comparison subplot
            placeholder_ax = ax_row[1].inset_axes(zoom_pos)
            placeholder_ax.set_xticklabels([])
            placeholder_ax.set_xticks([])
            placeholder_ax.set_yticklabels([])
            placeholder_ax.set_yticks([])
            placeholder_ax.set_ylim(6.8,13.2)
            placeholder_ax.set_xlim(40,140)
            ax_row[1].indicate_inset_zoom(placeholder_ax, edgecolor='black', facecolor='Wheat', zorder=0, alpha=0.3)

            
            zoom_ax = ax_row[1].inset_axes(zoom_pos, facecolor='Wheat')
            zoom_ax.boxplot(comparison_data_to_plot, labels=comparison_labels, patch_artist=True, vert=False, showfliers=False, widths=0.4)
            zoom_ax.set_xlim(50, 130)
            zoom_ax.set_xticks(np.arange(50, 146, step=16))
            zoom_ax.set_ylim(6.5,13.5)
            #zoom_ax.set_yticks([])
            plt.setp(zoom_ax.get_xticklabels(), backgroundcolor="white")
            zoom_ax.set_yticklabels([])
            zoom_ax.yaxis.set_ticks_position('none')
            zoom_ax.grid()

    # Set common x-label
    axes[-1][0].set_xlabel('Handshake Duration [ms]')
    axes[-1][1].set_xlabel('Handshake Duration [ms]')
    
    # Add titles for the columns of subplots
    axes[0][0].annotate('Real-World Network', (0.5, 1), xytext=(0, 25), textcoords='offset points',
                        xycoords='axes fraction', ha='center', va='baseline', fontsize=14)
    axes[0][1].annotate('Emulated Network', (0.5, 1), xytext=(0, 25), textcoords='offset points',
                        xycoords='axes fraction', ha='center', va='baseline', fontsize=14)

    fig.tight_layout()
    
    # Save the figure
    fig.savefig(output_folder + '/box_plots.png', dpi=300)
    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate box plots from CSV files.')
    parser.add_argument('csv_files', nargs=3, help='Three CSV files containing the data')
    parser.add_argument('comparison_file', help='CSV file containing comparison data')
    parser.add_argument('output_folder', help='Folder to save the generated figure')
    args = parser.parse_args()

    delays = [2.623, 4.888, 14.866]
    create_box_plots(args.csv_files, args.comparison_file, args.output_folder)
