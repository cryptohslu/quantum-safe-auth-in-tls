import argparse
import os
import sys
import subprocess
import shutil
import time
from datetime import datetime


# List of the traditional algorithms used for reference
# Comment out if an algorithm should not be included in the test
TRADITIONAL_SIG_ALGS = []
TRADITIONAL_SIG_ALGS.append("rsa3072")
TRADITIONAL_SIG_ALGS.append("ecdsap256")

def run_benchmark_test():
    
    # Write Header to file for each algorithm
    results_file = open(results_file_name, "a")
    results_file.write("Testrun for the Algorithm: "+alg+"\n")
    results_file.close()
    
    # Execute OpenSSL library benchmark speed test for given algorithm for 120 seconds (instead of default=10)
    results = subprocess.run(['openssl', 'speed', '-seconds', '120', alg], capture_output=True)
       
    # Save output line by line in array
    output = bytes.decode(results.stdout, 'utf-8').splitlines()
    
    # Prepare line-by-line write, if in future stripping of the results is to be implemented
    for result in output:
        results_file = open(results_file_name, "a")
        results_file.write(result+"\n")
        results_file.close()
    
    # Add blank line at the end of the algorithm section
    results_file = open(results_file_name, "a")
    results_file.write("------------------------------\n")
    results_file.close()
        
    print('\033[1;32mSUCCESS:\tResults for {} written to file.\n\033[0m'.format(alg), file=sys.stdout)
                
    return

def read_pq_sigalgs(sig_file):
    
    algs_from_file=[]
    algs_supported=[]
    
    # First get the list of supported signature algorithms of the OpenSSL installation
    process = subprocess.run(["openssl", "list", "-signature-algorithms"], capture_output=True)

    for line in process.stdout.splitlines():
        l = str(line.rstrip())[2:-1]
        if l.endswith(" @ oqsprovider"):
            algs_supported.append(l[2:-14]) 
    
    # Get the signature algorithms from the file and check if they are supported, otherwise exclude from list
    with open(sig_file, 'r', encoding='UTF-8') as file:
        while line := file.readline():
            algname = line.rstrip()
            if algname in algs_supported:
                # Algorithm is supported, add it to the list
                algs_from_file.append(line.rstrip())
            else:
                print('\033[1;33mWARNING:\tAlgorithm "{}" not supported, removed from list.\033[0m'.format(algname), file=sys.stderr)
        
        # Check if there are signature algorithms found in the file provided, otherwise exit with error
        if not algs_from_file:
            print('\033[1;31mERROR:\t\tNo supported algorithms found in "{}". Aborting.\033[0m'.format(sig_file), file=sys.stderr)
            file.close()
            sys.exit(-1)
    file.close()
    return algs_from_file

def create_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        overwriting = ask_for_overwrite(path)
        
        if overwriting == "yes":
            # Delete directory and all contained subdirs and files
            shutil.rmtree(path)
            
            # Re-create the directory
            os.mkdir(path)
            print('\033[1;34mINFO:\t\tFile/Directory "{}" overwritten.\033[0m'.format(path), file=sys.stdout)
        elif overwriting == "no":
            print('\033[1;34mINFO:\t\tFile/Directory "{}" is not overwritten.\033[0m'.format(path), file=sys.stdout)
        else:
            print('\033[1;31mERROR:\t\tFailure during file/directory operation. Aborting.\033[0m', file=sys.stderr)
            sys.exit(-1)
    return

def ask_for_overwrite(path):
    yes = {'yes','y', 'ye'}
    no = {'no','n', ''}
    
    choice = input('Directory or file "{}" already exists. Should it be overwritten (ALL subdirectories and files will be lost!)? [y/N] '.format(path)).lower()
    
    if choice in yes:
       return "yes"
    elif choice in no:
       return "no"
    else:
       print('\033[1;34mINFO:\t\tPlease respond with yes or no.\033[0m', file=sys.stdout)
       ask_for_overwrite(path)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Post-Quantum Signature Algorithm Benchmarker',
        description='Benchmarking Post-Quantum Signature Algorithm performance using OpenSSL speed.')
    parser.add_argument('-sigs', help='path to file with list of PQ signature algorithms to be included in the tests', metavar='<file path>', required=True)
    parser.add_argument('-out', help='path to directory where the results should be saved to', metavar='<dir path>', required=True)
    
    args = parser.parse_args()
    
    sig_file = args.sigs
    out_dir = args.out
    
    # Make sure that the PQ signature algorithm file exists
    if not os.path.isfile(sig_file):
        print('\033[1;31mERROR:\t\tFile "{}" does not exist. Please provide a file with the post-quantum signature algorithms to be included in the tests.\033[0m'.format(sig_file), file=sys.stderr)
        sys.exit(-1)
    
    # Check if output directory exists
    if not os.path.isdir(out_dir):
        print('\033[1;31mERROR:\t\tDirectory "{}" does not exist. Please provide a directory to store the resulting files in.\033[0m'.format(out_dir), file=sys.stderr) 
        sys.exit(-1)
    
    # Prepare file for benchmark results
    results_file_name = out_dir+"results_"+datetime.now().strftime("%Y-%m-%d_%H:%M:%S")+".csv"
    results_file = open(results_file_name, "a")
    results_file.close()

    # Read the post-quantum signature algorithms from file and check if activated in oqs-provider
    pq_sig_algs = read_pq_sigalgs(sig_file)
    
    # Add the reference algorithms (traditional crypto, provided in global variable) to the list
    sig_algs = TRADITIONAL_SIG_ALGS + pq_sig_algs
     
    # Perform benchmark test for each signature algorithm
    for alg in sig_algs:       
        print('\033[1;34mINFO:\t\tStarting "{}" benchmark tests.\033[0m'.format(alg), file=sys.stdout)
        # Run OpenSSL speed benchmark test
        run_benchmark_test()
    
    print('\033[1;32mSUCCESS:\tResults were stored in "{}". Finished.\033[0m'.format(results_file_name), file=sys.stdout)
    sys.exit(0)
