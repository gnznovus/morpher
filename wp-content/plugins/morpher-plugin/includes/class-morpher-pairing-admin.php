<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Pairing_Admin {
    private $auth;

    public function __construct( Morpher_Auth $auth ) {
        $this->auth = $auth;
    }

    public function register() {
        add_action( 'admin_menu', array( $this, 'register_menu' ) );
    }

    public function register_menu() {
        add_submenu_page(
            'morpher',
            'Morpher Connection',
            'Connection',
            'manage_options',
            'morpher-connection',
            array( $this, 'render_page' )
        );
    }

    public function render_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }

        $pairing = null;
        $message = '';

        if ( isset( $_POST['morpher_pairing_action'] ) ) {
            check_admin_referer( 'morpher_pairing' );
            $action = sanitize_key( wp_unslash( $_POST['morpher_pairing_action'] ) );

            if ( 'start' === $action ) {
                $pairing = $this->auth->start_pairing();
            } elseif ( 'revoke' === $action ) {
                $this->auth->revoke();
                $message = 'Morpher connection revoked.';
            }
        }

        $connected     = $this->auth->is_connected();
        $dashboard_url = apply_filters( 'morpher_dashboard_url', 'http://127.0.0.1:8765' );
        ?>
        <div class="wrap">
            <h1>Morpher Connection</h1>
            <p>Pair this WordPress site with one Morpher app connection.</p>

            <?php if ( $message ) : ?>
                <div class="notice notice-success inline"><p><?php echo esc_html( $message ); ?></p></div>
            <?php endif; ?>

            <table class="widefat striped" style="max-width: 720px; margin-top: 16px;">
                <tbody>
                    <tr>
                        <th scope="row" style="width: 180px;">Connection</th>
                        <td id="morpher-connection-status"><?php echo esc_html( $connected ? 'Paired' : 'Not paired' ); ?></td>
                    </tr>
                    <tr>
                        <th scope="row">Site</th>
                        <td><code><?php echo esc_html( get_site_url() ); ?></code></td>
                    </tr>
                    <?php if ( $this->auth->connection_ref_no() ) : ?>
                    <tr>
                        <th scope="row">Ref No.</th>
                        <td><code><?php echo esc_html( $this->auth->connection_ref_no() ); ?></code></td>
                    </tr>
                    <?php endif; ?>
                </tbody>
            </table>

            <?php if ( $pairing ) : ?>
                <div class="notice notice-info inline" style="max-width: 680px; margin-top: 16px; padding: 12px 16px;">
                    <p><strong>Pairing request created.</strong></p>
                    <p>Ref No. <code><?php echo esc_html( $pairing['ref_no'] ); ?></code></p>
                    <p id="morpher-pairing-request-status">Sending request to the local Morpher dashboard...</p>
                </div>
            <?php endif; ?>

            <form method="post" style="margin-top: 20px;">
                <?php wp_nonce_field( 'morpher_pairing' ); ?>
                <input type="hidden" name="morpher_pairing_action" value="start">
                <?php submit_button( $connected ? 'Pair a new Morpher app' : 'Start pairing', 'primary', 'submit', false ); ?>
            </form>

            <?php if ( $connected ) : ?>
                <form method="post" style="margin-top: 12px;">
                    <?php wp_nonce_field( 'morpher_pairing' ); ?>
                    <input type="hidden" name="morpher_pairing_action" value="revoke">
                    <?php submit_button( 'Revoke Morpher connection', 'secondary', 'submit', false ); ?>
                </form>
            <?php endif; ?>
        </div>

        <?php if ( $pairing ) : ?>
        <script>
        (() => {
            const status = document.getElementById('morpher-pairing-request-status');
            const connectionStatus = document.getElementById('morpher-connection-status');
            const refNo = <?php echo wp_json_encode( $pairing['ref_no'] ); ?>;
            const request = {
                request_id: <?php echo wp_json_encode( $pairing['request_id'] ); ?>,
                ref_no: refNo,
                site_url: <?php echo wp_json_encode( get_site_url() ); ?>,
                site_name: <?php echo wp_json_encode( get_bloginfo( 'name' ) ); ?>,
                plugin_version: <?php echo wp_json_encode( MORPHER_PLUGIN_VERSION ); ?>,
                wordpress_version: <?php echo wp_json_encode( get_bloginfo( 'version' ) ); ?>,
                code: <?php echo wp_json_encode( $pairing['code'] ); ?>,
                expires_in: <?php echo (int) $pairing['expires_in']; ?>
            };

            fetch(<?php echo wp_json_encode( trailingslashit( $dashboard_url ) . 'api/pairing/requests' ); ?>, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(request)
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`Morpher dashboard returned ${response.status}`);
                    return response.json();
                })
                .then(() => {
                    status.textContent = `Sent to Morpher. Waiting for approval — ${refNo}`;
                    const poll = window.setInterval(() => {
                        fetch(<?php echo wp_json_encode( rest_url( 'morpher/v1/health' ) ); ?>, {headers: {'Accept': 'application/json'}})
                            .then((response) => response.json())
                            .then((health) => {
                                const connection = health.connection || {};
                                const ack = connection.latest_acknowledgement || {};
                                if (connection.paired && connection.ref_no === refNo) {
                                    connectionStatus.textContent = 'Paired';
                                    if (ack.ref_no === refNo && ack.event === 'pairing.completed' && ack.status === 'acknowledged') {
                                        status.textContent = `Pairing complete — ${refNo}`;
                                        window.clearInterval(poll);
                                    } else {
                                        status.textContent = `Connected — waiting for acknowledgement — ${refNo}`;
                                    }
                                }
                            })
                            .catch(() => {});
                    }, 2000);
                })
                .catch((error) => {
                    status.textContent = `Could not reach Morpher dashboard: ${error.message}`;
                });
        })();
        </script>
        <?php endif; ?>
        <?php
    }
}
