##############################################################################################
##      Title:           Post-Quantum TLS Handshake Benchmarker                             ##
##                                                                                          ##
##      Author:          Joshua Drexel, HSLU, Switzerland                                   ##
##                                                                                          ##
##      Description:     Benchmarking Post-Quantum TLS Handshake performance using          ##
##                       different signature algorithms with s_timer.                       ##
##                                                                                          ##
##############################################################################################

import argparse
import os
import sys
import subprocess
import shutil
import time
from datetime import datetime

# Path to s_timer
STIMER_BINARY = "/opt/stimer/s_timer"

# Dict with Signature Algorithm and Port Mapping
algs = {}
algs['RSA:3072'] = 50001
algs['ECDSAprime256v1'] = 50002
algs['dilithium2'] = 50003
algs['dilithium3'] = 50004
algs['dilithium5'] = 50005
algs['falcon512'] = 50006
algs['falcon1024'] = 50007
algs['sphincssha2128fsimple'] = 50008
algs['sphincssha2192fsimple'] = 50009
algs['sphincssha2256fsimple'] = 50010
algs['sphincssha2128ssimple'] = 50011
algs['sphincssha2192ssimple'] = 50012
algs['sphincssha2256ssimple'] = 50013


def run_benchmark_test(alg, algname, rounds, dest_ip, port):
    # Prepare file paths
    pki_path="./pki/pki-{}".format(algname)
    ca_cert = pki_path+"/ca/ca.crt"
    ica_cert = pki_path+"/ica/ica.crt"
    client_cert = pki_path+"/client/client.crt"
    client_key = pki_path+"/client/client.key"
    
    print(pki_path)
    
    # Start s_timer process
    # Note: Use run (not Popen), as it should be waited until the process execution in finished
    #       The test is repeated "rounds" times
    
    results = subprocess.run([STIMER_BINARY, '-h', '{}:{}'.format(dest_ip, port), '-r', str(rounds), '--cert='+client_cert, '--key='+client_key, '--rootcert='+ca_cert, '--chaincert='+ica_cert], capture_output=True)
    
    
    # Save output line by line in array
    s_time_output = bytes.decode(results.stdout, 'utf-8').splitlines()
        
    # Check that OpenSSL 3.2.0 was used (no older version)
    # Note: s_timer outputs the OpenSSL version in the first output line
    
    if s_time_output[0].find('OpenSSL 3.2.0 ') < 0:
        # Correct version string not found, abort
        print('\033[1;31mERROR:\t\tWrong OpenSSL version in s_timer. Aborting.\033[0m', file=sys.stderr)
        sys.exit(-1)
    else:
        # Check if provider could be loaded successfully
        # Note: s_timer output if provider load was successful on the second line
        if s_time_output[1].find('provider loaded successfully') < 0:
            # Provider not found
            print('\033[1;31mERROR:\t\tOQS-Provider in s_timer not loaded. Aborting.\033[0m', file=sys.stderr)
            sys.exit(-1)
        else:
            # Provider loaded successfully, print results
            i = 1
            for result in s_time_output[2].split(","):
                # s_timer outputs results as pairs of measurement:success (float:bool)
                # Note: If connection was unsuccessful (success=false), a dummy value of 0.0ms is returned as measurement
                measurement, success = result.split(":")
                results_file = open(results_file_name, "a")
                results_file.write(alg+","+str(i)+","+success+","+measurement+"\n")
                results_file.close()
                i = i + 1
            
            print('\033[1;32mSUCCESS:\tResults for {} written to file.\n\033[0m'.format(alg), file=sys.stdout)
                
    return

def run_ping(dest_ip):
    # Prepare file for output
    ping_file_name = out_dir+"ping_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".txt"
    
    print('\033[1;34mINFO:\t\tMeasuring RTT and Packet Loss to "{}".\n\033[0m'.format(dest_ip), file=sys.stdout)
    ping_results = subprocess.run(['ping', '-c', '10', str(dest_ip)], capture_output=True)
    
    # Save output
    ping_output = bytes.decode(ping_results.stdout, 'utf-8')
    
    # Write output to file
    ping_file = open(ping_file_name, "a")
    ping_file.write(ping_output)
    ping_file.close()
    
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Post-Quantum TLS Handshake Benchmarker',
        description='Benchmarking Post-Quantum TLS Handshake performance using different signature algorithms with OpenSSL s_time.')
    parser.add_argument('-rounds', help='the number of times the test should be performed for, default is 10', metavar='INT', type=int, default='10', required=False)
    parser.add_argument('-out', help='path to directory where the results should be saved to', metavar='<dir path>', required=True)
    parser.add_argument('-ip', help='IP address of TLS server', metavar='<IP>', default='localhost', required=False)
    
    args = parser.parse_args()
    
    rounds = args.rounds
    out_dir = args.out
    dest_ip = args.ip
    
    # Check if output directory exists
    if not os.path.isdir(out_dir):
        print('\033[1;31mERROR:\t\tDirectory "{}" does not exist. Please provide a directory to store the resulting files in.\033[0m'.format(out_dir), file=sys.stderr) 
        sys.exit(-1)
    
    # Run ping to measure RTT and Packet Loss
    run_ping(dest_ip)
    
    # Prepare file for benchmark results
    results_file_name = out_dir+"results_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".csv"
    results_file = open(results_file_name, "a")
    results_file.write("Signature Algorithm,Test Round,Success,Handshake Duration [ms]"+"\n")
    results_file.close()
    
    # Perform benchmark test for each signature algorithm
    for alg, port in algs.items():
               
        print('\033[1;34mINFO:\t\tStarting "{}" benchmark tests.\033[0m'.format(alg), file=sys.stdout)
        
        # For RSA, replace ":" with "" for the alg name used in the file paths
        if alg.startswith("RSA"):
            algname = alg.replace(":", "")
        else:
            algname = alg
        
        # Run s_timer benchmark test
        run_benchmark_test(alg, algname, rounds, dest_ip, port)
    
    print('\033[1;32mSUCCESS:\tResults were stored in "{}". Finished.\033[0m'.format(results_file_name), file=sys.stdout)
    sys.exit(0)
