<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_REST_Template_Deployment {
    const MAX_ASSET_BYTES = 26214400;

    public function import( $payload ) {
        if ( ! is_array( $payload ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'Deployment payload must be an object.', array( 'status' => 400 ) );
        }

        $slug       = sanitize_title( isset( $payload['slug'] ) ? (string) $payload['slug'] : '' );
        $title      = sanitize_text_field( isset( $payload['title'] ) ? (string) $payload['title'] : '' );
        $build_hash = sanitize_text_field( isset( $payload['build_hash'] ) ? (string) $payload['build_hash'] : '' );
        $ref_no     = strtoupper( sanitize_text_field( isset( $payload['ref_no'] ) ? (string) $payload['ref_no'] : '' ) );
        $template   = isset( $payload['template'] ) && is_array( $payload['template'] ) ? $payload['template'] : null;
        $asset_root = isset( $payload['asset_root'] ) ? trim( (string) $payload['asset_root'], '/' ) : '';
        $assets     = isset( $payload['assets'] ) && is_array( $payload['assets'] ) ? $payload['assets'] : array();

        if ( '' === $slug || '' === $build_hash || ! is_array( $template ) || ! isset( $template['content'] ) || ! is_array( $template['content'] ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'A slug, build hash, and valid Elementor template are required.', array( 'status' => 400 ) );
        }

        if ( '' === $title ) {
            $title = sanitize_text_field( isset( $template['title'] ) ? (string) $template['title'] : $slug );
        }

        $asset_result = $this->store_assets( $slug, $assets );
        if ( is_wp_error( $asset_result ) ) {
            return $asset_result;
        }

        if ( '' !== $asset_root && ! empty( $asset_result['url'] ) ) {
            $template = $this->rewrite_asset_urls( $template, $asset_root, $asset_result['url'] );
        }

        $existing = $this->find_template_by_slug( $slug );
        $post_data = array(
            'post_title'  => $title,
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
            return new WP_Error( 'morpher_deployment_failed', $template_id->get_error_message(), array( 'status' => 500 ) );
        }

        $template_type = isset( $template['type'] ) ? sanitize_key( $template['type'] ) : 'container';
        $page_settings = isset( $template['page_settings'] ) && is_array( $template['page_settings'] ) ? $template['page_settings'] : array();

        update_post_meta( $template_id, '_elementor_edit_mode', 'builder' );
        update_post_meta( $template_id, '_elementor_template_type', $template_type );
        update_post_meta( $template_id, '_elementor_data', wp_slash( wp_json_encode( $template['content'] ) ) );
        update_post_meta( $template_id, '_elementor_page_settings', $page_settings );
        if ( defined( 'ELEMENTOR_VERSION' ) ) {
            update_post_meta( $template_id, '_elementor_version', ELEMENTOR_VERSION );
        }
        update_post_meta( $template_id, '_morpher_slug', $slug );
        update_post_meta( $template_id, '_morpher_build_hash', $build_hash );
        if ( '' !== $ref_no ) {
            update_post_meta( $template_id, '_morpher_last_ref_no', $ref_no );
        }

        clean_post_cache( $template_id );

        return array(
            'status'      => $existing ? 'updated' : 'imported',
            'ref_no'      => $ref_no,
            'deployment'  => $slug,
            'slug'        => $slug,
            'title'       => $title,
            'template_id' => (int) $template_id,
            'build_hash'  => $build_hash,
            'asset_count' => (int) $asset_result['count'],
            'asset_url'   => (string) $asset_result['url'],
            'error'       => '',
        );
    }

    private function store_assets( $slug, $assets ) {
        if ( empty( $assets ) ) {
            return array( 'count' => 0, 'url' => '' );
        }

        $uploads = wp_upload_dir();
        if ( ! empty( $uploads['error'] ) ) {
            return new WP_Error( 'morpher_asset_storage_failed', $uploads['error'], array( 'status' => 500 ) );
        }

        $asset_dir = trailingslashit( $uploads['basedir'] ) . 'morpher-assets/' . $slug;
        $asset_url = trailingslashit( $uploads['baseurl'] ) . 'morpher-assets/' . $slug;
        if ( ! wp_mkdir_p( $asset_dir ) ) {
            return new WP_Error( 'morpher_asset_storage_failed', 'Could not create the Morpher asset directory.', array( 'status' => 500 ) );
        }

        $total = 0;
        $count = 0;
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

            $target = trailingslashit( $asset_dir ) . $relative;
            if ( ! wp_mkdir_p( dirname( $target ) ) || false === file_put_contents( $target, $raw ) ) {
                return new WP_Error( 'morpher_asset_storage_failed', 'Could not store a Morpher asset.', array( 'status' => 500 ) );
            }
            $count++;
        }

        return array( 'count' => $count, 'url' => $asset_url );
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
}
