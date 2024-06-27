/*
 * Copyright 1995-2018 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License"). You may not use
 * this file except in compliance with the License. You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

/*
 * ADDITIONAL COPYRIGHT NOTICE
 *
 * Many parts of this code originate from
 * https://github.com/xvzcf/pq-tls-benchmark/blob/master/emulation-exp/code/sig/s_timer.c,
 * which is an adaption of OpenSSL's s_time.c.
 *
 * The code was further adapted to the needs of the Master's Thesis by
 * Joshua Drexel, Lucerne University of Applied Sciences and Arts.
 */

#include <argp.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <openssl/conf.h>
#include <openssl/err.h>
#include <openssl/provider.h>
#include <openssl/ssl.h>

#define NS_IN_MS 1000000.0
#define MS_IN_S 1000

// Command Line Argument Parser
const char *argp_program_version = "s_timer-0.0.1";
const char *argp_program_bug_address = "joshua.drexel@stud.hslu.ch";
static char doc[] = "This is an adaption of the OpenSSL s_time program. This "
                    "program performs an mTLS handshake and measures the time "
                    "it takes to complete the handshake.";
static char args_doc[] = "-h HOST:PORT -r ROUNDS --config=PATH --rootcert=PATH "
                         "--chaincert=PATH --cert=PATH --key=PATH";
static struct argp_option options[] = {
    {"host", 'h', "IP:PORT", 0, "Destination host IP address and Port."},
    {"rounds", 'r', "INT", 0, "Number of rounds the test should be repeated."},
    {"config", 1, "PATH", 0,
     "Path to openssl config file that has the oqs-provider enabled."},
    {"rootcert", 2, "PATH", 0, "Path to the Root-CA certificate."},
    {"chaincert", 3, "PATH", 0, "Path to the Intermediate-CA certificate."},
    {"cert", 4, "PATH", 0, "Path to the client certificate."},
    {"key", 5, "PATH", 0, "Path to the client key."},
    {0}};

struct arguments {
  char *host_name;
  size_t rounds;
  char *config_file;
  char *ca_cert;
  char *ica_cert;
  char *client_cert;
  char *client_key;
};

static struct arguments arguments;

static error_t parse_opt(int key, char *arg, struct argp_state *state) {
  struct arguments *arguments = state->input;
  switch (key) {
  case 'h':
    arguments->host_name = arg;
    break;
  case 'r':
    arguments->rounds = atoi(arg);
    break;
  case 1:
    arguments->config_file = arg;
    break;
  case 2:
    arguments->ca_cert = arg;
    break;
  case 3:
    arguments->ica_cert = arg;
    break;
  case 4:
    arguments->client_cert = arg;
    break;
  case 5:
    arguments->client_key = arg;
    break;
  default:
    return ARGP_ERR_UNKNOWN;
  }
  return 0;
}

static struct argp argp = {options, parse_opt, args_doc, doc};

int loadOQSProvider(const char *providerPath) {
  // Load the OQS provider dynamically
  if (providerPath) {
    if (CONF_modules_load_file(NULL, providerPath, 0) <= 0) {
      fprintf(stderr, "Error loading OQS provider from %s\n", providerPath);
      return 1;
    }
  }
  return 0;
}

// This is the function for which the time is measured,
// therefore keep it as clean as possible
SSL *do_tls_handshake(SSL_CTX *ssl_ctx) {
  BIO *conn = NULL;
  SSL *ssl = NULL;
  int ret;

  conn = BIO_new(BIO_s_connect());
  if (!conn) {
    return NULL;
  }

  BIO_set_conn_hostname(conn, arguments.host_name);
  BIO_set_conn_mode(conn, BIO_SOCK_NODELAY);

  ssl = SSL_new(ssl_ctx);
  if (!ssl) {
    BIO_free(conn);
    return NULL;
  }

  SSL_set_bio(ssl, conn, conn);

  /* ok, lets connect */
  ret = SSL_connect(ssl);
  if (ret <= 0) {
    ERR_print_errors_fp(stderr);
    SSL_free(ssl);
    return NULL;
  }

#if defined(SOL_SOCKET) && defined(SO_LINGER)
  {
    struct linger no_linger = {.l_onoff = 1, .l_linger = 0};
    int fd = SSL_get_fd(ssl);
    if (fd >= 0) {
      (void)setsockopt(fd, SOL_SOCKET, SO_LINGER, (char *)&no_linger,
                       sizeof(no_linger));
    }
  }
#endif
  return ssl;
}

