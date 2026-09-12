<?php
/**
 * Plugin Name: Morpher
 * Description: WordPress integration for Morpher-generated Elementor output.
 * Version: 0.3.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

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

function morpher_deployment_status( $directory, $status, $manifest, $extra = array() ) {
    $payload = array_merge(
        array(
            'status'     => $status,
            'slug'       => isset( $manifest['slug'] ) ? $manifest['slug'] : '',
            'build_hash' => isset( $manifest['build_hash'] ) ? $manifest['build_hash'] : '',
            'updated_at' => gmdate( 'c' ),
        ),
        $extra
    );

    file_put_contents(
        trailingslashit( $directory ) . 'status.json',
        wp_json_encode( $payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . "\n"
    );
}

function morpher_find_template_by_slug( $slug ) {
    $posts = get_posts(
        array(
            'post_type'      => 'elementor_library',
            'post_status'    => array( 'publish', 'draft', 'private' ),
            'posts_per_page' => 1,
            'fields'         => 'ids',
            'meta_key'       => '_morpher_slug',
            'meta_value'     => $slug,
        )
    );

    return $posts ? (int) $posts[0] : 0;
}

function morpher_copy_directory( $source, $destination ) {
    if ( ! is_dir( $source ) ) {
        return true;
    }

    if ( ! wp_mkdir_p( $destination ) ) {
        return false;
    }

    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator( $source, FilesystemIterator::SKIP_DOTS ),
        RecursiveIteratorIterator::SELF_FIRST
    );

    foreach ( $iterator as $item ) {
        $relative = substr( $item->getPathname(), strlen( $source ) + 1 );
        $target   = trailingslashit( $destination ) . $relative;
        if ( $item->isDir() ) {
            if ( ! wp_mkdir_p( $target ) ) {
                return false;
            }
        } elseif ( ! copy( $item->getPathname(), $target ) ) {
            return false;
        }
    }

    return true;
}

function morpher_rewrite_asset_urls( $value, $asset_root, $asset_url ) {
    if ( is_array( $value ) ) {
        foreach ( $value as $key => $child ) {
            $value[ $key ] = morpher_rewrite_asset_urls( $child, $asset_root, $asset_url );
        }
        return $value;
    }

    if ( is_string( $value ) ) {
        $prefix = trailingslashit( $asset_root );
        if ( str_starts_with( $value, $prefix ) ) {
            return trailingslashit( $asset_url ) . substr( $value, strlen( $prefix ) );
        }
    }

    return $value;
}

function morpher_import_deployment( $directory ) {
    $manifest_path = trailingslashit( $directory ) . 'manifest.json';
    $template_path = trailingslashit( $directory ) . 'template.json';
    $status_path   = trailingslashit( $directory ) . 'status.json';

    if ( ! is_file( $manifest_path ) || ! is_file( $template_path ) ) {
        return;
    }

    $manifest = json_decode( file_get_contents( $manifest_path ), true );
    if ( ! is_array( $manifest ) || empty( $manifest['slug'] ) || empty( $manifest['build_hash'] ) ) {
        return;
    }

    if ( is_file( $status_path ) ) {
        $status = json_decode( file_get_contents( $status_path ), true );
        if ( is_array( $status ) && isset( $status['build_hash'] ) && $status['build_hash'] === $manifest['build_hash'] ) {
            return;
        }
    }

    $slug     = sanitize_title( $manifest['slug'] );
    $force    = ! empty( $manifest['force'] );
    $existing = morpher_find_template_by_slug( $slug );

    if ( $existing && ! $force ) {
        morpher_deployment_status(
            $directory,
            'skipped',
            $manifest,
            array( 'template_id' => $existing )
        );
        return;
    }

    $template = json_decode( file_get_contents( $template_path ), true );
    if ( ! is_array( $template ) || ! isset( $template['content'] ) ) {
        morpher_deployment_status( $directory, 'failed', $manifest, array( 'error' => 'Invalid Elementor template JSON.' ) );
        return;
    }

    $uploads = wp_upload_dir();
    if ( ! empty( $uploads['error'] ) ) {
        morpher_deployment_status( $directory, 'failed', $manifest, array( 'error' => $uploads['error'] ) );
        return;
    }

    $asset_dir     = trailingslashit( $uploads['basedir'] ) . 'morpher-assets/' . $slug;
    $asset_url     = trailingslashit( $uploads['baseurl'] ) . 'morpher-assets/' . $slug;
    $source_assets = trailingslashit( $directory ) . 'assets';

    if ( ! morpher_copy_directory( $source_assets, $asset_dir ) ) {
        morpher_deployment_status( $directory, 'failed', $manifest, array( 'error' => 'Could not copy Morpher assets.' ) );
        return;
    }

    $asset_root = isset( $manifest['asset_root'] ) ? trim( $manifest['asset_root'], '/' ) : '';
    if ( $asset_root ) {
        $template = morpher_rewrite_asset_urls( $template, $asset_root, $asset_url );
    }

    $post_data = array(
        'post_title'  => sanitize_text_field( isset( $template['title'] ) ? $template['title'] : $manifest['title'] ),
        'post_type'   => 'elementor_library',
        'post_status' => 'publish',
    );

    if ( $existing ) {
        $post_data['ID'] = $existing;
        $template_id = wp_update_post( $post_data, true );
    } else {
        $template_id = wp_insert_post( $post_data, true );
    }

    if ( is_wp_error( $template_id ) ) {
        morpher_deployment_status( $directory, 'failed', $manifest, array( 'error' => $template_id->get_error_message() ) );
        return;
    }

    $template_type = isset( $template['type'] ) ? sanitize_key( $template['type'] ) : 'container';
    $page_settings = isset( $template['page_settings'] ) ? $template['page_settings'] : array();

    update_post_meta( $template_id, '_elementor_edit_mode', 'builder' );
    update_post_meta( $template_id, '_elementor_template_type', $template_type );
    update_post_meta( $template_id, '_elementor_data', wp_slash( wp_json_encode( $template['content'] ) ) );
    update_post_meta( $template_id, '_elementor_page_settings', $page_settings );
    if ( defined( 'ELEMENTOR_VERSION' ) ) {
        update_post_meta( $template_id, '_elementor_version', ELEMENTOR_VERSION );
    }
    update_post_meta( $template_id, '_morpher_slug', $slug );
    update_post_meta( $template_id, '_morpher_build_hash', $manifest['build_hash'] );

    clean_post_cache( $template_id );

    morpher_deployment_status(
        $directory,
        $existing ? 'updated' : 'imported',
        $manifest,
        array(
            'template_id' => (int) $template_id,
            'asset_url'   => $asset_url,
        )
    );
}

function morpher_process_deployments() {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    $root = plugin_dir_path( __FILE__ ) . 'deployments';
    if ( ! is_dir( $root ) ) {
        return;
    }

    $directories = glob( trailingslashit( $root ) . '*', GLOB_ONLYDIR );
    if ( ! $directories ) {
        return;
    }

    foreach ( $directories as $directory ) {
        morpher_import_deployment( $directory );
    }
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
    morpher_process_deployments();

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

function morpher_deployment_rows() {
    $root = plugin_dir_path( __FILE__ ) . 'deployments';
    if ( ! is_dir( $root ) ) {
        return array();
    }

    $rows = array();
    $directories = glob( trailingslashit( $root ) . '*', GLOB_ONLYDIR );
    foreach ( $directories ?: array() as $directory ) {
        $manifest_path = trailingslashit( $directory ) . 'manifest.json';
        $status_path   = trailingslashit( $directory ) . 'status.json';
        $manifest      = is_file( $manifest_path ) ? json_decode( file_get_contents( $manifest_path ), true ) : array();
        $status        = is_file( $status_path ) ? json_decode( file_get_contents( $status_path ), true ) : array();

        $rows[] = array(
            'slug'   => isset( $manifest['slug'] ) ? $manifest['slug'] : basename( $directory ),
            'title'  => isset( $manifest['title'] ) ? $manifest['title'] : basename( $directory ),
            'status' => isset( $status['status'] ) ? $status['status'] : 'staged',
            'id'     => isset( $status['template_id'] ) ? (int) $status['template_id'] : 0,
            'error'  => isset( $status['error'] ) ? $status['error'] : '',
        );
    }

    return $rows;
}

function morpher_render_admin_page() {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    $rows = morpher_deployment_rows();
    ?>
    <div class="wrap">
        <h1>Morpher</h1>
        <p>Process staged Morpher Elementor deployments manually.</p>

        <?php if ( isset( $_GET['morpher_processed'] ) ) : ?>
            <div class="notice notice-success is-dismissible"><p>Morpher deployments processed.</p></div>
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
            <table class="widefat striped" style="max-width: 1000px;">
                <thead>
                    <tr>
                        <th>Template</th>
                        <th>Slug</th>
                        <th>Status</th>
                        <th>Elementor ID</th>
                        <th>Error</th>
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
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>
    <?php
}
