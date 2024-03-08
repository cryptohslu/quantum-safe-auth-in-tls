import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import sys

# Dictionary for algorithm name replacements
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

def create_plots(csv_file, output_dir):
    # Read CSV file
    data = pd.read_csv(csv_file)

    # Filter data where Success = 1
    data = data[data['Success'] == 1]

    # Replace technical signature algorithm names with human-readable names
    data['Signature Algorithm'] = data['Signature Algorithm'].map(algorithm_names)

    # Group data by Signature Algorithm and Delay
    grouped_data = data.groupby(['Signature Algorithm', 'Delay'])

    # Get unique delay values
    unique_delays = data['Delay'].unique()

    # Get unique signature algorithms
    signature_algorithms = data['Signature Algorithm'].unique()

    # Create a subplot for each signature algorithm
    num_algorithms = len(signature_algorithms)
    fig, axes = plt.subplots(num_algorithms, len(unique_delays), figsize=(8, 16), sharex=True, sharey=True)

    # Loop through each signature algorithm
    for i, alg in enumerate(signature_algorithms):
        # Get data for the current signature algorithm
        alg_data = data[data['Signature Algorithm'] == alg]

        # Add the signature algorithm as a side title for each row
        axes[i, 4].set_ylabel(alg, rotation=90, ha='center', va='baseline')
        axes[i, 4].yaxis.set_label_position("right")

        # Loop through each unique delay value
        for j, delay in enumerate(unique_delays):
            # Get data for the current delay
            delay_data = alg_data[alg_data['Delay'] == delay]

            # Group data by Packet Loss and calculate median and 95th percentile Handshake Duration for each Packet Loss
            median_data = delay_data.groupby('Packet Loss')['Handshake Duration [ms]'].median().reset_index()
            percentile95_data = delay_data.groupby('Packet Loss')['Handshake Duration [ms]'].quantile(0.95).reset_index()

            # Plot median Handshake Duration against Packet Loss
            #axes[i, j].plot(median_data['Packet Loss'], median_data['Handshake Duration [ms]'], color='blue', linestyle='-',
              #              marker='', label='Median')
            axes[i, j].plot(percentile95_data['Packet Loss'], percentile95_data['Handshake Duration [ms]'], color='red',
                            linestyle='--', label='95th Percentile')
                        
            # Add the delay at the top for each column
            axes[0, j].set_title(f'Delay: {delay}ms')
            
            axes[i, j].set_xticks(np.arange(0, 1.5, step=0.5))


    fig.supxlabel('Packet Loss [%]')
    fig.supylabel('95th Percentile Handshake Duration [ms]')
    
    # Adjust layout and save the plot
    plt.tight_layout()
    plt.savefig(output_dir + '/handshake_durations.png')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <csv_file> <output_dir>")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_dir = sys.argv[2]

    create_plots(csv_file, output_dir)
