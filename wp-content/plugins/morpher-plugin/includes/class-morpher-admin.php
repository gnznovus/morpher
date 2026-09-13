<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Admin {
    private $deployments;
    private $plugin_file;

    public function __construct( Morpher_Deployment $deployments, $plugin_file ) {
        $this->deployments = $deployments;
        $this->plugin_file = $plugin_file;
    }

    public function register() {
        add_action( 'admin_menu', array( $this, 'register_menu' ) );
        add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_assets' ) );
        add_action( 'wp_ajax_morpher_load_tab', array( $this, 'handle_load_tab' ) );
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

    public function enqueue_assets( $hook_suffix ) {
        if ( 'toplevel_page_morpher' !== $hook_suffix ) {
            return;
        }

        $base_url = plugin_dir_url( $this->plugin_file );

        wp_enqueue_style(
            'morpher-admin',
            $base_url . 'assets/admin.css',
            array(),
            '0.4.0'
        );

        wp_enqueue_script(
            'morpher-admin',
            $base_url . 'assets/admin.js',
            array(),
            '0.4.0',
            true
        );

        wp_localize_script(
            'morpher-admin',
            'MorpherAdmin',
            array(
                'ajaxUrl' => admin_url( 'admin-ajax.php' ),
                'nonce'   => wp_create_nonce( 'morpher_admin_tabs' ),
            )
        );
    }

    public function handle_load_tab() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_send_json_error( array( 'message' => 'Forbidden.' ), 403 );
        }

        check_ajax_referer( 'morpher_admin_tabs', 'nonce' );

        $tab = isset( $_POST['tab'] ) ? sanitize_key( wp_unslash( $_POST['tab'] ) ) : 'deployments';

        ob_start();
        if ( 'diagnostics' === $tab ) {
            $this->render_diagnostics_tab();
        } else {
            $tab = 'deployments';
            $this->render_deployments_tab();
        }
        $html = ob_get_clean();

        wp_send_json_success(
            array(
                'tab'  => $tab,
                'html' => $html,
            )
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
        ?>
        <div class="wrap" id="morpher-admin">
            <div class="morpher-admin-header">
                <h1>Morpher</h1>
                <p>Manage Morpher deployments and inspect plugin diagnostics.</p>
            </div>

            <?php if ( isset( $_GET['morpher_processed'] ) ) : ?>
                <div class="notice notice-success is-dismissible"><p>Morpher deployments processed.</p></div>
            <?php endif; ?>
            <?php if ( isset( $_GET['morpher_redeployed'] ) ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( 'Re-deployed ' . sanitize_file_name( wp_unslash( $_GET['morpher_redeployed'] ) ) . '.' ); ?></p></div>
            <?php endif; ?>

            <nav class="nav-tab-wrapper morpher-tabs" aria-label="Morpher sections" role="tablist">
                <a href="#deployments" class="nav-tab morpher-tab nav-tab-active" data-tab="deployments" role="tab" aria-selected="true">Deployments</a>
                <a href="#diagnostics" class="nav-tab morpher-tab" data-tab="diagnostics" role="tab" aria-selected="false" tabindex="-1">Diagnostics</a>
            </nav>

            <div class="morpher-tab-panel" role="tabpanel" aria-live="polite" aria-busy="true">
                <p class="morpher-loading">Loading…</p>
            </div>
        </div>
        <?php
    }

    private function render_deployments_tab() {
        $rows = $this->deployments->rows();
        ?>
        <div class="morpher-toolbar">
            <h2>Deployments</h2>
            <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                <input type="hidden" name="action" value="morpher_process_deployments">
                <?php wp_nonce_field( 'morpher_process_deployments' ); ?>
                <?php submit_button( 'Process staged deployments', 'primary', 'submit', false ); ?>
            </form>
        </div>

        <?php if ( ! $rows ) : ?>
            <div class="morpher-empty-state">
                <h2>No deployments yet</h2>
                <p>Stage a Morpher deployment and it will appear here.</p>
            </div>
        <?php else : ?>
            <table class="widefat striped morpher-deployment-table">
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
                        <?php $status_class = 'morpher-status morpher-status--' . sanitize_html_class( $row['status'] ); ?>
                        <tr>
                            <td><?php echo esc_html( $row['title'] ); ?></td>
                            <td><code><?php echo esc_html( $row['slug'] ); ?></code></td>
                            <td><span class="<?php echo esc_attr( $status_class ); ?>"><?php echo esc_html( $row['status'] ); ?></span></td>
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
        <?php
    }

    private function render_diagnostics_tab() {
        ?>
        <div class="morpher-empty-state">
            <h2>Diagnostics</h2>
            <p>No plugin diagnostics are available yet.</p>
        </div>
        <?php
    }
}