int main(int argc, char *args[]) {
  int ret = -1;
  SSL_CTX *ssl_ctx = NULL;

  // Prepare for CLI arguments parsing
  arguments.host_name = "";
  arguments.rounds = 1;
  arguments.config_file = "";
  arguments.ca_cert = "";
  arguments.ica_cert = "";
  arguments.client_cert = "";
  arguments.client_key = "";

  // Parse the CLI arguments
  argp_parse(&argp, argc, args, 0, 0, &arguments);

  // Counter for number of measurements taken (performed rounds)
  size_t measurements = 0;

  // Fix cipher suite
  const char *ciphersuites = "TLS_AES_256_GCM_SHA384";

  // Fix KEX mechanism
  const char *kex = "x25519_kyber768";

  const SSL_METHOD *ssl_meth = TLS_client_method();
  SSL *ssl = NULL;

  struct timespec start, finish;
  double *handshake_times_ms =
      malloc(arguments.rounds * sizeof(*handshake_times_ms));
  bool *conn_success = malloc(arguments.rounds * sizeof(*conn_success));

  if (!handshake_times_ms || !conn_success) {
    fprintf(stderr, "Memory allocation failed.\n");
    free(handshake_times_ms);
    free(conn_success);
    return 1;
  }

  ssl_ctx = SSL_CTX_new(ssl_meth);
  if (!ssl_ctx) {
    fprintf(stderr, "Failed to create SSL context.\n");
    free(handshake_times_ms);
    free(conn_success);
    return 1;
  }

  // Print OpenSSL version and build information
  printf("OpenSSL Version: %s\n", OpenSSL_version(OPENSSL_VERSION));

  SSL_CTX_set_mode(ssl_ctx, SSL_MODE_AUTO_RETRY);
  SSL_CTX_set_quiet_shutdown(ssl_ctx, 1);

  ret = SSL_CTX_set_min_proto_version(ssl_ctx, TLS1_3_VERSION);
  if (ret != 1) {
    goto ossl_error;
  }

  ret = SSL_CTX_set_max_proto_version(ssl_ctx, TLS1_3_VERSION);
  if (ret != 1) {
    goto ossl_error;
  }

  SSL_CTX_set_options(ssl_ctx, SSL_OP_NO_COMPRESSION);

  ret = SSL_CTX_set_ciphersuites(ssl_ctx, ciphersuites);
  if (ret != 1) {
    goto ossl_error;
  }

  ret = SSL_CTX_set1_groups_list(ssl_ctx, kex);
  if (ret != 1) {
    goto ossl_error;
  }

  // Load CA certificate as trust anchor
  ret = SSL_CTX_load_verify_locations(ssl_ctx, arguments.ca_cert, 0);
  if (ret <= 0) {
    goto ossl_error;
  }

  // Load the intermediate CA certificate
  X509 *intermediate_cert = NULL;
  FILE *intermediate_file = fopen(arguments.ica_cert, "r");
  if (intermediate_file) {
    intermediate_cert = PEM_read_X509(intermediate_file, NULL, NULL, NULL);
    fclose(intermediate_file);
  }

  if (!intermediate_cert) {
    fprintf(stderr, "Error loading intermediate CA certificate.\n");
    SSL_CTX_free(ssl_ctx);
    goto ossl_error;
  }

  // Add the intermediate CA certificate to the chain
  if (SSL_CTX_add_extra_chain_cert(ssl_ctx, intermediate_cert) <= 0) {
    fprintf(stderr, "Error adding intermediate CA certificate to the chain.\n");
    X509_free(intermediate_cert);
    SSL_CTX_free(ssl_ctx);
    goto ossl_error;
  }

  // Load the client certificate and key
  if (SSL_CTX_use_certificate_file(ssl_ctx, arguments.client_cert,
                                   SSL_FILETYPE_PEM) <= 0) {
    ERR_print_errors_fp(stderr);
    SSL_CTX_free(ssl_ctx);
    goto ossl_error;
  }

  if (SSL_CTX_use_PrivateKey_file(ssl_ctx, arguments.client_key,
                                  SSL_FILETYPE_PEM) <= 0) {
    ERR_print_errors_fp(stderr);
    SSL_CTX_free(ssl_ctx);
    goto ossl_error;
  }

  // Check if the private key matches the certificate
  if (!SSL_CTX_check_private_key(ssl_ctx)) {
    fprintf(stderr, "Private key does not match the certificate.\n");
    SSL_CTX_free(ssl_ctx);
    goto ossl_error;
  }

  SSL_CTX_set_verify(ssl_ctx, SSL_VERIFY_PEER, NULL);

  // Load OQS-Provider
  const char *providerPath = arguments.config_file;
  if (loadOQSProvider(providerPath) == 0) {
    printf("OQS provider loaded successfully.\n");
  } else {
    fprintf(stderr, "Failed to load OQS provider.\n");
    goto ossl_error;
  }

  while (measurements < arguments.rounds) {
    clock_gettime(CLOCK_MONOTONIC_RAW, &start);
    ssl = do_tls_handshake(ssl_ctx);
    clock_gettime(CLOCK_MONOTONIC_RAW, &finish);
    if (!ssl) {
      // Handshake unsuccessful
      conn_success[measurements] = false;
      handshake_times_ms[measurements] = -1.0;
    } else {
      // Handshake successful
      conn_success[measurements] = true;
      handshake_times_ms[measurements] =
          ((finish.tv_sec - start.tv_sec) * MS_IN_S) +
          ((finish.tv_nsec - start.tv_nsec) / NS_IN_MS);

      SSL_set_shutdown(ssl, SSL_SENT_SHUTDOWN | SSL_RECEIVED_SHUTDOWN);
      ret = BIO_closesocket(SSL_get_fd(ssl));
      if (ret == -1) {
        goto ossl_error;
      }

      SSL_free(ssl);
    }

    // Go to next test round
    // Note: Unsuccessful connections are also counted as a test round
    measurements++;
  }

  for (size_t i = 0; i < measurements - 1; i++) {
    printf("%f:%i,", handshake_times_ms[i], conn_success[i]);
  }
  printf("%f:%i", handshake_times_ms[measurements - 1],
         conn_success[measurements - 1]);

  ret = 0;
  goto end;

ossl_error:
  fprintf(stderr, "Unrecoverable OpenSSL error.\n");
  ERR_print_errors_fp(stderr);

end:
  SSL_CTX_free(ssl_ctx);
  free(handshake_times_ms);
  free(conn_success);
  return ret;
}
