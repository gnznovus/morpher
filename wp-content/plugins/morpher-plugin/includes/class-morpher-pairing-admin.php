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

        $connected = $this->auth->is_connected();
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
                        <td><?php echo esc_html( $connected ? 'Paired' : 'Not paired' ); ?></td>
                    </tr>
                    <tr>
                        <th scope="row">Site</th>
                        <td><code><?php echo esc_html( get_site_url() ); ?></code></td>
                    </tr>
                </tbody>
            </table>

            <?php if ( $pairing ) : ?>
                <div class="notice notice-info inline" style="max-width: 680px; margin-top: 16px; padding: 12px 16px;">
                    <p><strong>Pairing mode is active for 5 minutes.</strong></p>
                    <p>Enter this code in Morpher:</p>
                    <p style="font-size: 32px; letter-spacing: 0.18em; margin: 12px 0;"><code><?php echo esc_html( $pairing['code'] ); ?></code></p>
                    <p>The code is one-time use and locks after <?php echo esc_html( (string) Morpher_Auth::MAX_ATTEMPTS ); ?> failed attempts.</p>
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
        <?php
    }
}
