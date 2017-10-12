# -*- coding: utf-8 -*-
"""
"""
import json
import socket
import ssl

import h2.connection
import h2.events


def get_http2_ssl_context():
    """
    This function creates an SSLContext object that is suitably configured for
    HTTP/2. If you're working with Python TLS directly, you'll want to do the
    exact same setup as this function does.
    """
    # Get the basic context from the standard library.
    ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)

    # RFC 7540 Section 9.2: Implementations of HTTP/2 MUST use TLS version 1.2
    # or higher. Disable TLS 1.1 and lower.
    ctx.options |= (
        ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    )

    # RFC 7540 Section 9.2.1: A deployment of HTTP/2 over TLS 1.2 MUST disable
    # compression.
    ctx.options |= ssl.OP_NO_COMPRESSION

    # RFC 7540 Section 9.2.2: "deployments of HTTP/2 that       use TLS 1.2 MUST
    # support TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256". In practice, the
    # blacklist defined in this section allows only the AES GCM and ChaCha20
    # cipher suites with ephemeral key negotiation.
    ctx.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384")
    # print(ctx.get_ciphers())

    ctx.load_cert_chain(certfile="../certs/server.crt",
                        keyfile="../certs/server.key")

    # We want to negotiate using NPN and ALPN. ALPN is mandatory, but NPN may
    # be absent, so allow that. This setup allows for negotiation of HTTP/1.1.
    ctx.set_alpn_protocols(["h2", "http/1.1"])

    try:
        ctx.set_npn_protocols(["h2", "http/1.1"])
    except NotImplementedError:
        pass

    return ctx


def negotiate_tls(tcp_conn, context):
    """
    Given an established TCP connection and a HTTP/2-appropriate TLS context,
    this function:

    1. wraps TLS around the TCP connection.
    2. confirms that HTTP/2 was negotiated and, if it was not, throws an error.
    """
    tls_conn = context.wrap_socket(tcp_conn, server_side=True)

    # Always prefer the result from ALPN to that from NPN.
    # You can only check what protocol was negotiated once the handshake is
    # complete.
    negotiated_protocol = tls_conn.selected_alpn_protocol()
    if negotiated_protocol is None:
        negotiated_protocol = tls_conn.selected_npn_protocol()

    if negotiated_protocol != "h2":
        raise RuntimeError("Didn't negotiate HTTP/2!")

    return tls_conn


def send_response(conn, event):
    stream_id = event.stream_id
    # response_data = json.dumps(dict(event.headers)).encode('utf-8')

    conn.send_headers(
        stream_id=stream_id,
        headers=[
            (':status', '200'),
            ('server', 'basic-h2-server/1.0'),
            ('content-type', 'application/json'),
        ],
    )
    conn.send_data(
        stream_id=stream_id,
        data=b"this is server",
        end_stream=False
    )
    conn.send_data(
        stream_id=stream_id,
        data=b"this is server second data",
        end_stream=True
    )

def handle(tcpsock, httpconn):
    """handle something something"""
    while True:
        data = tcpsock.recv(65535)
        print("\nTLS Data:")
        print(data)
        if not data:
            break
        events = httpconn.receive_data(data)
        for event in events:
            print("\nEvent fired: " + str(event))
            if isinstance(event, h2.events.RequestReceived):
                print(event.headers)
                send_response(httpconn, event)

        data_to_send = httpconn.data_to_send()
        if data_to_send:
            tcpsock.sendall(data_to_send)

def main():
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 8080))
    sock.listen(5)

    print("TCP socket:" + str(sock))

    while True:
        print("Waiting for connection")

        tcpconn, address = sock.accept()
        print("TCP connection:" + str(tcpconn))

        context = get_http2_ssl_context()

        tls_connection = negotiate_tls(tcpconn, context)
        print("TLS Connection: " + str(tls_connection))

        config = h2.config.H2Configuration(client_side=False)
        conn = h2.connection.H2Connection(config=config)
        conn.initiate_connection()
        tls_connection.sendall(conn.data_to_send())

        print("HTTP2 connection: " + str(conn))

        handle(tls_connection, conn)

if __name__ == "__main__":
    main()