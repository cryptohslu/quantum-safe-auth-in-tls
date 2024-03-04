import argparse
import os
import sys
import subprocess
import shutil

# List of the traditional algorithms used for reference
# Comment out if an algorithm should not be included in the test
TRADITIONAL_SIG_ALGS = []
#TRADITIONAL_SIG_ALGS.append("ED448")
#TRADITIONAL_SIG_ALGS.append("ED25519")
#TRADITIONAL_SIG_ALGS.append("RSA:2048")
TRADITIONAL_SIG_ALGS.append("RSA:3072")
TRADITIONAL_SIG_ALGS.append("ECDSAprime256v1")
#TRADITIONAL_SIG_ALGS.append("ECDSAsecp384r1")

def pki_setup(alg, algstring, out_dir):
    
    # Prepare parent directory for algorithm specific PKI
    pki_path = os.path.join(out_dir, "pki-{}".format(algstring))
    create_dir(pki_path)
    ca_config = pki_path+"/oqs-openssl-ca.cnf"
    ica_config = pki_path+"/oqs-openssl-ica.cnf"             
    
    # Create sub-directory for CA, prepare file paths, create and init serial-number file
    ca_path = os.path.join(pki_path, "ca")
    create_dir(ca_path)
    ca_cert = ca_path+"/ca.crt"
    ca_key = ca_path+"/ca.key"
    serial_file = open(ca_path+"/serial", "a")
    serial_file.write("1000")
    serial_file.close()
    index_file = open(ca_path+"/index.txt", "a")
    index_file.close()
    # Copy CA config, but set real CA path
    with open('./oqs-openssl-ca.cnf', "rt") as template_config:
        with open(ca_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace('{path}', ca_path))
    
    # Create sub-directory for ICA, prepare file paths, create and init serial-number file
    ica_path = os.path.join(pki_path, "ica")
    create_dir(ica_path)
    ica_cert = ica_path+"/ica.crt"
    ica_csr = ica_path+"/ica.csr"
    ica_key = ica_path+"/ica.key"
    file = open(ica_path+"/serial", "a")
    file.write("1000")
    file.close()
    index_file = open(ica_path+"/index.txt", "a")
    index_file.close()
    # Copy ICA config, but set real ICA path
    with open('./oqs-openssl-ica.cnf', "rt") as template_config:
        with open(ica_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace('{path}', ica_path))
    
    ####################################################################
    # Create CA key and certificate
    # Note: if/else is needed, because ECDSA needs additional arguments than EdDSA, RSA and PQC
    if alg.startswith("ECDSA"):
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg[5:]+" - Test Root CA"
        ec_param = 'ec_paramgen_curve:'+alg[5:]
        ca_cert_process = subprocess.run(['openssl', 'req', '-x509', '-new', '-sha256', '-newkey', 'ec', '-pkeyopt', ec_param, '-keyout', ca_key, '-out', ca_cert, '-nodes', '-subj', subject, '-days', '7300', '-extensions', 'v3_ca', '-config', ca_config], capture_output = True, text = True)
    else:
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg+" - Test Root CA"
        ca_cert_process = subprocess.run(['openssl', 'req', '-x509', '-new', '-sha256', '-newkey', alg, '-keyout', ca_key, '-out', ca_cert, '-nodes', '-subj', subject, '-days', '7300', '-extensions', 'v3_ca', '-config', ca_config], capture_output=True, text = True)
    
    
    if ca_cert_process.returncode != 0:
        # Print the error messages from subprocess
        print(ca_cert_process.stderr)
        print('\033[1;31mERROR:\t\tError during CA setup. Aborting.\033[0m', file=sys.stderr)
        sys.exit(-1)
    
    
    ####################################################################
    # Create Intermediate-CA key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg[5:]+" - Test Intermediate CA"
        ica_key_process = subprocess.run(['openssl', 'ecparam', '-name', alg[5:], '-genkey', '-out', ica_key,], capture_output=True, text = True)
    else:
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg+" - Test Intermediate CA"
        ica_key_process = subprocess.run(['openssl', 'genpkey', '-algorithm', alg, '-out', ica_key, '-config', ica_config], capture_output=True, text = True)
    
    ica_csr_process = subprocess.run(['openssl', 'req', '-new', '-sha256', '-key', ica_key, '-out', ica_csr, '-subj', subject, '-config', ica_config], capture_output=True, text = True)        
    ica_cert_process = subprocess.run(['openssl', 'ca', '-extensions', 'v3_intermediate_ca', '-md', 'sha256', '-batch', '-in', ica_csr, '-out', ica_cert, '-days', '3650', '-config', ca_config], capture_output=True, text = True)
    
    
    if ica_key_process.returncode != 0 or ica_csr_process.returncode != 0 or ica_cert_process.returncode != 0:
        # Print the error messages from subprocess
        print(ica_key_process.stderr)
        print(ica_csr_process.stderr)
        print(ica_cert_process.stderr)
        print('\033[1;31mERROR:\t\tError during ICA setup. Aborting.\033[0m', file=sys.stderr)
        sys.exit(-1)
    
    # Create sub-directory for server certificate, prepare file paths
    server_path = os.path.join(pki_path, "server")
    create_dir(server_path)
    server_cert = server_path+"/server.crt"
    server_csr = server_path+"/server.csr"
    server_key = server_path+"/server.key"
        
    
    ####################################################################
    # Create Server key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg[5:]+" - Server Certificate"
        server_key_process = subprocess.run(['openssl', 'ecparam', '-name', alg[5:], '-genkey', '-out', server_key,], capture_output=True, text = True)
    else:
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg+" - Server Certificate"
        server_key_process = subprocess.run(['openssl', 'genpkey', '-algorithm', alg, '-out', server_key, '-config', ica_config], capture_output=True, text = True)
    
    server_csr_process = subprocess.run(['openssl', 'req', '-new', '-sha256', '-key', server_key, '-out', server_csr, '-subj', subject, '-config', ica_config], capture_output=True, text = True)        
    server_cert_process = subprocess.run(['openssl', 'ca', '-extensions', 'server_cert', '-md', 'sha256', '-batch', '-in', server_csr, '-out', server_cert, '-days', '365', '-config', ica_config], capture_output=True, text = True)
    
    
    if server_key_process.returncode != 0 or server_csr_process.returncode != 0 or server_cert_process.returncode != 0:
        # Print the error messages from subprocess
        print(server_key_process.stderr)
        print(server_csr_process.stderr)
        print(server_cert_process.stderr)
        print('\033[1;31mERROR:\t\tError during server certificate setup. Aborting.\033[0m', file=sys.stderr)
        sys.exit(-1)
    
    # Create sub-directory for client certificate, prepare file paths
    client_path = os.path.join(pki_path, "client")
    create_dir(client_path)
    client_cert = client_path+"/client.crt"
    client_csr = client_path+"/client.csr"
    client_key = client_path+"/client.key"
    
    
    ####################################################################
    # Create Client key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg[5:]+" - Client Certificate"
        client_key_process = subprocess.run(['openssl', 'ecparam', '-name', alg[5:], '-genkey', '-out', client_key,], capture_output=True, text = True)
    else:
        subject = "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="+alg+" - Client Certificate"
        client_key_process = subprocess.run(['openssl', 'genpkey', '-algorithm', alg, '-out', client_key, '-config', ica_config], capture_output=True, text = True)
    
    client_csr_process = subprocess.run(['openssl', 'req', '-new', '-sha256', '-key', client_key, '-out', client_csr, '-subj', subject, '-config', ica_config], capture_output=True, text = True)        
    client_cert_process = subprocess.run(['openssl', 'ca', '-extensions', 'server_cert', '-md', 'sha256', '-batch', '-in', client_csr, '-out', client_cert, '-days', '365', '-config', ica_config], capture_output=True, text = True)
    
    
    if client_key_process.returncode != 0 or client_csr_process.returncode != 0 or client_cert_process.returncode != 0:
        # Print the error messages from subprocess
        print(client_key_process.stderr)
        print(client_csr_process.stderr)
        print(client_cert_process.stderr)
        print('\033[1;31mERROR:\t\tError during server certificate setup. Aborting.\033[0m', file=sys.stderr)
        sys.exit(-1)
    
    
    # Overwrite CA and ICA config files again to prepare it for usage in Docker container
    with open('./oqs-openssl-ca.cnf', "rt") as template_config:
        with open(ca_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace('{path}', '/pqc-tls-tests/pki/pki-{}/ca'.format(algstring)))
    
    with open('./oqs-openssl-ica.cnf', "rt") as template_config:
        with open(ica_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace('{path}', '/pqc-tls-tests/pki/pki-{}/ica'.format(algstring)))
    
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
        prog='PQC PKI Set Up',
        description='Set-up Script for PKIs.')
    parser.add_argument('-sigs', help='path to file with list of PQ signature algorithms to be included in the set up', metavar='<file path>', required=True)
    parser.add_argument('-out', help='path to directory where the results should be saved to', metavar='<dir path>', required=True)
    
    args = parser.parse_args()
    
    sig_file = args.sigs
    out_dir = args.out
    
    # Make sure that the PQ signature algorithm file exists
    if not os.path.isfile(sig_file):
        print('\033[1;31mERROR:\t\tFile "{}" does not exist. Please provide a file with the post-quantum signature algorithms to be included in the set up.\033[0m'.format(sig_file), file=sys.stderr)
        sys.exit(-1)
    
    # Check if output directory exists
    if not os.path.isdir(out_dir):
        print('\033[1;31mERROR:\t\tDirectory "{}" does not exist. Please provide a directory to store the resulting files in.\033[0m'.format(out_dir), file=sys.stderr) 
        sys.exit(-1)
        
    # Read the post-quantum signature algorithms from file and check if activated in oqs-provider
    pq_sig_algs = read_pq_sigalgs(sig_file)
    
    # Add the reference algorithms (traditional crypto, provided in global variable) to the list
    sig_algs = TRADITIONAL_SIG_ALGS + pq_sig_algs
     
    # Set up PKI for each signature algorithm
    for alg in sig_algs:
        print('\033[1;34mINFO:\t\tSetting up "{}" PKI.\033[0m'.format(alg), file=sys.stdout)
        
        # For RSA, replace ":" with "" for the alg name used in the file paths
        if alg.startswith("RSA"):
            algname = alg.replace(":", "")
        else:
            algname = alg
        
        # Setting up the PKI (CA, ICA and EE certificates)
        pki_setup(alg, algname, out_dir)
        
    sys.exit(0)
