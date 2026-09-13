<?php
/**
 * Plugin Name: Morpher
 * Description: WordPress integration for Morpher-generated Elementor output.
 * Version: 0.4.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

require_once plugin_dir_path( __FILE__ ) . 'includes/class-morpher-deployment.php';

function morpher_plugin_enqueue_fonts() {
    $css_path = plugin_dir_path( __FILE__ ) . 'assets/fonts.css';
    if ( ! file_exists( $css_path ) ) {
        return;
    }

    wp_enqueue_style(
        'morpher-fonts',
        plugin_dir_url( __FILE__ ) . 'assets/fonts.css',
        array(),
        (string) filemtime( $css_path )
    );
}

add_action( 'wp_enqueue_scripts', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/frontend/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/editor/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/preview/enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );

function morpher_deployment_service() {
    static $service = null;

    if ( null === $service ) {
        $service = new Morpher_Deployment( plugin_dir_path( __FILE__ ) . 'deployments' );
    }

    return $service;
}

function morpher_admin_menu() {
    add_menu_page(
        'Morpher',
        'Morpher',
        'manage_options',
        'morpher',
        'morpher_render_admin_page',
        'dashicons-layout',
        58
    );
}
add_action( 'admin_menu', 'morpher_admin_menu' );

function morpher_handle_manual_process() {
    if ( ! current_user_can( 'manage_options' ) ) {
        wp_die( esc_html__( 'You are not allowed to process Morpher deployments.', 'morpher' ) );
    }

    check_admin_referer( 'morpher_process_deployments' );
    morpher_deployment_service()->process_all();

    wp_safe_redirect(
        add_query_arg(
            'morpher_processed',
            '1',
            admin_url( 'admin.php?page=morpher' )
        )
    );
    exit;
}
add_action( 'admin_post_morpher_process_deployments', 'morpher_handle_manual_process' );

function morpher_handle_redeploy() {
    if ( ! current_user_can( 'manage_options' ) ) {
        wp_die( esc_html__( 'You are not allowed to re-deploy Morpher templates.', 'morpher' ) );
    }

    check_admin_referer( 'morpher_redeploy' );

    $requested = isset( $_POST['deployment'] ) ? sanitize_file_name( wp_unslash( $_POST['deployment'] ) ) : '';
    $service   = morpher_deployment_service();
    $directory = $requested ? $service->directory( $requested ) : '';

    if ( ! $requested || ! is_dir( $directory ) || basename( $directory ) !== $requested ) {
        wp_die( esc_html__( 'Invalid Morpher deployment.', 'morpher' ) );
    }

    $service->import( $directory, true );

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
add_action( 'admin_post_morpher_redeploy', 'morpher_handle_redeploy' );

function morpher_render_admin_page() {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    $rows = morpher_deployment_service()->rows();
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
