<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_REST_Template_Deployment {
    public function import( $payload ) {
        if ( ! is_array( $payload ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'Deployment payload must be an object.', array( 'status' => 400 ) );
        }

        $slug       = sanitize_title( isset( $payload['slug'] ) ? (string) $payload['slug'] : '' );
        $title      = sanitize_text_field( isset( $payload['title'] ) ? (string) $payload['title'] : '' );
        $build_hash = sanitize_text_field( isset( $payload['build_hash'] ) ? (string) $payload['build_hash'] : '' );
        $ref_no     = strtoupper( sanitize_text_field( isset( $payload['ref_no'] ) ? (string) $payload['ref_no'] : '' ) );
        $template   = isset( $payload['template'] ) && is_array( $payload['template'] ) ? $payload['template'] : null;

        if ( '' === $slug || '' === $build_hash || ! is_array( $template ) || ! isset( $template['content'] ) || ! is_array( $template['content'] ) ) {
            return new WP_Error( 'morpher_deployment_invalid', 'A slug, build hash, and valid Elementor template are required.', array( 'status' => 400 ) );
        }

        if ( '' === $title ) {
            $title = sanitize_text_field( isset( $template['title'] ) ? (string) $template['title'] : $slug );
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
            'error'       => '',
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
}
