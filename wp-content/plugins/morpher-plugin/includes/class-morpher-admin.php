<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Admin {
    private $deployments;

    public function __construct( Morpher_Deployment $deployments ) {
        $this->deployments = $deployments;
    }

    public function register() {
        add_action( 'admin_menu', array( $this, 'register_menu' ) );
        add_action( 'admin_post_morpher_process_deployments', array( $this, 'handle_manual_process' ) );
        add_action( 'admin_post_morpher_redeploy', array( $this, 'handle_redeploy' ) );
    }

    public function register_menu() {
        add_menu_page(
            'Morpher',
            'Morpher',
            'manage_options',
            'morpher',
            array( $this, 'render_page' ),
            'dashicons-layout',
            58
        );
    }

    public function handle_manual_process() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'You are not allowed to process Morpher deployments.', 'morpher' ) );
        }

        check_admin_referer( 'morpher_process_deployments' );
        $this->deployments->process_all();

        wp_safe_redirect(
            add_query_arg(
                'morpher_processed',
                '1',
                admin_url( 'admin.php?page=morpher' )
            )
        );
        exit;
    }

    public function handle_redeploy() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'You are not allowed to re-deploy Morpher templates.', 'morpher' ) );
        }

        check_admin_referer( 'morpher_redeploy' );

        $requested = isset( $_POST['deployment'] ) ? sanitize_file_name( wp_unslash( $_POST['deployment'] ) ) : '';
        $directory = $requested ? $this->deployments->directory( $requested ) : '';

        if ( ! $requested || ! is_dir( $directory ) || basename( $directory ) !== $requested ) {
            wp_die( esc_html__( 'Invalid Morpher deployment.', 'morpher' ) );
        }

        $this->deployments->import( $directory, true );

        wp_safe_redirect(
            add_query_arg(
                array(
                    'page'               => 'morpher',
                    'morpher_redeployed' => $requested,
                ),
                admin_url( 'admin.php' )
            )
        );
        exit;
    }

    public function render_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }

        $rows = $this->deployments->rows();
        ?>
        <div class="wrap">
            <h1>Morpher</h1>
            <p>Process staged Morpher Elementor deployments manually.</p>

            <?php if ( isset( $_GET['morpher_processed'] ) ) : ?>
                <div class="notice notice-success is-dismissible"><p>Morpher deployments processed.</p></div>
            <?php endif; ?>
            <?php if ( isset( $_GET['morpher_redeployed'] ) ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( 'Re-deployed ' . sanitize_file_name( wp_unslash( $_GET['morpher_redeployed'] ) ) . '.' ); ?></p></div>
            <?php endif; ?>

            <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                <input type="hidden" name="action" value="morpher_process_deployments">
                <?php wp_nonce_field( 'morpher_process_deployments' ); ?>
                <?php submit_button( 'Process staged deployments', 'primary', 'submit', false ); ?>
            </form>

            <h2>Deployments</h2>
            <?php if ( ! $rows ) : ?>
                <p>No staged deployments found.</p>
            <?php else : ?>
                <table class="widefat striped" style="max-width: 1100px;">
                    <thead>
                        <tr>
                            <th>Template</th>
                            <th>Slug</th>
                            <th>Status</th>
                            <th>Elementor ID</th>
                            <th>Error</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ( $rows as $row ) : ?>
                            <tr>
                                <td><?php echo esc_html( $row['title'] ); ?></td>
                                <td><code><?php echo esc_html( $row['slug'] ); ?></code></td>
                                <td><?php echo esc_html( $row['status'] ); ?></td>
                                <td><?php echo $row['id'] ? esc_html( (string) $row['id'] ) : '—'; ?></td>
                                <td><?php echo $row['error'] ? esc_html( $row['error'] ) : '—'; ?></td>
                                <td>
                                    <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                                        <input type="hidden" name="action" value="morpher_redeploy">
                                        <input type="hidden" name="deployment" value="<?php echo esc_attr( $row['deployment'] ); ?>">
                                        <?php wp_nonce_field( 'morpher_redeploy' ); ?>
                                        <?php submit_button( 'Re-deploy', 'secondary small', 'submit', false ); ?>
                                    </form>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
        <?php
    }
}
