##############################################################################################
##      Title:          Post-Quantum TLS Handshake Benchmarker                              ##
##                                                                                          ##
##      Author:         Joshua Drexel, HSLU, Switzerland                                    ##
##                                                                                          ##
##      Description:    Benchmarking Post-Quantum TLS Handshake performance using           ##
##                      different signature algorithms with s_timer.                        ##
##                                                                                          ##
##      Prerequisites:                                                                      ##
##                      - Have the OQS-Provider for OpenSSL installed.                      ##
##                      - Have PATH and LD_LIBRARY_PATH adjusted to point to the OpenSSL    ##
##                        version, which has the OQS-Provider activated                     ##
##                        (if multiple OpenSSL versions are installed).                     ##
##############################################################################################

import argparse
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CWD = Path.cwd()

# Path to s_timer binary
STIMER_BINARY = CWD / "tls-client" / "s_timer"
# Path to namespace setup script
NSPACE_SETUP = CWD / "virt-test-env" / "namespace-setup.sh"
# Path to namespace cleanup script
NSPACE_CLEANUP = CWD / "virt-test-env" / "namespace-cleanup.sh"
# Path to general OpenSSL config file
OSSL_CONFIG = CWD / "emulated-nw-assessmnt" / "oqs-openssl.cnf"
# Path to OpenSSL RCA config file
OSSL_RCA_CONFIG = CWD / "emulated-nw-assessmnt" / "oqs-openssl-rca.cnf"
# Path to OpenSSL ICA config file
OSSL_ICA_CONFIG = CWD / "emulated-nw-assessmnt" / "oqs-openssl-ica.cnf"

# Sample size per iteration
# Note: The number of rounds provided as argument to this script is split up in SAMPLE_SIZE chunks.
SAMPLE_SIZE = 1

# Maximum duration in seconds for a single handshake (used for timeout)
MAX_HS_DUR = 1

# List of the traditional algorithms used for reference
# Uncomment if an algorithm should be included in the test
TRADITIONAL_SIG_ALGS = []
# TRADITIONAL_SIG_ALGS.append("ED448")
TRADITIONAL_SIG_ALGS.append("ED25519")
TRADITIONAL_SIG_ALGS.append("RSA:2048")
# TRADITIONAL_SIG_ALGS.append("RSA:3072")
# TRADITIONAL_SIG_ALGS.append("ECDSAprime256v1")
# TRADITIONAL_SIG_ALGS.append("ECDSAsecp384r1")

# Lists of Bitrate FLOAT (Mbit/s), Delay FLOAT (ms) and Packet Loss Rate FLOAT (percent) values to be emulated
# The delay will be added to both veth devices, therefore RTT is approx. twice the delay
RATE_VALUES = [10000.0]
DELAY_VALUES = [0.0, 5.0, 10.0]  # , 5.0, 50.0]
LOSS_VALUES = [0, 0.05, 0.1, 0.15]  # , 0.1, 1.0]


