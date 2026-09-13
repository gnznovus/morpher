<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Deployment {
    private $root;

    public function __construct( $root ) {
        $this->root = untrailingslashit( $root );
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
