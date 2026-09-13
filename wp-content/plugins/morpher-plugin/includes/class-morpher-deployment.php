<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Deployment {
    const MAX_ASSET_BYTES = 26214400;

    private $root;

    public function __construct( $root ) {
        $this->root = untrailingslashit( $root );
    }

    public function stage_payload( $payload ) {
        if ( ! is_array( $payload ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'Deployment payload must be an object.', array( 'status' => 400 ) );
        }

        $ref_no   = strtoupper( sanitize_text_field( isset( $payload['ref_no'] ) ? (string) $payload['ref_no'] : '' ) );
        $manifest = isset( $payload['manifest'] ) && is_array( $payload['manifest'] ) ? $payload['manifest'] : null;
        $template = isset( $payload['template'] ) && is_array( $payload['template'] ) ? $payload['template'] : null;
        $assets   = isset( $payload['assets'] ) && is_array( $payload['assets'] ) ? $payload['assets'] : array();

        if ( ! is_array( $manifest ) || ! is_array( $template ) || ! isset( $template['content'] ) || ! is_array( $template['content'] ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'A manifest and valid Elementor template are required.', array( 'status' => 400 ) );
        }

        $slug       = sanitize_title( isset( $manifest['slug'] ) ? (string) $manifest['slug'] : '' );
        $build_hash = sanitize_text_field( isset( $manifest['build_hash'] ) ? (string) $manifest['build_hash'] : '' );
        if ( '' === $slug || '' === $build_hash || '' === $ref_no ) {
            return new WP_Error( 'morpher_deployment_invalid', 'Deployment slug, build hash, and Ref No. are required.', array( 'status' => 400 ) );
        }

        $manifest['slug']       = $slug;
        $manifest['build_hash'] = $build_hash;
        $manifest['ref_no']     = $ref_no;
        $manifest['staged_at']  = gmdate( 'c' );

        if ( ! wp_mkdir_p( $this->root ) ) {
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not create Morpher deployment staging.', array( 'status' => 500 ) );
        }

        $directory = $this->directory( $slug );
        $temporary = $directory . '.incoming-' . wp_generate_password( 8, false, false );
        if ( ! wp_mkdir_p( $temporary ) ) {
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not create temporary deployment staging.', array( 'status' => 500 ) );
        }

        $result = $this->write_staged_package( $temporary, $manifest, $template, $assets );
        if ( is_wp_error( $result ) ) {
            $this->remove_directory( $temporary );
            return $result;
        }

        if ( is_dir( $directory ) && ! $this->remove_directory( $directory ) ) {
            $this->remove_directory( $temporary );
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not replace the existing staged deployment.', array( 'status' => 500 ) );
        }

        if ( ! rename( $temporary, $directory ) ) {
            $this->remove_directory( $temporary );
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not activate the staged deployment.', array( 'status' => 500 ) );
        }

        return array(
            'status'      => 'staged',
            'ref_no'      => $ref_no,
            'deployment'  => $slug,
            'slug'        => $slug,
            'title'       => isset( $manifest['title'] ) ? (string) $manifest['title'] : $slug,
            'build_hash'  => $build_hash,
            'asset_count' => count( $assets ),
        );
    }

    private function write_staged_package( $directory, $manifest, $template, $assets ) {
        $manifest_json = wp_json_encode( $manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );
        $template_json = wp_json_encode( $template, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );
        if ( false === $manifest_json || false === $template_json ) {
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not encode the deployment package.', array( 'status' => 500 ) );
        }

        if ( false === file_put_contents( trailingslashit( $directory ) . 'manifest.json', $manifest_json . "\n" ) ||
            false === file_put_contents( trailingslashit( $directory ) . 'template.json', $template_json . "\n" ) ) {
            return new WP_Error( 'morpher_deployment_stage_failed', 'Could not write the staged deployment.', array( 'status' => 500 ) );
        }

        $total = 0;
        foreach ( $assets as $asset ) {
            if ( ! is_array( $asset ) ) {
                return new WP_Error( 'morpher_asset_invalid', 'Asset entries must be objects.', array( 'status' => 400 ) );
            }

            $relative = isset( $asset['path'] ) ? str_replace( '\\', '/', trim( (string) $asset['path'] ) ) : '';
            $encoded  = isset( $asset['content'] ) ? (string) $asset['content'] : '';
            $expected = strtolower( isset( $asset['sha256'] ) ? trim( (string) $asset['sha256'] ) : '' );

            if ( '' === $relative || str_starts_with( $relative, '/' ) || false !== strpos( $relative, '../' ) || '..' === $relative ) {
                return new WP_Error( 'morpher_asset_path_invalid', 'Morpher asset path is invalid.', array( 'status' => 400 ) );
            }

            $raw = base64_decode( $encoded, true );
            if ( false === $raw ) {
                return new WP_Error( 'morpher_asset_invalid', 'Morpher asset content is not valid base64.', array( 'status' => 400 ) );
            }

            $total += strlen( $raw );
            if ( $total > self::MAX_ASSET_BYTES ) {
                return new WP_Error( 'morpher_assets_too_large', 'Morpher deployment assets exceed the v1 size limit.', array( 'status' => 413 ) );
            }

            if ( '' !== $expected && ! hash_equals( $expected, hash( 'sha256', $raw ) ) ) {
                return new WP_Error( 'morpher_asset_hash_mismatch', 'Morpher asset integrity check failed.', array( 'status' => 400 ) );
            }

            $target = trailingslashit( $directory ) . 'assets/' . $relative;
            if ( ! wp_mkdir_p( dirname( $target ) ) || false === file_put_contents( $target, $raw ) ) {
                return new WP_Error( 'morpher_deployment_stage_failed', 'Could not write a staged Morpher asset.', array( 'status' => 500 ) );
            }
        }

        return true;
    }

    public function import( $directory, $force_override = false ) {
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

        $force = $force_override || ! empty( $manifest['force'] );

        if ( ! $force && is_file( $status_path ) ) {
            $status = json_decode( file_get_contents( $status_path ), true );
            if ( is_array( $status ) && isset( $status['build_hash'] ) && $status['build_hash'] === $manifest['build_hash'] ) {
                return;
            }
        }

        $slug     = sanitize_title( $manifest['slug'] );
        $existing = $this->find_template_by_slug( $slug );

        if ( $existing && ! $force ) {
            $this->write_status(
                $directory,
                'skipped',
                $manifest,
                array( 'template_id' => $existing )
            );
            return;
        }

        $template = json_decode( file_get_contents( $template_path ), true );
        if ( ! is_array( $template ) || ! isset( $template['content'] ) ) {
            $this->write_status( $directory, 'failed', $manifest, array( 'error' => 'Invalid Elementor template JSON.' ) );
            return;
        }

        $uploads = wp_upload_dir();
        if ( ! empty( $uploads['error'] ) ) {
            $this->write_status( $directory, 'failed', $manifest, array( 'error' => $uploads['error'] ) );
            return;
        }

        $asset_dir     = trailingslashit( $uploads['basedir'] ) . 'morpher-assets/' . $slug;
        $asset_url     = trailingslashit( $uploads['baseurl'] ) . 'morpher-assets/' . $slug;
        $source_assets = trailingslashit( $directory ) . 'assets';

        if ( ! $this->copy_directory( $source_assets, $asset_dir ) ) {
            $this->write_status( $directory, 'failed', $manifest, array( 'error' => 'Could not copy Morpher assets.' ) );
            return;
        }

        $asset_root = isset( $manifest['asset_root'] ) ? trim( $manifest['asset_root'], '/' ) : '';
        if ( $asset_root ) {
            $template = $this->rewrite_asset_urls( $template, $asset_root, $asset_url );
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
            $this->write_status( $directory, 'failed', $manifest, array( 'error' => $template_id->get_error_message() ) );
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
        if ( ! empty( $manifest['ref_no'] ) ) {
            update_post_meta( $template_id, '_morpher_last_ref_no', sanitize_text_field( $manifest['ref_no'] ) );
        }

        clean_post_cache( $template_id );

        $this->write_status(
            $directory,
            $existing ? 'updated' : 'imported',
            $manifest,
            array(
                'template_id' => (int) $template_id,
                'asset_url'   => $asset_url,
            )
        );
    }

    public function process_all( $force_override = false ) {
        if ( ! current_user_can( 'manage_options' ) || ! is_dir( $this->root ) ) {
            return;
        }

        $directories = glob( trailingslashit( $this->root ) . '*', GLOB_ONLYDIR );
        if ( ! $directories ) {
            return;
        }

        foreach ( $directories as $directory ) {
            $this->import( $directory, $force_override );
        }
    }

    public function rows() {
        if ( ! is_dir( $this->root ) ) {
            return array();
        }

        $rows = array();
        $directories = glob( trailingslashit( $this->root ) . '*', GLOB_ONLYDIR );
        foreach ( $directories ?: array() as $directory ) {
            $manifest_path = trailingslashit( $directory ) . 'manifest.json';
            $status_path   = trailingslashit( $directory ) . 'status.json';
            $manifest      = is_file( $manifest_path ) ? json_decode( file_get_contents( $manifest_path ), true ) : array();
            $status        = is_file( $status_path ) ? json_decode( file_get_contents( $status_path ), true ) : array();

            $rows[] = array(
                'deployment' => basename( $directory ),
                'slug'       => isset( $manifest['slug'] ) ? $manifest['slug'] : basename( $directory ),
                'title'      => isset( $manifest['title'] ) ? $manifest['title'] : basename( $directory ),
                'status'     => isset( $status['status'] ) ? $status['status'] : 'staged',
                'id'         => isset( $status['template_id'] ) ? (int) $status['template_id'] : 0,
                'error'      => isset( $status['error'] ) ? $status['error'] : '',
            );
        }

        return $rows;
    }

    public function directory( $deployment ) {
        return trailingslashit( $this->root ) . $deployment;
    }

    private function write_status( $directory, $status, $manifest, $extra = array() ) {
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

    private function find_template_by_slug( $slug ) {
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

    private function copy_directory( $source, $destination ) {
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

    private function remove_directory( $directory ) {
        if ( ! is_dir( $directory ) ) {
            return true;
        }

        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator( $directory, FilesystemIterator::SKIP_DOTS ),
            RecursiveIteratorIterator::CHILD_FIRST
        );

        foreach ( $iterator as $item ) {
            if ( $item->isDir() ) {
                if ( ! rmdir( $item->getPathname() ) ) {
                    return false;
                }
            } elseif ( ! unlink( $item->getPathname() ) ) {
                return false;
            }
        }

        return rmdir( $directory );
    }

    private function rewrite_asset_urls( $value, $asset_root, $asset_url ) {
        if ( is_array( $value ) ) {
            foreach ( $value as $key => $child ) {
                $value[ $key ] = $this->rewrite_asset_urls( $child, $asset_root, $asset_url );
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
}