def run_benchmark_test(retry):
    # Prepare file paths
    ca_cert = pki_path / "ca" / "ca.crt"
    ica_cert = pki_path / "ica" / "ica.crt"
    server_cert = pki_path / "server" / "server.crt"
    server_key = pki_path / "server" / "server.key"
    client_cert = pki_path / "client" / "client.crt"
    client_key = pki_path / "client" / "client.key"

    # If record flag is set, prepare Wireshark file for traffic dump
    if record_traffic:
        traffic_recordings_file_name_server = (
            wireshark_folder_path
            / f"server-{algname}_Rate-{rate}_Delay-{delay}_Loss-{loss}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pcap"
        )
        Path(traffic_recordings_file_name_server).touch()

        traffic_recordings_file_name_client = (
            wireshark_folder_path
            / f"client-{algname}_Rate-{rate}_Delay-{delay}_Loss-{loss}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pcap"
        )
        Path(traffic_recordings_file_name_client).touch()

        # Prepare tls session secrets file for later traffic decryption in Wireshark
        session_secrets_file_name = (
            wireshark_folder_path
            / f"{algname}_Rate-{rate}_Delay-{delay}_Loss-{loss}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.secrets"
        )
        Path(session_secrets_file_name).touch()

        # Give "others" write permissions to recording file, otherwise tshark cannot record traffic (if the file is in a user's home-dir)
        Path.chmod(traffic_recordings_file_name_server, 0o666)
        Path.chmod(traffic_recordings_file_name_client, 0o666)

        # Start wireshark process in namespace ns1 (server)
        # Note: Use Popen, as the process needs to run in background
        # fmt: off
        wireshark_server = subprocess.Popen(
            ["sudo", "ip", "netns", "exec", "ns1", "tshark", "-i", "veth1", "-w", traffic_recordings_file_name_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # fmt: on

        # Wait for wireshark to start
        time.sleep(2)

        if wireshark_server is None:
            print(
                "\033[1;31mERROR:\t\tFailure during start of wireshark for server. Aborting.\033[0m",
                file=sys.stderr,
            )
            sys.exit(-1)

        # Start wireshark process in namespace ns2 (client)
        # Note: Use Popen, as the process needs to run in background
        # fmt: off
        wireshark_client = subprocess.Popen(
            ["sudo", "ip", "netns", "exec", "ns2", "tshark", "-i", "veth2", "-w", traffic_recordings_file_name_client],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # fmt: on

        # Wait for wireshark to start
        time.sleep(2)

        if wireshark_client is None:
            print(
                "\033[1;31mERROR:\t\tFailure during start of wireshark for client. Aborting.\033[0m",
                file=sys.stderr,
            )
            sys.exit(-1)

    # Split in SAMPLE_SIZE-chunks of rounds to fail faster and repeat the execution if TIMEOUT is reached
    open_rounds = rounds
    output_iterator = 1

    while open_rounds > 0:

        if open_rounds - SAMPLE_SIZE >= 0:
            # Another full SAMPLE_SIZE-rounds chunk to go
            run_rounds = SAMPLE_SIZE
            open_rounds = open_rounds - SAMPLE_SIZE
        else:
            # Run a last time with the left-over rounds to go
            run_rounds = open_rounds
            open_rounds = 0

        # Start s_server process in namespace ns1
        if record_traffic:
            # fmt: off
            tls_server = subprocess.Popen(
                [
                    "sudo", f"OPENSSL_CONF={OSSL_CONFIG}", "ip", "netns", "exec", "ns1", "openssl", "s_server", "-cert",
                    server_cert, "-key", server_key, "-tls1_3", "-Verify", "2", "-verify_return_error", "-CAfile",
                    ca_cert, "-chainCAfile", ica_cert, "-ignore_unexpected_eof", "-keylogfile", session_secrets_file_name
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # fmt: on
        else:
            # fmt: off
            tls_server = subprocess.Popen(
                [
                    "sudo", f"OPENSSL_CONF={OSSL_CONFIG}", "ip", "netns", "exec", "ns1", "openssl", "s_server", "-cert",
                    server_cert, "-key", server_key, "-tls1_3", "-verify", "2", "-verify_return_error", "-CAfile",
                    ca_cert, "-chainCAfile", ica_cert, "-ignore_unexpected_eof"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # fmt: on

        # Wait for server to start
        time.sleep(0.2)

        # Check if process start was successful
        if tls_server is None:
            print(
                "\033[1;31mERROR:\t\tFailure during start of TLS server. Aborting.\033[0m",
                file=sys.stderr,
            )
            sys.exit(-1)

        # Start s_timer process in namespace ns2
        # fmt: off
        tls_client = subprocess.Popen(
            [
                "sudo", "ip", "netns", "exec", "ns2", STIMER_BINARY, "-h", "10.5.0.1:4433",
                "-r", str(run_rounds), f"--cert={client_cert}", f"--key={client_key}",
                f"--rootcert={ca_cert}", f"--chaincert={ica_cert}", f"--config={OSSL_CONFIG}"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # fmt: on

        # It is assumed that no more than MAX_HS_DUR seconds per handshake are required.
        timeout = MAX_HS_DUR * run_rounds

        try:
            tls_client.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(
                f"\033[1;31mERROR:\t\tTimeout reached for {alg} with rate of {rate}, {delay}ms delay and {loss}% packet loss. Repeating the test.\033[0m",
                file=sys.stderr,
            )

            # End all processes
            tls_server.terminate()
            tls_client.terminate()

            # Adding up the failed rounds and start again
            open_rounds = open_rounds + run_rounds

            continue

        # Save output line by line in array
        s_time_output = bytes.decode(tls_client.stdout.read(), "utf-8").splitlines()

        # Check that OpenSSL >= 3.2.0 was used
        # Note: s_timer outputs the OpenSSL version in the first output line

        openssl_version = extract_openssl_version(s_time_output[0])
        if openssl_version < [3, 2, 0]:
            # Correct version string not found, abort
            print(
                "\033[1;31mERROR:\t\tWrong OpenSSL version in s_timer. Aborting.\033[0m",
                file=sys.stderr,
            )
            sys.exit(-1)
        else:
            # Check if provider could be loaded successfully
            # Note: s_timer output if provider load was successful on the second line
            if s_time_output[1].find("provider loaded successfully") < 0:
                # Provider not found
                print(
                    "\033[1;31mERROR:\t\tOQS-Provider in s_timer not loaded. Aborting.\033[0m",
                    file=sys.stderr,
                )
                sys.exit(-1)
            else:
                # Provider loaded successfully, print results
                for result in s_time_output[-1].split(","):
                    # s_timer outputs results as pairs of measurement:success (float:bool)
                    # Note: If connection was unsuccessful (success=false), a value of -1.0ms is returned as measurement
                    measurement, success = result.split(":")
                    with open(results_file_name, "a") as results_file:
                        results_file.write(
                            f"{alg},{output_iterator},{rate},{delay},{loss},{success},{measurement}\n"
                        )
                    output_iterator = output_iterator + 1

                print(
                    f"SUCCESS:(Round {open_rounds}). {alg}, {rate}mbit, {delay}ms delay, {loss}% packet loss.",
                    file=sys.stdout,
                )

        # Terminate TLS server process
        tls_server.terminate()

        # End of while loop

    if record_traffic:
        time.sleep(2)
        wireshark_server.terminate()
        wireshark_client.terminate()

    return


def pki_setup(alg, algname, out_dir):
    # Prepare parent directory for algorithm specific PKI
    pki_path = out_dir / f"pki-{algname}"
    create_dir(pki_path)
    ca_config = pki_path / "oqs-openssl-ca.cnf"
    ica_config = pki_path / "oqs-openssl-ica.cnf"

    # Create sub-directory for CA, prepare file paths, create and init serial-number file
    ca_path = pki_path / "ca"
    create_dir(ca_path)
    ca_cert = ca_path / "ca.crt"
    ca_key = ca_path / "ca.key"
    with open(ca_path / "serial", "a") as serial_file:
        serial_file.write("1000")
    Path(ca_path / "index.txt").touch()
    # Copy CA config, but set real CA path
    with open(OSSL_RCA_CONFIG, "rt") as template_config:
        with open(ca_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace("{path}", str(ca_path)))

    # Create sub-directory for ICA, prepare file paths, create and init serial-number file
    ica_path = pki_path / "ica"
    create_dir(ica_path)
    ica_cert = ica_path / "ica.crt"
    ica_csr = ica_path / "ica.csr"
    ica_key = ica_path / "ica.key"
    with open(ica_path / "serial", "a") as file:
        file.write("1000")
    Path(ica_path / "index.txt").touch()
    # Copy ICA config, but set real ICA path
    with open(OSSL_ICA_CONFIG, "rt") as template_config:
        with open(ica_config, "wt") as new_config:
            for line in template_config:
                new_config.write(line.replace("{path}", str(ica_path)))

    # Create sub-directory for server certificate, prepare file paths
    server_path = pki_path / "server"
    create_dir(server_path)
    server_cert = server_path / "server.crt"
    server_csr = server_path / "server.csr"
    server_key = server_path / "server.key"

    # Create sub-directory for client certificate, prepare file paths
    client_path = pki_path / "client"
    create_dir(client_path)
    client_cert = client_path / "client.crt"
    client_csr = client_path / "client.csr"
    client_key = client_path / "client.key"

    ####################################################################
    # Create CA key and certificate
    # Note: if/else is needed, because ECDSA needs additional arguments than EdDSA, RSA and PQC
    if alg.startswith("ECDSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg[5:]
            + " - Test Root CA"
        )
        ec_param = "ec_paramgen_curve:" + alg[5:]
        # fmt: off
        ca_cert_process = subprocess.run(
            [
                "openssl", "req", "-x509", "-new", "-sha256", "-newkey", "ec", "-pkeyopt", ec_param,
                "-keyout", ca_key, "-out", ca_cert, "-nodes", "-subj", subject, "-days", "7300",
                "-extensions", "v3_ca", "-config", ca_config
            ],
            capture_output=True,
            text=True,
        )
        # fmt: on
    else:
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Test Root CA"
        )
        # fmt: off
        ca_cert_process = subprocess.run(
            [
                "openssl", "req", "-x509", "-new", "-sha256", "-newkey", alg, "-keyout", ca_key,
                "-out", ca_cert, "-nodes", "-subj", subject, "-days", "7300", "-extensions",
                "v3_ca", "-config", ca_config
            ],
            capture_output=True,
            text=True,
        )
        # fmt: on

    if ca_cert_process.returncode != 0:
        # Print the error messages from subprocess
        print(ca_cert_process.stderr)
        print(
            "\033[1;31mERROR:\t\tError during CA setup. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    ####################################################################
    # Create Intermediate-CA key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg[5:]
            + " - Test Intermediate CA"
        )
        # fmt: off
        ica_key_process = subprocess.run(
            ["openssl", "ecparam", "-name", alg[5:], "-genkey", "-out", ica_key],
            capture_output=True,
            text=True,
        )
        # fmt: on
    elif alg.startswith("RSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Test Intermediate CA"
        )
        # fmt: off
        ica_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg[:3], "-pkeyopt", f"rsa_keygen_bits:{alg[4:]}", "-out", ica_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on
    else:
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Test Intermediate CA"
        )
        # fmt: off
        ica_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg, "-out", ica_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on

    # fmt: off
    ica_csr_process = subprocess.run(
        [
            "openssl", "req", "-new", "-sha256", "-key", ica_key,
            "-out", ica_csr, "-subj", subject, "-config", ica_config,
        ],
        capture_output=True,
        text=True,
    )
    ica_cert_process = subprocess.run(
        [
            "openssl", "ca", "-extensions", "v3_intermediate_ca", "-md", "sha256", "-batch",
            "-in", ica_csr, "-out", ica_cert, "-days", "3650", "-config", ca_config
        ],
        capture_output=True,
        text=True,
    )
    # fmt: on

    if (
        ica_key_process.returncode != 0
        or ica_csr_process.returncode != 0
        or ica_cert_process.returncode != 0
    ):
        # Print the error messages from subprocess
        print(ica_key_process.stderr)
        print(ica_csr_process.stderr)
        print(ica_cert_process.stderr)
        print(
            "\033[1;31mERROR:\t\tError during ICA setup. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    ####################################################################
    # Create Server key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg[5:]
            + " - Server Certificate"
        )
        # fmt: off
        server_key_process = subprocess.run(
            ["openssl", "ecparam", "-name", alg[5:], "-genkey", "-out", server_key],
            capture_output=True,
            text=True,
        )
        # fmt: on
    elif alg.startswith("RSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Server Certificate"
        )
        # fmt: off
        server_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg[:3], "-pkeyopt", f"rsa_keygen_bits:{alg[4:]}", "-out", server_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on
    else:
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Server Certificate"
        )
        # fmt: off
        server_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg, "-out", server_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on

    # fmt: off
    server_csr_process = subprocess.run(
        [
            "openssl", "req", "-new", "-sha256", "-key", server_key, "-out",
            server_csr, "-subj", subject, "-config", ica_config
        ],
        capture_output=True,
        text=True,
    )
    server_cert_process = subprocess.run(
        [
            "openssl", "ca", "-extensions", "server_cert", "-md", "sha256", "-batch",
            "-in", server_csr, "-out", server_cert, "-days", "365", "-config", ica_config
        ],
        capture_output=True,
        text=True,
    )
    # fmt: on

    if (
        server_key_process.returncode != 0
        or server_csr_process.returncode != 0
        or server_cert_process.returncode != 0
    ):
        # Print the error messages from subprocess
        print(server_key_process.stderr)
        print(server_csr_process.stderr)
        print(server_cert_process.stderr)
        print(
            "\033[1;31mERROR:\t\tError during server certificate setup. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    ####################################################################
    # Create Client key, CSR and certificate
    if alg.startswith("ECDSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg[5:]
            + " - Client Certificate"
        )
        # fmt: off
        client_key_process = subprocess.run(
            ["openssl", "ecparam", "-name", alg[5:], "-genkey", "-out", client_key],
            capture_output=True,
            text=True,
        )
        # fmt: on
    elif alg.startswith("RSA"):
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Client Certificate"
        )
        # fmt: off
        client_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg[:3], "-pkeyopt", f"rsa_keygen_bits:{alg[4:]}", "-out", client_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on
    else:
        subject = (
            "/C=CH/ST=Zug/L=Rotkreuz/O=Lucerne University of Applied Sciences and Arts/OU=Applied Cyber Security Research Lab/CN="
            + alg
            + " - Client Certificate"
        )
        # fmt: off
        client_key_process = subprocess.run(
            ["openssl", "genpkey", "-algorithm", alg, "-out", client_key, "-config", ica_config],
            capture_output=True,
            text=True,
        )
        # fmt: on

    # fmt: off
    client_csr_process = subprocess.run(
        [
            "openssl", "req", "-new", "-sha256", "-key", client_key, "-out",
            client_csr, "-subj", subject, "-config", ica_config
        ],
        capture_output=True,
        text=True,
    )
    client_cert_process = subprocess.run(
        [
            "openssl", "ca", "-extensions", "server_cert", "-md", "sha256", "-batch", "-in",
            client_csr, "-out", client_cert, "-days", "365", "-config", ica_config
        ],
        capture_output=True,
        text=True,
    )
    # fmt: on

    if (
        client_key_process.returncode != 0
        or client_csr_process.returncode != 0
        or client_cert_process.returncode != 0
    ):
        # Print the error messages from subprocess
        print(client_key_process.stderr)
        print(client_csr_process.stderr)
        print(client_cert_process.stderr)
        print(
            "\033[1;31mERROR:\t\tError during server certificate setup. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    return


def namespaces_setup(has_failed):
    print("\033[1;34mINFO:\t\tSetting up namespaces.\033[0m", file=sys.stdout)

    ns_process = subprocess.run(["bash", NSPACE_SETUP], capture_output=True)

    if ns_process.returncode != 0 and not has_failed:
        print(
            "\033[1;33mWARNING:\tError during namespace setup. Will do cleanup and retry again.\033[0m",
            file=sys.stdout,
        )
        namespaces_cleanup()
        namespaces_setup(True)
    elif ns_process.returncode != 0 and has_failed:
        print(
            "\033[1;31mERROR:\t\tFailure during namespace setup. Cleanup did not help. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    return


def namespaces_cleanup():
    print("\033[1;34mINFO:\t\tCleaning up namespaces.\033[0m", file=sys.stdout)

    ns_process = subprocess.run(["bash", NSPACE_CLEANUP], capture_output=True)

    if ns_process.returncode != 0:
        print(
            "\033[1;31mERROR:\t\tFailure during namespace cleanup. Aborting.\033[0m",
            file=sys.stderr,
        )
        sys.exit(-1)

    return


def read_pq_sigalgs(sig_file):
    algs_from_file = []
    algs_supported = []

    # First get the list of supported signature algorithms of the OpenSSL installation
    process = subprocess.run(
        ["openssl", "list", "-signature-algorithms"], capture_output=True
    )

    for line in process.stdout.splitlines():
        l = str(line.rstrip())[2:-1]
        if l.endswith(" @ oqsprovider"):
            algs_supported.append(l[2:-14])

    # Get the signature algorithms from the file and check if they are supported, otherwise exclude from list
    with open(sig_file, "r", encoding="UTF-8") as file:
        while line := file.readline():
            algname = line.rstrip()
            if algname in algs_supported:
                # Algorithm is supported, add it to the list
                algs_from_file.append(line.rstrip())
            else:
                print(
                    f"WARNING:Algorithm {algname} not supported, removed from list.",
                    file=sys.stderr,
                )

        # Check if there are signature algorithms found in the file provided, otherwise exit with error
        if not algs_from_file:
            print(
                f"ERROR: No supported algorithms found in {sig_file}. Aborting.",
                file=sys.stderr,
            )
            sys.exit(-1)
    return algs_from_file


def create_dir(path):
    if not path.exists():
        Path.mkdir(path)
    else:
        overwriting = ask_for_overwrite(path)

        if overwriting == "yes":
            # Delete directory and all contained subdirs and files
            shutil.rmtree(path)

            # Re-create the directory
            Path.mkdir(path)
            print(
                f"INFO: File/Directory {path} overwritten.",
                file=sys.stdout,
            )
        elif overwriting == "no":
            print(
                f"INFO: File/Directory {path} is not overwritten.",
                file=sys.stdout,
            )
        else:
            print(
                "ERROR: Failure during file/directory operation. Aborting.",
                file=sys.stderr,
            )
            sys.exit(-1)
    return


def ask_for_overwrite(path):
    yes = {"yes", "y", "ye"}
    no = {"no", "n", ""}

    choice = input(
        f'Directory or file "{path}" already exists. Should it be overwritten (ALL subdirectories and files will be lost!)? [y/N] '
    ).lower()

    if choice in yes:
        return "yes"
    elif choice in no:
        return "no"
    else:
        print(
            "\033[1;34mINFO:\t\tPlease respond with yes or no.\033[0m", file=sys.stdout
        )
        ask_for_overwrite(path)
    return


def extract_openssl_version(text):
    pattern = r"OpenSSL (\d+)\.(\d+)\.(\d+)"
    match = re.search(pattern, text)

    if match:
        version = [int(match.group(1)), int(match.group(2)), int(match.group(3))]
        return version
    else:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Post-Quantum TLS Handshake Benchmarker",
        description="Benchmarking Post-Quantum TLS Handshake performance using different signature algorithms with OpenSSL s_time.",
    )
    parser.add_argument(
        "-rounds",
        help="the number of times the test should be performed for, default is 10",
        metavar="INT",
        type=int,
        default="10",
        required=False,
    )
    parser.add_argument(
        "-sigs",
        help="path to file with list of PQ signature algorithms to be included in the tests",
        metavar="<file path>",
        default="sig-list-test.txt",
        required=False,
    )
    parser.add_argument(
        "-out",
        help="path to directory where the results should be saved to",
        metavar="<dir path>",
        default="./tmp",
        required=False,
    )
    parser.add_argument(
        "-rec",
        help="if set, the TLS traffic is dumped to a file and the session secrets are exported",
        action="store_true",
        default=True,
        required=False,
    )

    args = parser.parse_args()

    rounds = args.rounds
    sig_file = Path(args.sigs)
    out_dir = Path(args.out)
    record_traffic = args.rec

    # Make sure that the PQ signature algorithm file exists
    if not sig_file.is_file():
        print(
            f"ERROR: File {sig_file} does not exist.",
            file=sys.stderr,
        )
        sys.exit(-1)

    # Check if output directory exists
    if not out_dir.is_dir():
        print(
            f"ERROR: Directory {out_dir} does not exist.",
            file=sys.stderr,
        )
        sys.exit(-1)

    # Prepare file for benchmark results
    results_file_name = (
        out_dir / f"results_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv"
    )
    with open(results_file_name, "a") as results_file:
        results_file.write(
            "Signature Algorithm,Test Round,Rate Limit,Delay,Packet Loss,Success,Handshake Duration [ms]"
            + "\n"
        )

    # If traffic is to be recorded, prepare folder
    if record_traffic:
        # Prepare folder for wireshark dump files
        wireshark_folder_path = out_dir / "traffic-recordings"
        create_dir(wireshark_folder_path)

    # Read the post-quantum signature algorithms from file and check if activated in oqs-provider
    pq_sig_algs = read_pq_sigalgs(sig_file)

    # Add the reference algorithms (traditional crypto, provided in global variable) to the list
    sig_algs = TRADITIONAL_SIG_ALGS + pq_sig_algs

    # Setup of namespaces and virtual Ethernet devices
    # Note: Perform a cleanup first, just to make sure to have a clean state
    namespaces_cleanup()
    namespaces_setup(False)

    # Initialize network emulation on ns1 and ns2 with rate limit of 10 Gbit/s, 0 delay and 0 packet loss
    # fmt: off
    subprocess.run([
        "sudo", "ip", "netns", "exec", "ns1", "tc", "qdisc",
        "add", "dev", "veth1", "root", "netem", "rate", "10000.0mbit",
        "delay", "0ms", "loss", "0%"
    ])
    subprocess.run([
        "sudo", "ip", "netns", "exec", "ns2", "tc", "qdisc",
        "add", "dev", "veth2", "root", "netem", "rate", "10000.0mbit",
        "delay", "0ms", "loss", "0%"
    ])

    # Hard-Code MAC Addresses to prevent ARP resolutions which may cause the processes to hang, especially with high packet loss rates
    subprocess.run([
        "sudo", "ip", "netns", "exec", "ns1", "ip", "neighbor",
        "add", "10.5.0.1", "lladdr", "00:00:00:00:00:02",
        "nud", "permanent", "dev", "veth1"
    ])
    subprocess.run([
        "sudo", "ip", "netns", "exec", "ns2", "ip", "neighbor",
        "add", "10.6.0.1", "lladdr", "00:00:00:00:00:01",
        "nud", "permanent", "dev", "veth2"
    ])
    # fmt: on

    # Perform benchmark test for each signature algorithm
    for alg in sig_algs:
        print(
            f"INFO: Setting up {alg} PKI.",
            file=sys.stdout,
        )

        # For RSA, replace ":" with "" for the alg name used in the file paths
        if alg.startswith("RSA"):
            algname = alg.replace(":", "")
        else:
            algname = alg

        # Setting up the PKI (CA, ICA and EE certificates)
        pki_setup(alg, algname, out_dir)
        pki_path = out_dir / f"pki-{algname}"

        print(
            f"INFO: Starting {alg} benchmark tests.",
            file=sys.stdout,
        )
        # Run s_timer benchmark test for each rate, delay and loss value
        for rate in RATE_VALUES:
            for delay in DELAY_VALUES:
                for loss in LOSS_VALUES:
                    print(
                        f"INFO: Rate = {rate}Mbit/s, Delay = {delay}ms, Packet Loss Rate = {loss}%.",
                        file=sys.stdout,
                    )
                    # Change network emulation to specified delay and loss
                    # fmt: off
                    subprocess.run([
                        "sudo", "ip", "netns", "exec", "ns1", "tc", "qdisc", "change",
                        "dev", "veth1", "root", "netem", "rate", f"{rate}mbit",
                        "delay", f"{delay}ms", "loss", f"{loss}%"
                    ])
                    subprocess.run([
                        "sudo", "ip", "netns", "exec", "ns2", "tc", "qdisc", "change",
                        "dev", "veth2", "root", "netem", "rate", f"{rate}mbit",
                        "delay", f"{delay}ms", "loss", f"{loss}%"
                    ])
                    # fmt: on

                    # Execute the test using s_timer
                    run_benchmark_test(0)

    # Cleaning up namespaces and virtual Ethernet devices
    namespaces_cleanup()

    print(
        f"SUCCESS: Results were stored in {results_file_name.name}. Finished.",
        file=sys.stdout,
    )
    sys.exit(0)
