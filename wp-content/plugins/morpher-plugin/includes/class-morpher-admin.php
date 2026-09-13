<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Admin {
    private $deployments;
    private $diagnostics;
    private $plugin_file;

    public function __construct( Morpher_Deployment $deployments, Morpher_Diagnostics $diagnostics, $plugin_file ) {
        $this->deployments = $deployments;
        $this->diagnostics = $diagnostics;
        $this->plugin_file = $plugin_file;
    }

    public function register() {
        add_action( 'admin_menu', array( $this, 'register_menu' ) );
        add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_assets' ) );
        add_action( 'wp_ajax_morpher_load_tab', array( $this, 'handle_load_tab' ) );
        add_action( 'wp_ajax_morpher_process_deployments', array( $this, 'handle_ajax_process' ) );
        add_action( 'wp_ajax_morpher_redeploy', array( $this, 'handle_ajax_redeploy' ) );
        add_action( 'wp_ajax_morpher_redeploy_all', array( $this, 'handle_ajax_redeploy_all' ) );
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
        $this->guard_ajax();

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

    public function handle_ajax_process() {
        $this->guard_ajax();
        $this->deployments->process_all();
        $this->send_deployments_tab( 'Processed staged Morpher deployments.' );
    }

    public function handle_ajax_redeploy() {
        $this->guard_ajax();

        $requested = isset( $_POST['deployment'] ) ? sanitize_file_name( wp_unslash( $_POST['deployment'] ) ) : '';
        $directory = $requested ? $this->deployments->directory( $requested ) : '';

        if ( ! $requested || ! is_dir( $directory ) || basename( $directory ) !== $requested ) {
            wp_send_json_error( array( 'message' => 'Invalid Morpher deployment.' ), 400 );
        }

        $this->deployments->import( $directory, true );
        $this->send_deployments_tab( 'Re-deployed ' . $requested . '.' );
    }

    public function handle_ajax_redeploy_all() {
        $this->guard_ajax();
        $this->deployments->process_all( true );
        $this->send_deployments_tab( 'Re-deployed all Morpher templates.' );
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

            <div class="morpher-ajax-notice" aria-live="polite"></div>

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
            <div>
                <h2>Deployments</h2>
                <p class="description"><?php echo esc_html( count( $rows ) . ' template' . ( 1 === count( $rows ) ? '' : 's' ) ); ?></p>
            </div>
            <div class="morpher-toolbar-actions">
                <button type="button" class="button morpher-redeploy-all" <?php disabled( empty( $rows ) ); ?>>Re-deploy all</button>
                <button type="button" class="button button-primary morpher-process-staged">Process staged deployments</button>
            </div>
        </div>

        <?php if ( ! $rows ) : ?>
            <div class="morpher-empty-state">
                <h2>No deployments yet</h2>
                <p>Stage a Morpher deployment and it will appear here.</p>
            </div>
        <?php else : ?>
            <div class="morpher-search-row">
                <label class="screen-reader-text" for="morpher-template-search">Search templates</label>
                <input id="morpher-template-search" class="regular-text morpher-template-search" type="search" placeholder="Search templates…" autocomplete="off">
                <span class="morpher-search-count" aria-live="polite"></span>
            </div>

            <div class="morpher-table-scroll">
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
                            <tr data-morpher-search="<?php echo esc_attr( strtolower( $row['title'] . ' ' . $row['slug'] . ' ' . $row['status'] . ' ' . $row['id'] . ' ' . $row['error'] ) ); ?>">
                                <td><?php echo esc_html( $row['title'] ); ?></td>
                                <td><code><?php echo esc_html( $row['slug'] ); ?></code></td>
                                <td><span class="<?php echo esc_attr( $status_class ); ?>"><?php echo esc_html( $row['status'] ); ?></span></td>
                                <td><?php echo $row['id'] ? esc_html( (string) $row['id'] ) : '—'; ?></td>
                                <td><?php echo $row['error'] ? esc_html( $row['error'] ) : '—'; ?></td>
                                <td>
                                    <button type="button" class="button button-small morpher-redeploy" data-deployment="<?php echo esc_attr( $row['deployment'] ); ?>">Re-deploy</button>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
            <p class="morpher-no-results" hidden>No templates match this search.</p>
        <?php endif; ?>
        <?php
    }

    private function render_diagnostics_tab() {
        $system       = $this->diagnostics->system_checks();
        $integrations = $this->diagnostics->integration_checks();
        $issues       = $this->diagnostics->recent_issues();
        ?>
        <div class="morpher-toolbar">
            <div>
                <h2>Diagnostics</h2>
                <p class="description">Check whether Morpher can deploy safely into this WordPress environment.</p>
            </div>
            <div class="morpher-toolbar-actions">
                <button type="button" class="button morpher-refresh-diagnostics">Refresh checks</button>
            </div>
        </div>

        <div class="morpher-diagnostics-grid">
            <?php $this->render_diagnostic_group( 'System Health', $system ); ?>
            <?php $this->render_diagnostic_group( 'Integration', $integrations ); ?>
        </div>

        <section class="morpher-diagnostic-section morpher-issues">
            <div class="morpher-diagnostic-section-header">
                <h3>Recent Issues</h3>
                <span class="morpher-issue-count"><?php echo esc_html( count( $issues ) ); ?></span>
            </div>

            <?php if ( ! $issues ) : ?>
                <div class="morpher-diagnostic-ok">
                    <span class="dashicons dashicons-yes-alt" aria-hidden="true"></span>
                    <span>No deployment issues detected.</span>
                </div>
            <?php else : ?>
                <div class="morpher-issue-list">
                    <?php foreach ( $issues as $issue ) : ?>
                        <div class="morpher-issue-item">
                            <strong><?php echo esc_html( $issue['title'] ); ?></strong>
                            <code><?php echo esc_html( $issue['slug'] ); ?></code>
                            <p><?php echo esc_html( $issue['message'] ); ?></p>
                        </div>
                    <?php endforeach; ?>
                </div>
            <?php endif; ?>
        </section>
        <?php
    }

    private function render_diagnostic_group( $title, $checks ) {
        ?>
        <section class="morpher-diagnostic-section">
            <h3><?php echo esc_html( $title ); ?></h3>
            <div class="morpher-diagnostic-list">
                <?php foreach ( $checks as $check ) : ?>
                    <div class="morpher-diagnostic-row">
                        <span class="morpher-health-dot morpher-health-dot--<?php echo esc_attr( $check['status'] ); ?>" aria-hidden="true"></span>
                        <div class="morpher-diagnostic-copy">
                            <strong><?php echo esc_html( $check['label'] ); ?></strong>
                            <span><?php echo esc_html( $check['detail'] ); ?></span>
                        </div>
                        <span class="morpher-health-label morpher-health-label--<?php echo esc_attr( $check['status'] ); ?>">
                            <?php echo esc_html( 'healthy' === $check['status'] ? 'Healthy' : ( 'error' === $check['status'] ? 'Error' : 'Not configured' ) ); ?>
                        </span>
                    </div>
                <?php endforeach; ?>
            </div>
        </section>
        <?php
    }

    private function guard_ajax() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_send_json_error( array( 'message' => 'Forbidden.' ), 403 );
        }

        check_ajax_referer( 'morpher_admin_tabs', 'nonce' );
    }

    private function send_deployments_tab( $message ) {
        ob_start();
        $this->render_deployments_tab();
        $html = ob_get_clean();

        wp_send_json_success(
            array(
                'html'    => $html,
                'message' => $message,
            )
        );
    }
}
